import base64
import hashlib
import hmac
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
DIET_BOT_DIR = r"C:\Users\aaron\OneDrive\Desktop\My Projects\diet-macro-assistant\bot"
VAULT_OUT = os.path.join(DIET_BOT_DIR, "lifting_vault.json")


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_payload(plaintext_bytes: bytes, secret: str) -> dict:
    salt = os.urandom(16)
    nonce = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, 100000, dklen=64)
    enc_key, mac_key = derived[:32], derived[32:]
    stream = _keystream(enc_key, nonce, len(plaintext_bytes))
    ciphertext = bytes(a ^ b for a, b in zip(plaintext_bytes, stream))
    tag = hmac.new(mac_key, salt + nonce + ciphertext, hashlib.sha256).digest()
    return {
        "v": 1,
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ciphertext).decode("ascii"),
        "tag": base64.b64encode(tag).decode("ascii"),
    }


def read_rel(rel_path: str, max_chars: int = 25000) -> str:
    full = os.path.join(BASE_DIR, rel_path)
    if not os.path.exists(full):
        return ""
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        text = f.read().strip()
    if len(text) > max_chars:
        return text[:max_chars] + "\n...[truncated]..."
    return text


def collect_files() -> dict:
    files = {}
    core_files = [
        ("rules/MasterRules.md", 15000),
        ("memory/ProjectMemory.md", 15000),
        ("memory/DecisionLog.md", 10000),
        ("data/workout_data.json", 25000),
    ]
    for rel, limit in core_files:
        c = read_rel(rel, limit)
        if c:
            files[rel] = c
    return files


def main():
    try:
        from bot import telegram_agent
        telegram_agent.sync_state_from_telegram_cloud()
    except Exception:
        pass

    token_path = os.path.join(BASE_DIR, "bot", ".telegram_token")
    key_path = os.path.join(BASE_DIR, "bot", ".gemini_key")
    with open(token_path, "r", encoding="utf-8") as f:
        token = f.read().strip()
    with open(key_path, "r", encoding="utf-8") as f:
        gemini_key = f.read().strip()

    payload = {
        "token": token,
        "files": collect_files(),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encrypted = encrypt_payload(raw, gemini_key)
    with open(VAULT_OUT, "w", encoding="utf-8") as f:
        json.dump(encrypted, f, indent=2)
    print(f"Encrypted {len(payload['files'])} context files + token -> {VAULT_OUT} ({len(raw)} bytes)")


if __name__ == "__main__":
    main()
