import bpy
from bpy.types import Operator, Panel
from . import blender_utils

# ---- Modal Chat Window Operator ----
class RM_OT_OpenChatWindow(Operator):
    """Open RenderMind Chat Window"""
    bl_idname = "rm.open_chat_window"
    bl_label = "RenderMind Chat"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=600)
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.rm_props
        
        # Modern chat window design
        layout.ui_units_x = 30
        
        # Header
        header_box = layout.box()
        header_row = header_box.row()
        header_row.label(text="💬 RenderMind AI Assistant", icon='LIGHT_SUN')
        header_row.operator("rm.clear_chat", text="", icon='TRASH')
        
        layout.separator()
        
        # Chat messages area (scrollable)
        chat_box = layout.box()
        chat_box.label(text="Conversation")
        
        # Messages column
        col = chat_box.column(align=True)
        col.scale_y = 0.9
        
        if len(props.chat_messages) == 0:
            empty_box = col.box()
            empty_box.label(text="👋 Hi! I'm RenderMind, your AI assistant for Blender.", icon='INFO')
            empty_box.label(text="Tell me what you want to create and I'll generate the code!")
        else:
            # Display messages
            for msg in props.chat_messages:
                msg_box = col.box()
                
                # Message header
                header = msg_box.row()
                if msg.role == 'USER':
                    header.label(text="You", icon='USER')
                else:
                    header.label(text="RenderMind AI", icon='LIGHT_SUN')
                header.label(text=msg.timestamp)
                
                # Message content
                content_col = msg_box.column(align=True)
                for line in msg.content.split('\n')[:8]:
                    content_col.label(text=line)
                
                # Code block if available
                if msg.code and msg.role == 'AI':
                    code_row = msg_box.row(align=True)
                    code_row.prop(msg, "show_code", 
                        icon='TRIA_DOWN' if msg.show_code else 'TRIA_RIGHT',
                        text="Show Code", toggle=True)
                    
                    if msg.show_code:
                        code_box = msg_box.box()
                        code_lines = msg.code.split('\n')[:12]
                        for line in code_lines:
                            code_box.label(text=line, icon='BLANK1')
                    
                    # Action buttons
                    actions = msg_box.row(align=True)
                    actions.operator("rm.run_message_code", text="Run Code", icon='PLAY')
                    actions.operator("rm.copy_message_code", text="Copy", icon='COPYDOWN')
                
                # Status
                if msg.status == 'SUCCESS':
                    msg_box.label(text="✓ Executed successfully", icon='CHECKMARK')
                elif msg.status == 'ERROR':
                    error_box = msg_box.box()
                    error_box.alert = True
                    error_box.label(text=f"✗ Error: {msg.error_msg}", icon='ERROR')
        
        layout.separator()
        
        # Input area
        input_box = layout.box()
        input_box.label(text="Your Message:", icon='GREASEPENCIL')
        
        # Text input
        input_box.prop(props, "chat_input", text="")
        
        # Character counter
        char_row = input_box.row()
        char_row.scale_y = 0.7
        char_row.label(text=f"{len(props.chat_input)} / 4096 chars")
        
        # Send button
        send_row = input_box.row()
        send_row.scale_y = 1.3
        send_row.enabled = len(props.chat_input.strip()) > 0
        send_op = send_row.operator("rm.send_message", text="Send Message", icon='PLAY')
        
        # Quick actions
        quick_box = input_box.box()
        quick_box.label(text="Quick Actions:")
        quick_row = quick_box.row(align=True)
        quick_row.operator("rm.quick_action", text="Create", icon='MESH_CUBE').action = 'CREATE'
        quick_row.operator("rm.quick_action", text="Modify", icon='MODIFIER').action = 'MODIFY'
        quick_row.operator("rm.quick_action", text="Material", icon='MATERIAL').action = 'MATERIAL'
        
        layout.separator()
        
        # Settings (compact)
        settings_box = layout.box()
        settings_row = settings_box.row(align=True)
        settings_row.prop(props, "show_settings", 
            icon='TRIA_DOWN' if props.show_settings else 'TRIA_RIGHT',
            text="Settings", toggle=True, emboss=False)
        
        if props.show_settings:
            settings_content = settings_box.column(align=True)
            
            # Provider
            row = settings_content.row(align=True)
            row.label(text="AI Provider:")
            row.prop(props, "provider", text="")
            
            # Model
            settings_content.prop(props, "model_name", text="Model")
            
            # Temperature
            settings_content.prop(props, "temperature", text="Creativity", slider=True)
            
            # Auto-execute
            settings_content.prop(props, "auto_execute", text="Auto-execute code")


