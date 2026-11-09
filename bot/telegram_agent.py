import base64
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import re
import ssl
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Any, Tuple

SSL_CTX = ssl.create_default_context()
SSL_UNVERIFIED_CTX = ssl._create_unverified_context()


def open_url(req, timeout: int = 25):
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX)
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            return urllib.request.urlopen(req, timeout=timeout, context=SSL_UNVERIFIED_CTX)
        raise


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_path(filename: str, subfolder: str = "") -> str:
    if subfolder:
        candidate = os.path.join(BASE_DIR, subfolder, filename)
        if os.path.exists(candidate):
            return candidate
    root_candidate = os.path.join(BASE_DIR, filename)
    if os.path.exists(root_candidate):
        return root_candidate
    return os.path.join(BASE_DIR, subfolder, filename) if subfolder else root_candidate


TOKEN_FILE = resolve_path(".telegram_token", "bot")
GEMINI_KEY_FILE = resolve_path(".gemini_key", "bot")
WORKOUT_DATA_FILE = resolve_path("workout_data.json", "data")
NOTES_FILE = resolve_path("telegram_notes.json", "memory")
PROJECT_MEMORY_FILE = resolve_path("ProjectMemory.md", "memory")
DECISION_LOG_FILE = resolve_path("DecisionLog.md", "memory")
MASTER_RULES_FILE = resolve_path("MasterRules.md", "rules")

# Per-chat conversation history
CHAT_MEMORY: Dict[int, List[Dict[str, Any]]] = {}

# Per-chat batching (2 seconds) so rapid messages/screenshots/voice notes produce ONE reply
BATCH_LOCK = threading.Lock()
CHAT_BATCH: Dict[int, Dict[str, Any]] = {}
BATCH_DELAY_SEC = 2.0

# Cloud sync flag so Render containers restore Telegram-side notes/updates on wakeup
CLOUD_SYNC_DONE = False
CLOUD_SYNC_LOCK = threading.Lock()


