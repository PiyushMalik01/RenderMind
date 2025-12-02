bl_info = {
    "name": "RenderMind Copilot (Dev)",
    "author": "You",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > RenderMind",
    "description": "AI copilot starter for Blender — dev-friendly with hot reload",
    "category": "3D View",
}

import importlib, sys
import os

# Add user site-packages to sys.path for websockets library
user_site_packages = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Python", "Python311", "site-packages")
if os.path.exists(user_site_packages) and user_site_packages not in sys.path:
    sys.path.insert(0, user_site_packages)
    print(f"[RenderMind] Added to path: {user_site_packages}")

# Import from blender_addon package
from .blender_addon import ui_panel_modal, operators, model_library, plan_emitter, dev_reload, blender_utils
from . import model_interface

# Try to import websocket_server (requires 'websockets' library)
HAS_WEBSOCKET = False
try:
    from . import websocket_server
    HAS_WEBSOCKET = True
except ImportError as e:
    print(f"RenderMind: websockets library not found - {e}")
    print("RenderMind: Install with: python -m pip install websockets")

SUBMODULES = ["blender_addon.ui_panel_modal", "blender_addon.operators", "model_interface", 
              "blender_addon.plan_emitter", "blender_addon.dev_reload", "blender_addon.model_library",
              "blender_addon.blender_utils"]
if HAS_WEBSOCKET:
    SUBMODULES.append("websocket_server")

# If reloading during dev, reload submodules so changes are picked up
if __package__:
    for mod in SUBMODULES:
        fq = f"{__package__}.{mod}"
        if fq in sys.modules:
            importlib.reload(sys.modules[fq])

def register():
    # register submodules in order - each has register()/unregister()
    blender_utils.register()
    model_library.register()
    model_interface.register()
    plan_emitter.register()
    operators.register()
    ui_panel_modal.register()
    if HAS_WEBSOCKET:
        websocket_server.register()
    dev_reload.register()

def unregister():
    # unregister in reverse order
    try:
        dev_reload.unregister()
    except Exception:
        pass
    if HAS_WEBSOCKET:
        try:
            websocket_server.unregister()
        except Exception:
            pass
    try:
        ui_panel_modal.unregister()
    except Exception:
        pass
    try:
        operators.unregister()
    except Exception:
        pass
    try:
        plan_emitter.unregister()
    except Exception:
        pass
    try:
        model_interface.unregister()
    except Exception:
        pass
    try:
        model_library.unregister()
    except Exception:
        pass
    try:
        blender_utils.unregister()
    except Exception:
        pass

if __name__ == "__main__":
    register()
