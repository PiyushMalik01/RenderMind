import bpy
import tempfile, os
from datetime import datetime

from bpy.props import StringProperty, BoolProperty, IntProperty, PointerProperty, CollectionProperty, EnumProperty, FloatProperty
from bpy.types import PropertyGroup

# ---- Chat Message Properties ----
class RMChatMessage(PropertyGroup):
    """Represents a single message in the chat conversation"""
    role: EnumProperty(
        name="Role",
        items=[
            ('USER', "User", "User message"),
            ('AI', "AI", "AI response"),
            ('SYSTEM', "System", "System message")
        ],
        default='USER'
    )
    content: StringProperty(name="Message Content", default="")
    code: StringProperty(name="Generated Code", default="")
    timestamp: StringProperty(name="Timestamp", default="")
    status: EnumProperty(
        name="Status",
        items=[
            ('NONE', "None", "No status"),
            ('THINKING', "Thinking", "AI is generating"),
            ('SUCCESS', "Success", "Executed successfully"),
            ('ERROR', "Error", "Execution failed")
        ],
        default='NONE'
    )
    error_msg: StringProperty(name="Error Message", default="")
    show_code: BoolProperty(name="Show Code", default=False)

# ---- Legacy Properties (kept for compatibility) ----
class RMVariant(PropertyGroup):
    name: StringProperty(name="Variant Name", default="Variant")
    plan: StringProperty(name="Plan", default="")
    thumb_path: StringProperty(name="Thumb Path", default="")

class RMHistoryItem(PropertyGroup):
    prompt: StringProperty(name="Prompt", default="")
    plan: StringProperty(name="Plan", default="")
    accepted: BoolProperty(name="Accepted", default=False)

class RMProps(PropertyGroup):
    # Chat interface properties
    chat_messages: CollectionProperty(type=RMChatMessage)
    chat_input: StringProperty(name="Chat Input", default="", maxlen=4096)
    is_thinking: BoolProperty(name="AI Thinking", default=False)
    show_settings: BoolProperty(name="Show Settings", default=False)
    
    # AI Settings
    provider: EnumProperty(
        name="Provider",
        items=[
            ('OPENAI', "RenderMind AI", "Use RenderMind AI Model"),
            ('OLLAMA', "Ollama", "Use local Ollama")
        ],
        default='OPENAI'
    )
    openai_api_key: StringProperty(
        name="RenderMind API Key",
        description="Your RenderMind API key",
        default="",
        subtype='PASSWORD'
    )
    model_name: StringProperty(name="Model", default="rendermind-v1")
    temperature: FloatProperty(name="Temperature", default=0.7, min=0.0, max=2.0)
    auto_execute: BoolProperty(name="Auto Execute", default=True)
    show_advanced: BoolProperty(name="Show Advanced", default=False)
    
    # Legacy properties (kept for compatibility)
    prompt_text: StringProperty(name="Prompt Text", default="Create a vase", maxlen=1024)
    plan_text: StringProperty(name="Plan Text", default="")
    preview_count: IntProperty(name="Preview Count", default=2, min=1, max=4)
    show_plan: BoolProperty(name="Show Plan", default=True)
    variants: CollectionProperty(type=RMVariant)
    history: CollectionProperty(type=RMHistoryItem)
    variants_index: IntProperty(default=0)
    history_index: IntProperty(default=0)

# ---- Safe execution helpers ----
FORBIDDEN_TOKENS = [
    "import os", "subprocess", "open(", "__import__", "eval(", "exec(", "os.system",
    "bpy.ops.wm.open_mainfile", "bpy.ops.wm.read_homefile"
]

def validate_script(src: str):
    for tok in FORBIDDEN_TOKENS:
        if tok in src:
            raise RuntimeError(f"Unsafe token detected in script: {tok}")

def exec_script_in_current_scene(script_src: str):
    """
    Executes script_src (which must define rendermind_action(context))
    in the current Blender Python environment.
    """
    validate_script(script_src)
    ns = {}
    exec(script_src, ns)
    if "rendermind_action" not in ns:
        raise RuntimeError("Script must define `rendermind_action(context)`")
    ns["rendermind_action"](bpy.context)

def temp_thumbnail_path(name="rm_preview.png"):
    return os.path.join(tempfile.gettempdir(), name)

# ---- Register / unregister for property groups ----
def register():
    bpy.utils.register_class(RMChatMessage)
    bpy.utils.register_class(RMVariant)
    bpy.utils.register_class(RMHistoryItem)
    bpy.utils.register_class(RMProps)
    bpy.types.Scene.rm_props = bpy.props.PointerProperty(type=RMProps)

def unregister():
    if hasattr(bpy.types.Scene, "rm_props"):
        del bpy.types.Scene.rm_props
    bpy.utils.unregister_class(RMProps)
    bpy.utils.unregister_class(RMHistoryItem)
    bpy.utils.unregister_class(RMVariant)
    bpy.utils.unregister_class(RMChatMessage)
