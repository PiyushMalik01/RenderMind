"""
WebSocket server for RenderMind - runs in background thread
Allows web UI to communicate with Blender addon
"""

import bpy
import json
import threading
import asyncio
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
from pathlib import Path
from datetime import datetime

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
    print(f"RenderMind: websockets {websockets.__version__} loaded successfully")
except ImportError as e:
    WEBSOCKETS_AVAILABLE = False
    websockets = None
    print(f"RenderMind: websockets library not found - {e}")
    print("RenderMind: Install with: python -m pip install websockets")

# Global server state
server_instance = None
server_thread = None
http_server = None
http_thread = None
server_running = False
server_loop = None  # Store event loop for broadcasting from timer
connected_clients = set()


async def handle_client(websocket):
    """Handle incoming WebSocket connections"""
    global connected_clients
    connected_clients.add(websocket)
    print(f"[RenderMind WebSocket] Client connected. Total clients: {len(connected_clients)}")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                print(f"[RenderMind] Received: {data.get('type', 'unknown')}")
                
                # Handle different message types
                response = await handle_message(data)
                
                # Send response back
                await websocket.send(json.dumps(response))
                
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Invalid JSON'
                }))
            except Exception as e:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': str(e)
                }))
    
    except websockets.exceptions.ConnectionClosed:
        print("[RenderMind WebSocket] Client disconnected")
    finally:
        connected_clients.remove(websocket)


