# serve/api.py
from flask import Flask, request, jsonify
import os
from model_interface import generate_code

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status":"ok"})

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json() or {}
    instruction = data.get("instruction") or data.get("prompt") or ""
    if not instruction:
        return jsonify({"error":"no instruction provided"}), 400
    res = generate_code(instruction)
    return jsonify(res)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