# ---- Simple Sidebar Panel ----
class RM_PT_SimpleLauncher(Panel):
    """Simple launcher panel in sidebar"""
    bl_label = "RenderMind Copilot"
    bl_idname = "RM_PT_simple_launcher"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "RenderMind"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.rm_props
        
        # Logo/Title
        title_box = layout.box()
        title_col = title_box.column(align=True)
        title_col.scale_y = 1.2
        title_col.label(text="RenderMind AI", icon='LIGHT_SUN')
        title_col.label(text="Copilot for Blender")
        
        layout.separator()
        
        # Main button to open chat
        main_btn = layout.column()
        main_btn.scale_y = 2.0
        main_btn.operator("rm.open_chat_window", text="Start Building", icon='PLAY')
        
        layout.separator()
        
        # Web UI section (if websockets available)
        try:
            web_box = layout.box()
            web_box.label(text="Web Interface:", icon='URL')
            web_col = web_box.column(align=True)
            web_col.operator("rm.start_web_server", text="Start Web Server", icon='PLAY')
            web_col.operator("rm.stop_web_server", text="Stop Web Server", icon='PAUSE')
            web_col.operator("rm.open_web_ui", text="Open Web UI", icon='URL')
        except:
            pass
        
        layout.separator()
        
        # Quick stats
        stats_box = layout.box()
        stats_box.label(text="Session Stats:", icon='INFO')
        stats_box.label(text=f"Messages: {len(props.chat_messages)}")
        
        # Display provider with custom name
        provider_name = "RenderMind AI" if props.provider == 'OPENAI' else props.provider
        stats_box.label(text=f"Provider: {provider_name}")
        
        # Quick actions
        layout.separator()
        layout.label(text="Quick Actions:")
        col = layout.column(align=True)
        col.operator("rm.quick_action", text="Create Object", icon='MESH_CUBE').action = 'CREATE'
        col.operator("rm.quick_action", text="Modify Scene", icon='MODIFIER').action = 'MODIFY'
        col.operator("rm.quick_action", text="Add Material", icon='MATERIAL').action = 'MATERIAL'
        
        # Settings toggle
        layout.separator()
        layout.prop(props, "show_settings", text="Show Settings", toggle=True, icon='PREFERENCES')
        
        if props.show_settings:
            settings_box = layout.box()
            settings_box.label(text="AI Settings", icon='SETTINGS')
            
            # Provider selection
            settings_box.prop(props, "provider", text="Provider")
            
            # RenderMind AI settings
            if props.provider == 'OPENAI':
                col = settings_box.column(align=True)
                
                # Check if API key is in .env
                from .. import model_interface
                env_key = model_interface.load_env_file().get('OPENAI_API_KEY', '')
                
                if env_key:
                    info_box = col.box()
                    info_box.label(text="✓ RenderMind API Key loaded", icon='CHECKMARK')
                else:
                    col.prop(props, "openai_api_key", text="API Key")
                    if not props.openai_api_key:
                        warning = col.box()
                        warning.label(text="⚠ API Key Required", icon='ERROR')
                        warning.label(text="Add to .env file or enter above")
                
                col.prop(props, "model_name", text="Model")
            
            # General settings
            settings_box.prop(props, "temperature", slider=True)
            settings_box.prop(props, "auto_execute", text="Auto-execute code")
        
        # Clear chat
        layout.separator()
        layout.operator("rm.clear_chat", text="Clear Chat History", icon='TRASH')


def register():
    bpy.utils.register_class(RM_OT_OpenChatWindow)
    bpy.utils.register_class(RM_PT_SimpleLauncher)

def unregister():
    bpy.utils.unregister_class(RM_PT_SimpleLauncher)
    bpy.utils.unregister_class(RM_OT_OpenChatWindow)
