# serve/model_interface.py
import os, torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

# config picks up env or defaults
BASE_MODEL = os.environ.get("BASE_MODEL", "codellama/CodeLlama-7b-Instruct-hf")
ADAPTER_PATH = os.environ.get("ADAPTER_PATH", "../models/codellama_adapter")  # relative to serve/
HF_TOKEN = os.environ.get("HF_TOKEN", None)
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", 256))
TEMPERATURE = float(os.environ.get("TEMPERATURE", 0.15))

# bitsandbytes 4-bit inference config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16
)

print("MODEL INTERFACE: Loading tokenizer from adapter:", ADAPTER_PATH)
tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH, use_fast=True)
if getattr(tokenizer, "pad_token", None) is None:
    tokenizer.pad_token = tokenizer.eos_token

print("MODEL INTERFACE: Loading base model and attaching adapter (this may take some time)...")
base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    use_auth_token=HF_TOKEN
)
model = PeftModel.from_pretrained(base, ADAPTER_PATH, device_map="auto")
model.eval()
device = next(model.parameters()).device
print("MODEL INTERFACE: model loaded on", device)

# Basic static safety blacklist
BLACKLIST = ["open(", "subprocess", "socket", "eval(", "exec(", "requests", "__import__", "os.system", "os.popen"]

def safety_block(code_str):
    for token in BLACKLIST:
        if token in code_str:
            return True, token
    return False, None

def build_prompt(instr: str) -> str:
    return (
        "You are RenderMind: convert a natural language instruction into Blender Python (bpy) code. "
        "Return ONLY python code inside the function wrapper. Do NOT add explanations.\n\n"
        f"### Instruction:\n{instr}\n\n### Response (Python code only):\n"
    )

def generate_code(instruction: str, max_new_tokens: int = MAX_NEW_TOKENS, temperature: float = TEMPERATURE) -> dict:
    prompt = build_prompt(instruction)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        gen = model.generate(**inputs, max_new_tokens=max_new_tokens, temperature=temperature)
    out = tokenizer.decode(gen[0], skip_special_tokens=True)
    # extract the code after the prompt to remove prompt echo
    code = out.split(prompt, 1)[-1].strip()
    blocked, reason = safety_block(code)
    return {"instruction": instruction, "code": "" if blocked else code, "safety_blocked": blocked, "safety_reason": reason}
