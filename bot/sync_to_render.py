import base64
import hashlib
import hmac
import json
import os
import re
import sys
import zlib

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
        ("data/workout_data.json", 35000),
        ("dashboard.html", 80000),
    ]
    for rel, limit in core_files:
        c = read_rel(rel, limit)
        if c:
            files[rel] = c
    return files


def rebuild_dashboard_data() -> None:
    w_path = os.path.join(BASE_DIR, "data", "workout_data.json")
    d_path = os.path.join(BASE_DIR, "dashboard.html")
    if not os.path.exists(w_path) or not os.path.exists(d_path):
        return
    try:
        with open(w_path, "r", encoding="utf-8") as f:
            w_data = json.load(f)
        with open(d_path, "r", encoding="utf-8") as f:
            html = f.read()

        curr_bw = w_data.get("bodyweight", {}).get("current")
        if isinstance(curr_bw, (int, float)):
            bw_disp = int(curr_bw) if float(curr_bw).is_integer() else round(float(curr_bw), 1)
            diff_peak = round(float(curr_bw) - 187.0, 1)
            diff_july = round(float(curr_bw) - 175.0, 1)
            dp_disp = int(diff_peak) if diff_peak.is_integer() else diff_peak
            dj_disp = int(diff_july) if diff_july.is_integer() else diff_july
            sign_peak = "+" if diff_peak > 0 else ""
            sign_july = "+" if diff_july >= 0 else ""
            html = re.sub(
                r'(<strong id="bw-curr-val">)[^<]*(</strong>)',
                rf"\g<1>{bw_disp} lbs\g<2>",
                html,
            )
            html = re.sub(
                r'(<small id="bw-curr-delta">)[^<]*(</small>)',
                rf"\g<1>{sign_peak}{dp_disp} lbs from peak\g<2>",
                html,
            )
            html = re.sub(
                r'(<div class="bw-summary" id="bw-summary-text">)[^<]*(</div>)',
                rf"\g<1>Started at 175 lbs (July 7) &rarr; Peaked at 187 lbs (+12 lbs bulk) &rarr; Now at {bw_disp} lbs ({sign_peak}{dp_disp} lbs from peak, {sign_july}{dj_disp} lbs net)\g<2>",
                html,
            )
            html = re.sub(
                r"(nov_8_2026_start:\s*[\d.]+,\s*current:\s*)[\d.]+",
                rf"\g<1>{float(curr_bw)}",
                html,
            )

        nov_map = w_data.get("baselines_nov_8_2026", {})
        curr_map = w_data.get("current_targets_and_maxes", {})
        for key, c_obj in curr_map.items():
            if not isinstance(c_obj, dict) or "value" not in c_obj:
                continue
            c_val = c_obj["value"]
            c_str = str(int(c_val)) if float(c_val).is_integer() else str(round(float(c_val), 1))
            n_obj = nov_map.get(key, {})
            n_val = n_obj.get("value") if isinstance(n_obj, dict) else None
            if n_val is not None:
                n_str = str(int(n_val)) if float(n_val).is_integer() else str(round(float(n_val), 1))
                pattern = rf'(\{{\s*key:\s*"{re.escape(key)}"[^\n]*?novVal:\s*)[\d.]+(\s*,\s*currVal:\s*)[\d.]+'
                html = re.sub(pattern, rf"\g<1>{n_str}\g<2>{c_str}", html)
            else:
                pattern = rf'(\{{\s*key:\s*"{re.escape(key)}"[^\n]*?currVal:\s*)[\d.]+'
                html = re.sub(pattern, rf"\g<1>{c_str}", html)

        with open(d_path, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception as e:
        print("Warning: rebuild_dashboard_data failed:", e)


def main():
    try:
        from bot import telegram_agent
        telegram_agent.sync_state_from_telegram_cloud()
    except Exception:
        pass

    rebuild_dashboard_data()

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
    compressed = zlib.compress(raw, level=9)
    encrypted = encrypt_payload(compressed, gemini_key)
    encrypted["compressed"] = True
    with open(VAULT_OUT, "w", encoding="utf-8") as f:
        json.dump(encrypted, f, indent=2)
    print(f"Encrypted {len(payload['files'])} context files + token -> {VAULT_OUT} ({len(raw)} bytes raw -> {len(compressed)} bytes zlib)")


if __name__ == "__main__":
    main()