async def handle_message(data):
    """Process messages from web UI"""
    msg_type = data.get('type')
    
    if msg_type == 'ping':
        return {'type': 'pong', 'timestamp': datetime.now().isoformat()}
    
    elif msg_type == 'transcribe_audio':
        # Handle voice transcription using OpenAI Whisper
        audio_base64 = data.get('audio', '')
        
        try:
            from . import model_interface
            import base64
            import tempfile
            
            # Decode audio
            audio_data = base64.b64decode(audio_base64)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_audio:
                temp_audio.write(audio_data)
                temp_path = temp_audio.name
            
            # Transcribe using Whisper API
            text, error = model_interface.transcribe_audio(temp_path)
            
            # Clean up temp file
            import os
            try:
                os.unlink(temp_path)
            except:
                pass
            
            if error:
                return {
                    'type': 'transcription',
                    'error': error
                }
            
            return {
                'type': 'transcription',
                'text': text
            }
            
        except Exception as e:
            return {
                'type': 'transcription',
                'error': str(e)
            }
    
    elif msg_type == 'send_message':
        # User sent a chat message
        user_message = data.get('content', '') or data.get('message', '')
        
        # Add to Blender's chat history (thread-safe)
        def add_message():
            from . import model_interface
            from .blender_addon import blender_utils
            
            props = bpy.context.scene.rm_props
            
            # Add user message
            user_msg = props.chat_messages.add()
            user_msg.role = 'USER'
            user_msg.content = user_message
            user_msg.timestamp = datetime.now().strftime("%H:%M")
            
            # Get AI response
            props.is_thinking = True
            try:
                code, ai_message, error = model_interface.generate_blender_code(user_message)
                
                if error:
                    # Add error message
                    error_msg = props.chat_messages.add()
                    error_msg.role = 'AI'
                    error_msg.content = f"Sorry, I encountered an error: {error}"
                    error_msg.timestamp = datetime.now().strftime("%H:%M")
                    error_msg.status = 'ERROR'
                    error_msg.error_msg = error
                    props.is_thinking = False
                    return {
                        'type': 'error',
                        'message': error
                    }
                
                # Add AI message with the conversational response
                ai_msg = props.chat_messages.add()
                ai_msg.role = 'AI'
                ai_msg.content = ai_message  # Use the AI's actual message
                ai_msg.code = code
                ai_msg.timestamp = datetime.now().strftime("%H:%M")
                
                # Auto-execute if enabled
                if props.auto_execute:
                    try:
                        blender_utils.exec_script_in_current_scene(code)
                        ai_msg.status = 'SUCCESS'
                    except Exception as e:
                        ai_msg.status = 'ERROR'
                        ai_msg.error_msg = str(e)
                else:
                    ai_msg.status = 'NONE'
                
                props.is_thinking = False
                
                return {
                    'type': 'new_message',
                    'message': {
                        'role': 'assistant',
                        'content': ai_msg.content,
                        'code': ai_msg.code,
                        'timestamp': ai_msg.timestamp,
                        'status': ai_msg.status
                    }
                }
            except Exception as e:
                props.is_thinking = False
                error_msg = props.chat_messages.add()
                error_msg.role = 'SYSTEM'
                error_msg.content = f"Error: {str(e)}"
                error_msg.timestamp = datetime.now().strftime("%H:%M")
                error_msg.status = 'ERROR'
                
                return {
                    'type': 'message_response',
                    'success': False,
                    'error': str(e)
                }
        
        # Run in main thread and broadcast result
        def run_and_broadcast():
            result = add_message()
            if result:
                # Schedule the broadcast in the event loop
                asyncio.run_coroutine_threadsafe(
                    broadcast_to_clients(result),
                    server_loop
                )
            return None
        
        bpy.app.timers.register(run_and_broadcast, first_interval=0.01)
        
        return {
            'type': 'message_received',
            'status': 'processing'
        }
    
    elif msg_type == 'get_messages':
        # Get all chat messages
        def get_messages():
            props = bpy.context.scene.rm_props
            messages = []
            for msg in props.chat_messages:
                messages.append({
                    'role': msg.role,
                    'content': msg.content,
                    'code': msg.code,
                    'timestamp': msg.timestamp,
                    'status': msg.status,
                    'error_msg': msg.error_msg
                })
            return messages
        
        messages = get_messages()
        return {
            'type': 'messages_list',
            'messages': messages
        }
    
    elif msg_type == 'execute_code':
        # Execute code from specific message
        code = data.get('code', '')
        
        def execute():
            from .blender_addon import blender_utils
            try:
                blender_utils.validate_script(code)
                exec(code, globals())
                return {'success': True}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        result = execute()
        return {
            'type': 'execution_result',
            **result
        }
    
    elif msg_type == 'clear_chat':
        # Clear chat history
        def clear():
            props = bpy.context.scene.rm_props
            props.chat_messages.clear()
        
        bpy.app.timers.register(lambda: clear() or None, first_interval=0.01)
        
        return {
            'type': 'chat_cleared',
            'success': True
        }
    
    else:
        return {
            'type': 'error',
            'message': f'Unknown message type: {msg_type}'
        }


async def broadcast_to_clients(message):
    """Send message to all connected clients"""
    if connected_clients:
        message_json = json.dumps(message)
        await asyncio.gather(
            *[client.send(message_json) for client in connected_clients],
            return_exceptions=True
        )


async def start_server(host='localhost', port=8765):
    """Start WebSocket server"""
    global server_instance, server_running
    
    if not WEBSOCKETS_AVAILABLE or websockets is None:
        print("[RenderMind WebSocket] ERROR: websockets library not available")
        return
    
    server_running = True
    
    print(f"[RenderMind WebSocket] Starting server on ws://{host}:{port}")
    print(f"[RenderMind] websockets version: {websockets.__version__}")
    
    try:
        print(f"[RenderMind] Calling websockets.serve...")
        server_instance = await websockets.serve(handle_client, host, port)
        print(f"[RenderMind WebSocket] ✓ Server started successfully!")
        print(f"[RenderMind] Open web UI at http://localhost:8080")
        print(f"[RenderMind] Waiting for connections...")
        
        # Keep server running forever
        stop_future = asyncio.Future()
        await stop_future
    except OSError as e:
        print(f"[RenderMind WebSocket] ✗ Port error: {e}")
        server_running = False
    except Exception as e:
        print(f"[RenderMind WebSocket] ✗ Server error: {e}")
        import traceback
        traceback.print_exc()
        server_running = False


