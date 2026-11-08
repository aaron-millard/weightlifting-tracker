# Project Memory — Weightlifting Tracker

Last Updated: 2026-11-08

## 1. Overview & Purpose
- Personal weightlifting tracker and gym assistant for Aaron Millard.
- Tracks 4-month progression starting from July 7, 2026 baseline (`2026-07-07`) across a 4-day Push / Pull / Legs / Rest+Abs split.
- Follows the exact same architecture, communication rules (ultra-short, zero fluff, no markdown asterisks), `Okay.` Idea-Dump Mode, and 24/7 Render multi-bot hosting methodology as `diet-macro-assistant` and `hunting-wabbits`.

## 2. Key Progression Highlights (July 2026 Baseline -> Nov 2026 Current)
- Push-Ups: 8.5 reps (7-10) -> 25 reps (+16.5 reps)
- Dumbbell Press: 40 lbs -> 55 lbs (+15 lbs)
- Assisted Dips: 40 lbs assist -> 15 lbs assist (+25 lbs real strength gained)
- Incline Press: 30 lbs -> 40 lbs (+10 lbs)
- Shoulder Press: 30 lbs -> 40 lbs (+10 lbs)
- Assisted Pull-Ups: 70 lbs assist -> 45 lbs assist (+25 lbs real strength gained)
- Assisted Chin-Ups: 50 lbs assist -> 35 lbs assist (+15 lbs real strength gained)
- Dumbbell / Hammer Curls: 22.5 lbs -> 30 lbs (+7.5 lbs)
- Hack Squats: 135 lbs -> 155 lbs (+20 lbs)
- Leg Press: 150 lbs -> 200 lbs (+50 lbs)
- Leg Curls: 60 lbs -> 75 lbs (+15 lbs)
- Leg Extensions: 120 lbs -> 140 lbs (+20 lbs)
- Decline Sit-Ups / Sit-Ups: 0 lbs -> 15 lbs weighted (+15 lbs)
- Stairclimber: Level 4 for 8 mins -> Level 4 for 12 mins (+4 mins)

## 3. Machine Settings
- Leg Curls: Front 2 | Medium 1 | Top 4-5
- Leg Extension: Back 5 | Front 2

## 4. System Architecture
- Workspace: `C:\Users\aaron\OneDrive\Desktop\My Projects\weightlifting-tracker`
- Telegram Bot: `@WeightliftingTracker_Bot` (`weightlifting-tracker-bot`)
- 24/7 Cloud Hosting: Hosted on Render at `https://macrodave.onrender.com/lifting-webhook` alongside the Macro and Hunting Wabbits bots on the single 24/7 Render container.
- Encrypted Vault (`bot/lifting_vault.json` in `diet-macro-assistant` via `bot/sync_to_render.py`): Encrypts `MasterRules.md`, `ProjectMemory.md`, `DecisionLog.md`, `workout_data.json`, and the bot token using PBKDF2-HMAC-SHA256 keyed by `GEMINI_API_KEY`.
- Persistent Cloud State: Runtime workout logs, weight updates, machine settings, and idea-dump notes are persisted in Telegram's cloud via `setMyCommands` (`all_chat_administrators`, `language_code: "eo"`) so Render restarts never lose state.
