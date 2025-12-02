import bpy, traceback, os
from datetime import datetime
from .. import model_interface
from . import plan_emitter, blender_utils

# ---- Modern Chat Operators ----

class RM_OT_SendMessage(bpy.types.Operator):
    """Send a message to the AI and get a response"""
    bl_idname = "rm.send_message"
    bl_label = "Send Message"
    bl_description = "Send your message to RenderMind AI"
    
    def execute(self, context):
        props = context.scene.rm_props
        user_input = props.chat_input.strip()
        
        if not user_input:
            self.report({'WARNING'}, "Please enter a message")
            return {'CANCELLED'}
        
        try:
            # Add user message
            user_msg = props.chat_messages.add()
            user_msg.role = 'USER'
            user_msg.content = user_input
            user_msg.timestamp = datetime.now().strftime("%H:%M")
            
            # Clear input
            props.chat_input = ""
            
            # Set thinking state
            props.is_thinking = True
            
            # Get AI response (now returns code and message)
            code, ai_message, error = model_interface.generate_blender_code(user_input)
            
            if error:
                # Add error message
                error_msg = props.chat_messages.add()
                error_msg.role = 'AI'
                error_msg.content = f"Sorry, I encountered an error: {error}"
                error_msg.timestamp = datetime.now().strftime("%H:%M")
                error_msg.status = 'ERROR'
                error_msg.error_msg = error
                props.is_thinking = False
                self.report({'ERROR'}, error)
                return {'CANCELLED'}
            
            # Add AI response with conversational message
            ai_msg = props.chat_messages.add()
            ai_msg.role = 'AI'
            ai_msg.content = ai_message  # Use the AI's actual message
            ai_msg.code = code
            ai_msg.timestamp = datetime.now().strftime("%H:%M")
            ai_msg.status = 'NONE'
            
            # Auto-execute if enabled
            if props.auto_execute:
                try:
                    blender_utils.exec_script_in_current_scene(code)
                    ai_msg.status = 'SUCCESS'
                    self.report({'INFO'}, "Code generated and executed successfully")
                except Exception as e:
                    ai_msg.status = 'ERROR'
                    ai_msg.error_msg = str(e)
                    self.report({'WARNING'}, f"Execution failed: {str(e)}")
            else:
                self.report({'INFO'}, "Response generated. Click 'Run' to execute.")
            
            props.is_thinking = False
            
        except Exception as e:
            props.is_thinking = False
            traceback.print_exc()
            
            # Add error message
            error_msg = props.chat_messages.add()
            error_msg.role = 'SYSTEM'
            error_msg.content = f"Error: {str(e)}"
            error_msg.timestamp = datetime.now().strftime("%H:%M")
            error_msg.status = 'ERROR'
            
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        
        return {'FINISHED'}


class RM_OT_ClearChat(bpy.types.Operator):
    """Clear all chat messages"""
    bl_idname = "rm.clear_chat"
    bl_label = "Clear Chat"
    bl_description = "Clear all conversation history"
    
    def execute(self, context):
        props = context.scene.rm_props
        props.chat_messages.clear()
        self.report({'INFO'}, "Chat cleared")
        return {'FINISHED'}