def run_server_thread():
    """Run server in background thread"""
    global server_loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        server_loop = loop  # Store for broadcasting from timer
        loop.run_until_complete(start_server())
    except Exception as e:
        print(f"[RenderMind WebSocket] Error in server thread: {e}")
        import traceback
        traceback.print_exc()


def start_http_server():
    """Start HTTP server to serve web UI files"""
    global http_server, http_thread
    
    # Get the web_ui directory path
    addon_dir = Path(__file__).parent
    web_ui_dir = addon_dir / "web_ui"
    
    # Change to web_ui directory
    os.chdir(str(web_ui_dir))
    
    class CustomHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            # Suppress HTTP server logs
            pass
    
    try:
        http_server = HTTPServer(('localhost', 8080), CustomHandler)
        print(f"[RenderMind HTTP] Server started on http://localhost:8080")
        http_server.serve_forever()
    except Exception as e:
        print(f"[RenderMind HTTP] Error: {e}")


def start_websocket_server():
    """Start WebSocket and HTTP servers in background threads"""
    global server_thread, http_thread, server_running
    
    if server_running:
        print("[RenderMind] Server already running")
        return
    
    server_running = True
    
    # Start WebSocket server
    try:
        server_thread = threading.Thread(target=run_server_thread, daemon=True)
        server_thread.start()
        print("[RenderMind] WebSocket server thread started")
    except Exception as e:
        print(f"[RenderMind] Failed to start WebSocket server: {e}")
        server_running = False
        return
    
    # Start HTTP server
    try:
        http_thread = threading.Thread(target=start_http_server, daemon=True)
        http_thread.start()
        print("[RenderMind] HTTP server thread started")
    except Exception as e:
        print(f"[RenderMind] Failed to start HTTP server: {e}")


def stop_websocket_server():
    """Stop WebSocket and HTTP servers"""
    global server_instance, http_server, server_running
    
    server_running = False
    
    if server_instance:
        server_instance.close()
        print("[RenderMind] WebSocket server stopped")
    
    if http_server:
        http_server.shutdown()
        print("[RenderMind] HTTP server stopped")


# Operators for starting/stopping server
class RM_OT_StartWebServer(bpy.types.Operator):
    """Start RenderMind Web Server"""
    bl_idname = "rm.start_web_server"
    bl_label = "Start Web Server"
    bl_description = "Start WebSocket server for web UI"
    
    def execute(self, context):
        try:
            start_websocket_server()
            self.report({'INFO'}, "WebSocket server started on port 8765")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to start server: {str(e)}")
        return {'FINISHED'}


class RM_OT_StopWebServer(bpy.types.Operator):
    """Stop RenderMind Web Server"""
    bl_idname = "rm.stop_web_server"
    bl_label = "Stop Web Server"
    bl_description = "Stop WebSocket server"
    
    def execute(self, context):
        stop_websocket_server()
        self.report({'INFO'}, "WebSocket server stopped")
        return {'FINISHED'}


class RM_OT_OpenWebUI(bpy.types.Operator):
    """Open Web UI in Browser"""
    bl_idname = "rm.open_web_ui"
    bl_label = "Open Web UI"
    bl_description = "Open RenderMind web interface in default browser"
    
    def execute(self, context):
        import webbrowser
        webbrowser.open('http://localhost:8080')
        self.report({'INFO'}, "Opening web UI in browser")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(RM_OT_StartWebServer)
    bpy.utils.register_class(RM_OT_StopWebServer)
    bpy.utils.register_class(RM_OT_OpenWebUI)


def unregister():
    stop_websocket_server()
    bpy.utils.unregister_class(RM_OT_OpenWebUI)
    bpy.utils.unregister_class(RM_OT_StopWebServer)
    bpy.utils.unregister_class(RM_OT_StartWebServer)
