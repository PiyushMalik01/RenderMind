# RenderMind Copilot

AI-powered Blender assistant with local fine-tuned model support and web-based interface.

## 🏗️ Project Structure

```
rendermind_copilot/
├─ .env                            # Environment variables (API keys, model paths)
├─ requirements.txt                 # Python dependencies
├─ README.md
├─ models/                          # Fine-tuned model adapters (PEFT/LoRA)
│   └─ codellama_adapter/           # Your adapter files go here
│       ├─ adapter_model.safetensors
│       ├─ adapter_config.json
│       └─ tokenizer.json
├─ assets/                          # 3D model library
│   ├─ food/
│   │   ├─ apple.blend
│   │   └─ pomegranate.blend
│   └─ nature/
│       └─ trees.blend
├─ serve/                           # Model serving (Flask API)
│   ├─ __init__.py
│   ├─ model_interface.py           # Load base model + adapter with PEFT
│   ├─ api.py                       # Flask server with /generate endpoint
│   └─ starter.sh                   # Server startup script
├─ web_ui/                          # Browser-based chat interface
│   ├─ index.html
│   ├─ style.css
│   └─ app.js
├─ blender_addon/                   # Blender addon code
│   ├─ __init__.py
│   ├─ operators.py                 # Blender operators
│   ├─ ui_panel_modal.py            # UI panels
│   ├─ model_library.py             # 3D asset management
│   ├─ blender_utils.py             # Blender properties & utilities
│   ├─ client_integration.py        # API client for local model
│   ├─ plan_emitter.py
│   └─ dev_reload.py
├─ tools/                           # Development & testing tools
│   └─ (coming soon)
└─ utils/                           # Shared utilities
    ├─ __init__.py
    └─ safe_filters.py              # Code safety checks
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:
```bash
# OpenAI API (for fallback)
OPENAI_API_KEY=your_key_here

# Local Model Configuration
BASE_MODEL=codellama/CodeLlama-7b-hf
ADAPTER_PATH=./models/codellama_adapter
MODEL_SERVER_URL=http://localhost:5000

# Server Configuration
PORT=5000
```

### 3. Start Model Server (Optional - for local fine-tuned model)

```bash
python -m serve.api
```

This starts a Flask server on port 5000 that serves your fine-tuned model.

### 4. Install Blender Addon

1. Open Blender
2. Edit → Preferences → Add-ons → Install
3. Select this entire folder
4. Enable "RenderMind Copilot (Dev)"

### 5. Use the Web UI

1. In Blender, open RenderMind panel (View3D → Sidebar → RenderMind)
2. Click "Start Web Server"
3. Click "Open Web UI"
4. Start chatting!

## 📦 Features

### ✨ Web-Based Chat Interface
- Real-time WebSocket communication with Blender
- Voice input via Whisper API
- Auto-execute generated code
- Beautiful dark theme UI

### 🎨 3D Asset Library
- Automatically imports matching models from `assets/` folder
- Smart keyword matching
- Supports .blend, .fbx, .obj, .gltf, .stl formats

### 🤖 Dual Model Support
1. **OpenAI API** (GPT-4o-mini) - Fast, reliable, cloud-based
2. **Local Fine-Tuned Model** - Your custom CodeLlama adapter

### 🛡️ Safety Features
- Code validation and sanitization
- Dangerous pattern detection
- Import whitelist

## 🔧 Using Your Fine-Tuned Model

### Setup

1. Place your adapter in `models/codellama_adapter/`
2. Update `.env` with correct paths
3. Start the model server: `python -m serve.api`
4. Update Blender addon to use local model

### Adapter Structure

```
models/codellama_adapter/
├─ adapter_model.safetensors     # PEFT/LoRA weights
├─ adapter_config.json            # Adapter configuration
├─ tokenizer.json                 # Tokenizer files
└─ ...
```

## 🎯 Usage Examples

**Using 3D Assets:**
- "add an apple" → Imports `assets/food/apple.blend`
- "create trees" → Imports `assets/nature/trees.blend`

**Generating Code:**
- "create a red cube" → AI generates code
- "make 10 spheres in a circle" → Procedural generation
- "add a camera looking at origin" → Scene setup

**Voice Input:**
- Click microphone button
- Speak your command
- Automatic transcription via Whisper

## 🧪 Development

### Hot Reload
The addon supports hot reload during development. Changes are automatically detected.

### Testing
```bash
# Test model server
curl http://localhost:5000/health

# Test code generation
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"create a cube"}'
```

## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required for OpenAI mode |
| `BASE_MODEL` | HuggingFace model name | `codellama/CodeLlama-7b-hf` |
| `ADAPTER_PATH` | Path to PEFT adapter | `./models/codellama_adapter` |
| `MODEL_SERVER_URL` | Local model server URL | `http://localhost:5000` |
| `PORT` | Flask server port | `5000` |

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test with Blender
5. Submit pull request

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Credits

- Built with Blender Python API
- Powered by OpenAI GPT-4 & Whisper
- Fine-tuning with PEFT/LoRA
- Base model: CodeLlama-7b

---

**Need help?** Check the issues page or create a new issue.
