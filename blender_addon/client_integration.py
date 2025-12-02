# blender_addon/client_integration.py
import requests, bpy

SERVER_URL = "http://127.0.0.1:5000/generate"  # change if server remote

def ask_render_mind(instruction, timeout=30):
    try:
        r = requests.post(SERVER_URL, json={"instruction": instruction}, timeout=timeout)
    except Exception as e:
        return None, f"Request failed: {e}"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text}"
    j = r.json()
    if j.get("safety_blocked"):
        return None, f"Blocked: {j.get('safety_reason')}"
    return j.get("code",""), None

def show_code_in_text_editor(code, name="render_mind_generated.py"):
    if name in bpy.data.texts:
        txt = bpy.data.texts[name]
        txt.clear()
    else:
        txt = bpy.data.texts.new(name)
    txt.from_string(code)
    # open the text editor area if present
    for area in bpy.context.screen.areas:
        if area.type == "TEXT_EDITOR":
            area.spaces.active.text = txt
            break
    return txt