def get_token() -> str:
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def get_gemini_key() -> str:
    if os.path.exists(GEMINI_KEY_FILE):
        with open(GEMINI_KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get("GEMINI_API_KEY", "").strip()


# ==============================================================================
# WORKOUT DATA + PERSISTENT NOTES + TELEGRAM CLOUD STORAGE
# ==============================================================================
def load_workout_data() -> Dict[str, Any]:
    if os.path.exists(WORKOUT_DATA_FILE):
        try:
            with open(WORKOUT_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[lifting] Error loading workout data: {e}", flush=True)
    return {"notes": "Fallback dataset", "current_targets_and_maxes": {}, "workout_logs": []}


def save_workout_data(data: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(WORKOUT_DATA_FILE), exist_ok=True)
        with open(WORKOUT_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[lifting] Error saving workout data: {e}", flush=True)


def load_local_notes() -> Dict[str, Any]:
    default_data = {"notes": [], "rules": [], "workout_updates": {}, "machine_updates": {}, "workout_logs": []}
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in default_data.items():
                if k not in data or not isinstance(data[k], type(v)):
                    data[k] = type(v)(v)
            return data
        except Exception:
            pass
    return default_data


def save_local_notes(data: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(NOTES_FILE), exist_ok=True)
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[lifting] Failed to save local notes: {e}", flush=True)


def save_state_to_telegram_cloud(data: Dict[str, Any]):
    """Persist notes & workout updates in Telegram's cloud under a hidden command scope so Render restarts never lose state."""
    token = get_token()
    if not token:
        return
    try:
        raw_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
        b64_str = base64.b64encode(raw_bytes).decode("ascii")
        chunks = [b64_str[i : i + 240] for i in range(0, len(b64_str), 240)][:95]
        commands = [{"command": f"s{idx}", "description": ch} for idx, ch in enumerate(chunks)]
        res = tg_api(
            token,
            "setMyCommands",
            {
                "commands": commands,
                "scope": {"type": "all_chat_administrators"},
                "language_code": "eo",
            },
        )
        if res.get("ok"):
            print(f"[lifting] Saved state to Telegram cloud ({len(chunks)} chunks).", flush=True)
        else:
            print(f"[lifting] Telegram cloud save rejected: {res}", flush=True)
    except Exception as e:
        print(f"[lifting] Telegram cloud save FAILED: {e}", flush=True)


def apply_cloud_state_to_workout_data(state: Dict[str, Any]):
    w_data = load_workout_data()
    changed = False
    for k, v in state.get("workout_updates", {}).items():
        if w_data.get("current_targets_and_maxes", {}).get(k) != v:
            w_data.setdefault("current_targets_and_maxes", {})[k] = v
            changed = True
    for k, v in state.get("machine_updates", {}).items():
        if w_data.get("machine_settings", {}).get(k) != v:
            w_data.setdefault("machine_settings", {})[k] = v
            changed = True
    existing_logs = {json.dumps(x, sort_keys=True) for x in w_data.get("workout_logs", [])}
    for log_entry in state.get("workout_logs", []):
        s_log = json.dumps(log_entry, sort_keys=True)
        if s_log not in existing_logs:
            w_data.setdefault("workout_logs", []).append(log_entry)
            existing_logs.add(s_log)
            changed = True
    if changed:
        save_workout_data(w_data)


def sync_state_from_telegram_cloud() -> Dict[str, Any]:
    global CLOUD_SYNC_DONE
    local_data = load_local_notes()
    if CLOUD_SYNC_DONE:
        return local_data

    with CLOUD_SYNC_LOCK:
        if CLOUD_SYNC_DONE:
            return load_local_notes()
        token = get_token()
        if not token:
            CLOUD_SYNC_DONE = True
            return local_data
        try:
            res = tg_api(
                token,
                "getMyCommands",
                {
                    "scope": {"type": "all_chat_administrators"},
                    "language_code": "eo",
                },
            )
            cmds = res.get("result", [])
            if cmds and isinstance(cmds, list):
                sorted_cmds = sorted(
                    [c for c in cmds if str(c.get("command", "")).startswith("s")],
                    key=lambda x: int(str(x["command"])[1:] or "0"),
                )
                b64_str = "".join(str(c.get("description", "")) for c in sorted_cmds)
                if b64_str:
                    cloud_data = json.loads(base64.b64decode(b64_str.encode("ascii")).decode("utf-8"))
                    if isinstance(cloud_data, dict):
                        for k in ("notes", "rules", "workout_logs"):
                            existing = {json.dumps(x, sort_keys=True) for x in local_data.get(k, [])}
                            for item in cloud_data.get(k, []):
                                s_item = json.dumps(item, sort_keys=True)
                                if s_item not in existing:
                                    local_data.setdefault(k, []).append(item)
                                    existing.add(s_item)
                        for dict_key in ("workout_updates", "machine_updates"):
                            if isinstance(cloud_data.get(dict_key), dict):
                                local_data.setdefault(dict_key, {}).update(cloud_data[dict_key])
                        save_local_notes(local_data)
                        apply_cloud_state_to_workout_data(local_data)
                        print("[lifting] Restored persistent state from Telegram cloud.", flush=True)
        except Exception as e:
            print(f"[lifting] Cloud sync warning: {e}", flush=True)
        CLOUD_SYNC_DONE = True
    return local_data


def append_project_note(note_text: str, category: str = "note"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    data = sync_state_from_telegram_cloud()
    entry = {"timestamp": ts, "text": note_text.strip()}
    if category == "rule":
        data.setdefault("rules", []).append(entry)
    else:
        data.setdefault("notes", []).append(entry)
    save_local_notes(data)
    threading.Thread(target=save_state_to_telegram_cloud, args=(data,), daemon=True).start()

    try:
        if os.path.exists(DECISION_LOG_FILE):
            with open(DECISION_LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            line = f"- [Telegram {ts}] {note_text.strip()}\n"
            if "## Telegram Updates" in content:
                content = content.replace("## Telegram Updates\n", f"## Telegram Updates\n{line}", 1)
            else:
                content = content.rstrip() + f"\n\n## Telegram Updates\n{line}"
            with open(DECISION_LOG_FILE, "w", encoding="utf-8") as f:
                f.write(content)
    except Exception as e:
        print(f"[lifting] Failed to append to DecisionLog.md: {e}", flush=True)


# ==============================================================================
# PROJECT CONTEXT LOADER
# ==============================================================================
def read_file_safe(rel_path: str, max_chars: int = 25000) -> str:
    full = os.path.join(BASE_DIR, rel_path)
    if not os.path.exists(full):
        return ""
    try:
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            text = f.read().strip()
        if len(text) > max_chars:
            return text[:max_chars] + "\n...[truncated]..."
        return text
    except Exception:
        return ""


def build_project_context() -> str:
    notes_data = sync_state_from_telegram_cloud()
    sections: List[str] = []

    core_files = [
        ("rules/MasterRules.md", 15000),
        ("memory/ProjectMemory.md", 15000),
        ("memory/DecisionLog.md", 10000),
        ("data/workout_data.json", 25000),
    ]
    for rel, limit in core_files:
        content = read_file_safe(rel, max_chars=limit)
        if content:
            sections.append(f"=== {rel} ===\n{content}")

    if notes_data.get("rules") or notes_data.get("notes"):
        sections.append(
            "=== Persistent Telegram Notes & Rule Additions ===\n"
            + json.dumps({"rules": notes_data.get("rules", []), "notes": notes_data.get("notes", [])}, indent=2)
        )

    return "\n\n".join(sections)


# ==============================================================================
# GEMINI API CALLER
# ==============================================================================
def call_gemini_generate(payload: Dict[str, Any], timeout_sec: int = 75) -> str:
    key = get_gemini_key()
    models = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"]
    bad_models = set()
    last_err = None

    for attempt in range(2):
        for model_name in models:
            if model_name in bad_models:
                continue
            req_payload = json.loads(json.dumps(payload))
            if attempt == 1 and "thinkingConfig" in req_payload.get("generationConfig", {}):
                req_payload["generationConfig"].pop("thinkingConfig", None)
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(req_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with open_url(req, timeout=timeout_sec) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                cand_parts = res["candidates"][0]["content"]["parts"]
                visible_texts = [p["text"] for p in cand_parts if "text" in p and not p.get("thought")]
                if not visible_texts:
                    visible_texts = [p["text"] for p in cand_parts if "text" in p]
                return "\n".join(visible_texts).strip()
            except urllib.error.HTTPError as he:
                last_err = he
                if he.code in (400, 404):
                    bad_models.add(model_name)
                    continue
                time.sleep(1.0)
            except Exception as e:
                last_err = e
                time.sleep(1.0)
                continue
    raise RuntimeError(f"Gemini API error: {last_err}")


def ask_gemini(
    user_text: str,
    chat_id: int,
    image_paths: List[str] = None,
    audio_items: List[Tuple[str, str]] = None,
) -> str:
    if image_paths and not (user_text or "").strip() and not audio_items:
        # Rule: Image sent with no text -> reply "I need more context." while keeping image in memory
        if chat_id not in CHAT_MEMORY:
            CHAT_MEMORY[chat_id] = []
        img_parts: List[Dict[str, Any]] = []
        for img_path in image_paths:
            if img_path and os.path.exists(img_path):
                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                img_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
        img_parts.append({"text": "[User uploaded image without text]"})
        CHAT_MEMORY[chat_id].append({"role": "user", "parts": img_parts})
        CHAT_MEMORY[chat_id].append({"role": "model", "parts": [{"text": "I need more context."}]})
        return "I need more context."

    project_context = build_project_context()

    if chat_id not in CHAT_MEMORY:
        CHAT_MEMORY[chat_id] = []
    history = CHAT_MEMORY[chat_id]

    today_str = datetime.now().strftime("%Y-%m-%d")
    system_prompt = (
        f"Current Date: {today_str}\n"
        "You are Aaron Millard's personal Weightlifting Tracker Assistant on Telegram.\n"
        "You have full access to his entire Weightlifting Tracker repository (`rules/MasterRules.md`, `memory/ProjectMemory.md`, `memory/DecisionLog.md`, and `data/workout_data.json`).\n\n"
        "CRITICAL RULES (FOLLOW AT ALL TIMES):\n"
        "1. RULE #1 (SHORT AS HUMANLY POSSIBLE & NO ASTERISKS): Every response must be as short, direct, and scannable as humanly possible. Use dashes (`-`) for bullets, zero fluff, no intros/outros, and NEVER use markdown asterisks (`*` or `**`).\n"
        "2. IDEA-DUMP VS. QUESTION RULE (TOP PRIORITY):
"
        "   - If Aaron includes or starts his message with 'Idea dump' (case-insensitive):
"
        "     Treat it strictly as an idea dump. You MUST reply strictly in this exact format:
"
        "     Okay.

"
        "     Update Summary:
"
        "     - [Ultra-concise 1-2 bullet summary of what was logged/updated in simplest possible format]
"
        "   - If Aaron does NOT say 'Idea dump':
"
        "     Treat the message normally as a question, routine lookup, equipment swap inquiry, or general gym conversation, and reply directly with a clear, helpful answer without the Okay/Summary header.
"
        "3. ASSISTED EXERCISE INVERSION: For assisted dips, assisted pull-ups, and assisted chin-ups, LOWER weight = MORE strength gained (e.g., 40 lb -> 15 lb assist = +25 lbs strength gained).\n"
        "4. DATABASE UPDATES: Whenever Aaron logs a new weight/rep update or machine setting, include a JSON block at the VERY END of your response inside ```json_update ... ``` formatted like:\n"
        "```json_update\n"
        "{\n"
        '  "updates": {"leg_press": {"value": 210.0, "unit": "lbs", "routine_sets": "4 sets, 6-10x, 2-3m"}},\n'
        '  "machine_updates": {},\n'
        '  "new_log": {"date": "' + today_str + '", "exercise": "leg_press", "value": 210.0, "unit": "lbs", "delta_from_baseline": "+60 lbs"}\n'
        "}\n"
        "```\n"
        "   Note: This ```json_update``` block is stripped automatically before the message reaches Aaron. NEVER leave raw json visible.\n\n"
        f"{project_context}"
    )

    parts: List[Dict[str, Any]] = []
    for img_path in (image_paths or []):
        if img_path and os.path.exists(img_path):
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})

    for aud_path, mime_type in (audio_items or []):
        if aud_path and os.path.exists(aud_path):
            with open(aud_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            parts.append({"inline_data": {"mime_type": mime_type, "data": b64}})

    default_prompt = (
        "Listen to this voice memo and respond following MasterRules.md."
        if audio_items
        else "Read the image(s) and respond following MasterRules.md."
    )
    parts.append({"text": user_text or default_prompt})

    trimmed_history: List[Dict[str, Any]] = []
    recent_slice = list(history[-12:])
    for idx, turn in enumerate(recent_slice):
        if idx < len(recent_slice) - 4:
            text_only_parts = [p for p in turn.get("parts", []) if "text" in p]
            if not text_only_parts:
                text_only_parts = [{"text": "[Earlier Media Upload]"}]
            trimmed_history.append({"role": turn["role"], "parts": text_only_parts})
        else:
            trimmed_history.append(turn)

    contents = trimmed_history + [{"role": "user", "parts": parts}]
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "thinkingConfig": {"thinkingBudget": 1024},
        },
    }

    reply = call_gemini_generate(payload, timeout_sec=75)

    # Apply any json_update block to workout_data.json and Telegram cloud state
    if "```json_update" in reply:
        try:
            m = re.search(r"```json_update\s*(\{.*?\})\s*```", reply, re.DOTALL)
            if m:
                update_payload = json.loads(m.group(1))
                w_data = load_workout_data()
                notes_state = sync_state_from_telegram_cloud()
                if isinstance(update_payload.get("updates"), dict):
                    for k, v in update_payload["updates"].items():
                        w_data.setdefault("current_targets_and_maxes", {})[k] = v
                        notes_state.setdefault("workout_updates", {})[k] = v
                if isinstance(update_payload.get("machine_updates"), dict):
                    for k, v in update_payload["machine_updates"].items():
                        w_data.setdefault("machine_settings", {})[k] = v
                        notes_state.setdefault("machine_updates", {})[k] = v
                if isinstance(update_payload.get("new_log"), dict):
                    w_data.setdefault("workout_logs", []).append(update_payload["new_log"])
                    notes_state.setdefault("workout_logs", []).append(update_payload["new_log"])
                save_workout_data(w_data)
                save_local_notes(notes_state)
                threading.Thread(target=save_state_to_telegram_cloud, args=(notes_state,), daemon=True).start()
        except Exception as e:
            print(f"[lifting] Error parsing json_update: {e}", flush=True)
        # Always aggressively strip json_update blocks even if parsing failed
        reply = re.sub(r"```json_update\s*\{.*?\}\s*```", "", reply, flags=re.DOTALL)
        reply = re.sub(r"```json_update[\s\S]*?```", "", reply)
        reply = reply.strip()

    # Strip any stray asterisks just in case
    reply = reply.replace("**", "")

    history.append({"role": "user", "parts": parts})
    history.append({"role": "model", "parts": [{"text": reply}]})

    s_lower = (user_text or "").strip().lower()
    if reply.strip() in ("Okay.", "Okay") or any(
        s_lower.startswith(p) for p in ("note:", "log:", "remember:", "rule:", "add rule", "save note")
    ):
        if user_text and user_text.strip():
            cat = "rule" if "rule" in s_lower[:15] else "note"
            append_project_note(user_text.strip(), category=cat)

    return reply


# ==============================================================================
# TELEGRAM HTTP HELPERS
# ==============================================================================
def tg_api(token: str, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with open_url(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_message(token: str, chat_id: int, text: str):
    chunks = [text[i : i + 3900] for i in range(0, len(text), 3900)] or [text]
    for chunk in chunks:
        payload: Dict[str, Any] = {"chat_id": chat_id, "text": chunk}
        tg_api(token, "sendMessage", payload)


def download_telegram_file(token: str, file_id: str, suffix: str = ".dat") -> str:
    info = tg_api(token, "getFile", {"file_id": file_id})
    file_path = info["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    fd, local_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    req = urllib.request.Request(url)
    with open_url(req, timeout=30) as resp, open(local_path, "wb") as out_f:
        out_f.write(resp.read())
    return local_path


# ==============================================================================
# BATCHED MESSAGE, PHOTO & VOICE HANDLER
# ==============================================================================
def flush_chat_batch(token: str, chat_id: int):
    with BATCH_LOCK:
        batch = CHAT_BATCH.pop(chat_id, None)
    if not batch:
        return

    texts: List[str] = batch.get("texts", [])
    photos: List[str] = batch.get("photos", [])
    audios: List[Tuple[str, str]] = batch.get("audios", [])
    combined_text = "\n".join(t for t in texts if t).strip()

    try:
        if combined_text.strip().lower() in ("/start", "start"):
            send_message(
                token,
                chat_id,
                "Weightlifting Tracker Bot online.\n"
                "- Log any set/weight update (e.g. 'Leg press up to 210')\n"
                "- Ask for routine (Push, Pull, Legs, Abs)\n"
                "- Ask for machine settings or backup exercises\n"
                "- Send voice memos, screenshots, or idea dumps",
            )
            return

        if combined_text.strip().lower() in ("/clear", "clear memory", "reset chat"):
            CHAT_MEMORY.pop(chat_id, None)
            send_message(token, chat_id, "Chat history cleared.")
            return

        reply = ask_gemini(combined_text, chat_id, image_paths=photos, audio_items=audios)
        send_message(token, chat_id, reply)
        print(f"[lifting] Replied to chat {chat_id} ({len(reply)} chars).", flush=True)
    except Exception as e:
        print(f"[lifting] Error handling chat {chat_id}: {e}", flush=True)
        send_message(token, chat_id, f"Error: {e}")
    finally:
        for p in photos:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        for ap, _ in audios:
            try:
                if os.path.exists(ap):
                    os.remove(ap)
            except Exception:
                pass


def enqueue_turn(
    token: str,
    chat_id: int,
    text: str = "",
    photo_path: str = None,
    audio_item: Tuple[str, str] = None,
):
    with BATCH_LOCK:
        entry = CHAT_BATCH.get(chat_id)
        if not entry:
            entry = {"texts": [], "photos": [], "audios": [], "timer": None}
            CHAT_BATCH[chat_id] = entry
        if entry["timer"] is not None:
            entry["timer"].cancel()
        if text:
            entry["texts"].append(text.strip())
        if photo_path:
            entry["photos"].append(photo_path)
        if audio_item:
            entry["audios"].append(audio_item)
        timer = threading.Timer(BATCH_DELAY_SEC, flush_chat_batch, args=(token, chat_id))
        timer.daemon = True
        entry["timer"] = timer
        timer.start()


def process_update(token: str, upd: Dict[str, Any]):
    if "message" in upd:
        msg = upd["message"]
        cid = msg["chat"]["id"]
        print(f"[lifting] Incoming message in chat {cid}", flush=True)
        if "photo" in msg:
            photo_list = msg["photo"]
            best_photo = photo_list[-2] if len(photo_list) >= 2 else photo_list[-1]
            try:
                local_path = download_telegram_file(token, best_photo["file_id"], suffix=".jpg")
                enqueue_turn(token, cid, text=msg.get("caption", ""), photo_path=local_path)
            except Exception as e:
                send_message(token, cid, f"Error downloading image: {e}")
        elif "voice" in msg:
            voice = msg["voice"]
            mime = voice.get("mime_type", "audio/ogg")
            try:
                local_path = download_telegram_file(token, voice["file_id"], suffix=".ogg")
                enqueue_turn(token, cid, text=msg.get("caption", ""), audio_item=(local_path, mime))
            except Exception as e:
                send_message(token, cid, f"Error downloading voice memo: {e}")
        elif "audio" in msg:
            aud = msg["audio"]
            mime = aud.get("mime_type", "audio/mp4")
            try:
                local_path = download_telegram_file(token, aud["file_id"], suffix=".m4a")
                enqueue_turn(token, cid, text=msg.get("caption", ""), audio_item=(local_path, mime))
            except Exception as e:
                send_message(token, cid, f"Error downloading audio: {e}")
        elif "text" in msg:
            enqueue_turn(token, cid, text=msg["text"])


# ==============================================================================
# WEBHOOK + POLLING SERVER
# ==============================================================================
SEEN_UPDATES = set()


class BotHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/lifting-data.json"):
            w_data = load_workout_data()
            body = json.dumps(w_data, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/lifting") or self.path == "/":
            dash_path = resolve_path("dashboard.html")
            if os.path.exists(dash_path):
                with open(dash_path, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
                return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK - Weightlifting Tracker Telegram Agent is awake")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b"{}"
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
        try:
            upd = json.loads(body.decode("utf-8"))
            uid = upd.get("update_id")
            if uid is not None:
                if uid in SEEN_UPDATES:
                    return
                SEEN_UPDATES.add(uid)
            token = get_token()
            if token:
                threading.Thread(target=process_update, args=(token, upd), daemon=True).start()
        except Exception:
            pass

    def log_message(self, format, *args):
        pass


def keep_alive_loop(external_url: str):
    while True:
        time.sleep(480)
        try:
            req = urllib.request.Request(external_url, headers={"User-Agent": "KeepAlive/1.0"})
            urllib.request.urlopen(req, timeout=10).read()
        except Exception:
            pass


def run_bot():
    token = get_token()
    if not token:
        print("Missing token. Save token to bot/.telegram_token or TELEGRAM_BOT_TOKEN env var.")
        return

    try:
        sync_state_from_telegram_cloud()
    except Exception:
        pass

    port = int(os.environ.get("PORT", "10002"))
    external_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")

    server = HTTPServer(("0.0.0.0", port), BotHTTPHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    if external_url:
        webhook_url = f"{external_url}/webhook"
        try:
            tg_api(token, "setWebhook", {"url": webhook_url})
            print(f"Webhook registered at {webhook_url}", flush=True)
        except Exception as e:
            print(f"Webhook setup failed ({e}), falling back to polling", flush=True)
            external_url = ""

    if external_url:
        if os.environ.get("ENABLE_KEEP_ALIVE", "false").lower() == "true":
            threading.Thread(target=keep_alive_loop, args=(external_url,), daemon=True).start()
        while True:
            time.sleep(3600)
    else:
        try:
            tg_api(token, "deleteWebhook", {})
        except Exception:
            pass
        print("Weightlifting Tracker Telegram polling mode active...", flush=True)
        offset = 0
        while True:
            try:
                res = tg_api(token, "getUpdates", {"offset": offset, "timeout": 25})
                for upd in res.get("result", []):
                    offset = upd["update_id"] + 1
                    process_update(token, upd)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(2)


if __name__ == "__main__":
    run_bot()
