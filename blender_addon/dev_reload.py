import bpy, importlib, sys

class RM_OT_DevReload(bpy.types.Operator):
    bl_idname = "rm.dev_reload"
    bl_label = "Reload RenderMind (Dev)"
    bl_description = "Reload RenderMind addon modules (development helper)"

    def execute(self, context):
        pkg = __package__
        if not pkg:
            self.report({'WARNING'}, "Package not set (use as addon, not run as script)")
            return {'CANCELLED'}
        try:
            # reload all submodules of this package
            for name, mod in list(sys.modules.items()):
                if name.startswith(pkg + "."):
                    importlib.reload(mod)
            # attempt to reload root package as well
            if pkg in sys.modules:
                importlib.reload(sys.modules[pkg])
            # force UI redraw
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
            self.report({'INFO'}, "RenderMind reloaded")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}

def register():
    bpy.utils.register_class(RM_OT_DevReload)

def unregister():
    try:
        bpy.utils.unregister_class(RM_OT_DevReload)
    except Exception:
        pass
