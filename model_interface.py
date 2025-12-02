"""
Model Interface - Handles AI interactions
Supports OpenAI API and will support local models
"""

import bpy
import json
import os
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("RenderMind: 'requests' library not found. API features will be limited.")


def load_env_file():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / ".env"
    env_vars = {}
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars


def get_api_key():
    """Get RenderMind API key from .env file or scene properties"""
    # Try .env file first
    env_vars = load_env_file()
    api_key = env_vars.get('OPENAI_API_KEY', '')  # Internal use only
    
    # If not in .env, try scene properties
    if not api_key:
        props = bpy.context.scene.rm_props
        api_key = props.openai_api_key
    
    return api_key


def get_model_settings():
    """Get model settings from .env or properties"""
    env_vars = load_env_file()
    props = bpy.context.scene.rm_props
    
    # Map display name to actual model
    display_model = env_vars.get('OPENAI_MODEL') or props.model_name or 'rendermind-v1'
    
    # Use actual OpenAI model internally
    if display_model == 'rendermind-v1':
        model = 'gpt-4o-mini'
    else:
        model = display_model
    
    try:
        temperature = float(env_vars.get('OPENAI_TEMPERATURE', '0.7'))
    except:
        temperature = props.temperature
    
    return model, temperature


def call_openai_api(messages, model="gpt-4o-mini", temperature=0.7):
    """Call RenderMind AI API with messages"""
    if not HAS_REQUESTS:
        return None, "Requests library not installed"
    
    api_key = get_api_key()
    if not api_key:
        return None, "RenderMind API key not set. Please add it in the settings."
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'], None
        else:
            error = f"API Error {response.status_code}: {response.text}"
            return None, error
            
    except Exception as e:
        return None, str(e)


def transcribe_audio(audio_file_path):
    """Transcribe audio using OpenAI Whisper API"""
    if not HAS_REQUESTS:
        return None, "Requests library not installed"
    
    api_key = get_api_key()
    if not api_key:
        return None, "RenderMind API key not set"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        with open(audio_file_path, 'rb') as audio_file:
            files = {
                'file': ('audio.webm', audio_file, 'audio/webm'),
                'model': (None, 'whisper-1')  # Use actual Whisper model
            }
            
            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            return result['text'], None
        else:
            error = f"Speech Recognition Error {response.status_code}: {response.text}"
            return None, error
            
    except Exception as e:
        return None, str(e)


def generate_blender_code(prompt: str, context_meta: dict = None) -> tuple:
    """
    Generate Blender Python code from natural language prompt
    Returns: (code_string, ai_response_text, error_message)
    """
    from .blender_addon import model_library
    
    props = bpy.context.scene.rm_props
    
    # Check if we have a matching model in the library
    # Only use if there's a strong match (score >= 60)
    model_matches = model_library.search_models(prompt)
    
    print(f"[RenderMind] Searching models for: '{prompt}'")
    print(f"[RenderMind] Found {len(model_matches)} matches")
    if model_matches:
        for i, match in enumerate(model_matches[:3]):
            print(f"  {i+1}. {match['filename']} - score: {match['score']}")
    
    if model_matches and model_matches[0]['score'] >= 60:
        # Found a strong matching model - use it
        best_match = model_matches[0]
        print(f"[RenderMind] Using model: {best_match['filename']} (score: {best_match['score']})")
        code = model_library.generate_import_code(best_match, prompt)
        
        # Generic message that doesn't reveal we're using pre-made assets
        ai_message = "I'll create that for you! Here's the code:"
        
        return code, ai_message, None
    
    print(f"[RenderMind] No match found, generating custom code")
    
    # No model found - generate code with AI
    system_prompt = """You are an expert Blender Python scripting assistant. Generate clean, executable Python code for Blender.

IMPORTANT RULES:
1. Always wrap your code in a function called `rendermind_action(context)`
2. Import bpy at the top
3. Use bpy.ops and bpy.data APIs correctly
4. Include error handling where appropriate
5. Add brief comments to explain complex operations
6. Respond with a friendly message followed by the code in a code block

Example response:
"I'll create a cube for you! Here's the code:

```python
import bpy

def rendermind_action(context):
    # Create a cube
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
```
"

Be conversational and helpful!"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Create Blender Python code for: {prompt}"}
    ]
    
    # Add context if available
    if context_meta:
        messages.append({
            "role": "system", 
            "content": f"Current scene context: {json.dumps(context_meta)}"
        })
    
    if props.provider == 'OPENAI':
        model, temperature = get_model_settings()
        full_response, error = call_openai_api(messages, model, temperature)
        if error:
            return None, None, error
        
        # Extract conversational message and code
        ai_message = full_response
        code = full_response
        
        # Extract code from markdown if present
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
            # Get the text before the code block as the message
            ai_message = full_response.split("```python")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()
            ai_message = full_response.split("```")[0].strip()
        
        # If no message before code, create a friendly one
        if not ai_message or ai_message == full_response:
            ai_message = "I've generated the code for you! ✨"
        
        return code, ai_message, None
    
    elif props.provider == 'OLLAMA':
        # TODO: Implement Ollama support
        return None, None, "Ollama support coming soon!"
    
    else:
        # Fallback to demo code
        return generate_demo_code(prompt), "Here's a simple example:", None


def generate_demo_code(prompt: str) -> str:
    """Generate simple demo code for testing"""
    p = prompt.lower()
    
    if "cube" in p or "box" in p:
        return """import bpy

def rendermind_action(context):
    # Create a cube
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
    cube = bpy.context.active_object
    cube.name = "RenderMind_Cube"
"""
    
    elif "sphere" in p or "ball" in p:
        return """import bpy

def rendermind_action(context):
    # Create a sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 1))
    sphere = bpy.context.active_object
    sphere.name = "RenderMind_Sphere"
"""
    
    elif "cylinder" in p or "vase" in p:
        return """import bpy

def rendermind_action(context):
    # Create a cylinder (vase-like)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=2, location=(0, 0, 1))
    cylinder = bpy.context.active_object
    cylinder.name = "RenderMind_Cylinder"
"""
    
    else:
        return """import bpy

def rendermind_action(context):
    # Create a default object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 1))
    obj = bpy.context.active_object
    obj.name = "RenderMind_Object"
"""


# Legacy functions for compatibility
def plan_from_prompt(prompt: str, context_meta: dict = None) -> str:
    """Legacy function - generates code instead of plan"""
    code, error = generate_blender_code(prompt, context_meta)
    if error:
        return f"ERROR: {error}"
    return code


def generate_variants(prompt: str, n: int = 2):
    """Generate multiple code variations"""
    variants = []
    for i in range(n):
        code, error = generate_blender_code(f"{prompt} (variation {i+1})")
        if code:
            variants.append(code)
    return variants if variants else [generate_demo_code(prompt)]


def register():
    pass


def unregister():
    pass
