# Decision & Session Log — Weightlifting Tracker

## 2026-11-08 — Project Standardized & 24/7 Render Bot Deployed
- Standardized repository layout and rules (`rules/MasterRules.md`, `memory/ProjectMemory.md`, `memory/DecisionLog.md`, `TECHNICAL_BLUEPRINT.md`, `bot/telegram_agent.py`, `bot/sync_to_render.py`) to match `diet-macro-assistant` and `hunting-wabbits`.
- Configured Telegram bot `@WeightliftingTracker_Bot` (`bot/.telegram_token`) and Gemini API key (`bot/.gemini_key`).
- Upgraded `bot/telegram_agent.py` with `gemini-3.5-flash` (and fallback chain), 2.0s per-chat message/photo/voice batching, rolling multimodal conversation memory, `Okay.` Idea-Dump Mode, and `setMyCommands` Telegram cloud persistence.
- Deployed 24/7 webhook route `/lifting-webhook` on `https://macrodave.onrender.com` with encrypted vault `bot/lifting_vault.json` so `@WeightliftingTracker_Bot` runs 24/7 even when the PC is off.