class RM_OT_RunMessageCode(bpy.types.Operator):
    """Execute code from a specific message"""
    bl_idname = "rm.run_message_code"
    bl_label = "Run Code"
    bl_description = "Execute the generated code from this message"
    
    message_index: bpy.props.IntProperty()
    
    def execute(self, context):
        props = context.scene.rm_props
        
        if self.message_index >= len(props.chat_messages):
            self.report({'ERROR'}, "Invalid message index")
            return {'CANCELLED'}
        
        msg = props.chat_messages[self.message_index]
        
        if not msg.code:
            self.report({'WARNING'}, "No code to execute")
            return {'CANCELLED'}
        
        try:
            blender_utils.validate_script(msg.code)
            exec(msg.code, globals())
            msg.status = 'SUCCESS'
            msg.error_msg = ""
            self.report({'INFO'}, "Code executed successfully")
        except Exception as e:
            traceback.print_exc()
            msg.status = 'ERROR'
            msg.error_msg = str(e)
            self.report({'ERROR'}, f"Execution failed: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}


class RM_OT_CopyMessageCode(bpy.types.Operator):
    """Copy code from a message to clipboard"""
    bl_idname = "rm.copy_message_code"
    bl_label = "Copy Code"
    bl_description = "Copy the generated code to clipboard"
    
    message_index: bpy.props.IntProperty()
    
    def execute(self, context):
        props = context.scene.rm_props
        
        if self.message_index >= len(props.chat_messages):
            self.report({'ERROR'}, "Invalid message index")
            return {'CANCELLED'}
        
        msg = props.chat_messages[self.message_index]
        
        if not msg.code:
            self.report({'WARNING'}, "No code to copy")
            return {'CANCELLED'}
        
        context.window_manager.clipboard = msg.code
        self.report({'INFO'}, "Code copied to clipboard")
        return {'FINISHED'}


class RM_OT_QuickAction(bpy.types.Operator):
    """Quick action templates for common tasks"""
    bl_idname = "rm.quick_action"
    bl_label = "Quick Action"
    bl_description = "Insert a quick action template"
    
    action: bpy.props.StringProperty()
    
    def execute(self, context):
        props = context.scene.rm_props
        
        templates = {
            'CREATE': "Create a ",
            'MODIFY': "Modify the selected object to ",
            'MATERIAL': "Add a material that "
        }
        
        if self.action in templates:
            props.chat_input = templates[self.action]
        
        return {'FINISHED'}


# ---- Legacy Operators (kept for compatibility) ----

class RM_OT_Generate(bpy.types.Operator):
    bl_idname = "rm.generate_plan"
    bl_label = "Generate Plan"
    bl_description = "Generate plan(s) for the current prompt and create previews"

    def execute(self, context):
        scn = context.scene
        props = scn.rm_props
        prompt = props.prompt_text
        try:
            # main plan
            plan = model_interface.plan_from_prompt(prompt)
            props.plan_text = plan
            # add history item
            h = props.history.add()
            h.prompt = prompt
            h.plan = plan
            h.accepted = False
            # variants
            props.variants.clear()
            variants = model_interface.generate_variants(prompt, n=props.preview_count)
            for i, pv in enumerate(variants):
                v = props.variants.add()
                v.name = f"Variant {i+1}"
                v.plan = pv
                # try to render a thumbnail in a temporary scene
                try:
                    tmp_scene = bpy.data.scenes.new(f"rm_preview_tmp_{i}")
                    bpy.context.window.scene = tmp_scene
                    # clear any default objects
                    for ob in list(tmp_scene.objects):
                        try:
                            bpy.data.objects.remove(ob, do_unlink=True)
                        except Exception:
                            pass
                    # emit script and run
                    script = plan_emitter.emitter_plan_to_script(pv)
                    blender_utils.validate_script(script)
                    # execute script in tmp_scene (note: script uses bpy.ops -> acts on tmp_scene)
                    exec(script, globals())
                    # render thumbnail
                    thumb = blender_utils.temp_thumbnail_path(f"rm_variant_{i}.png")
                    tmp_scene.render.filepath = thumb
                    bpy.ops.render.render(write_still=True, scene=tmp_scene.name)
                    v.thumb_path = thumb
                except Exception as e:
                    v.thumb_path = ""
                    print("Preview generation failed:", e)
                    traceback.print_exc()
                finally:
                    # remove the tmp scene if it exists
                    try:
                        bpy.data.scenes.remove(tmp_scene)
                    except Exception:
                        pass

            self.report({'INFO'}, "Plans and previews generated")
        except Exception as e:
            traceback.print_exc()
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}


class RM_OT_Preview(bpy.types.Operator):
    bl_idname = "rm.preview_plan"
    bl_label = "Preview Plan"
    bl_description = "Run the current plan in a temporary scene and render preview"

    def execute(self, context):
        scn = context.scene
        props = scn.rm_props
        plan = props.plan_text
        try:
            tmp_scene = bpy.data.scenes.new("rm_preview_exec")
            bpy.context.window.scene = tmp_scene
            for ob in list(tmp_scene.objects):
                try:
                    bpy.data.objects.remove(ob, do_unlink=True)
                except Exception:
                    pass
            script = plan_emitter.emitter_plan_to_script(plan)
            blender_utils.validate_script(script)
            exec(script, globals())
            # render
            thumb = blender_utils.temp_thumbnail_path("rm_preview_exec.png")
            tmp_scene.render.filepath = thumb
            bpy.ops.render.render(write_still=True, scene=tmp_scene.name)
            # attempt to open in image editor
            try:
                img = bpy.data.images.load(thumb)
                for area in bpy.context.window.screen.areas:
                    if area.type == 'IMAGE_EDITOR':
                        area.spaces.active.image = img
                        break
            except Exception:
                pass
            # cleanup
            try:
                bpy.data.scenes.remove(tmp_scene)
            except Exception:
                pass
            self.report({'INFO'}, f"Preview rendered: {thumb}")
        except Exception as e:
            traceback.print_exc()
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}


class RM_OT_Apply(bpy.types.Operator):
    bl_idname = "rm.apply_plan"
    bl_label = "Apply Plan"
    bl_description = "Apply current plan to the active scene (commits changes)"

    def execute(self, context):
        scn = context.scene
        props = scn.rm_props
        plan = props.plan_text
        try:
            script = plan_emitter.emitter_plan_to_script(plan)
            blender_utils.validate_script(script)
            # execute in current scene (commits)
            exec(script, globals())
            # mark latest history as accepted
            if len(props.history) > 0:
                props.history[-1].accepted = True
            self.report({'INFO'}, "Plan applied to scene")
        except Exception as e:
            traceback.print_exc()
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}


# Register / unregister
classes = (
    RM_OT_SendMessage,
    RM_OT_ClearChat,
    RM_OT_RunMessageCode,
    RM_OT_CopyMessageCode,
    RM_OT_QuickAction,
    RM_OT_Generate,
    RM_OT_Preview,
    RM_OT_Apply
)

def register():
    for c in classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
