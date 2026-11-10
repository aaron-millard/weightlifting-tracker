# Project Memory — Weightlifting Tracker

Last Updated: 2026-11-08

## 1. Overview & Purpose
- Personal weightlifting tracker and gym assistant for Aaron Millard.
- Tracks progression across two baseline views:
  1. Starting July 7, 2026 (`2026-07-07`): Initial gym start date (4-month historical progression).
  2. Starting November 8, 2026 (`2026-11-08`): Official live tracking start date.
- Bodyweight Progression: Started at 175 lbs (July 7, 2026) -> got up to 187 lbs peak -> 183 lbs on Nov 8 (official tracking start) -> currently 182.6 lbs (Nov 9 weigh-in, -4.4 lbs from peak, +7.6 lbs from start).
- Stairclimber Progression Split:
  - Day 2 (Pull Day): `12:00 mins` at Level 4.
  - Day 4 (Rest / Active Recovery Day): `15:00 mins` at Level 4 (+3 mins vs Nov 8 start, +7 mins vs July start).
- Idea-Dump Rule Updated: Telegram bot replies `Roger Roger.` followed by `Update Summary:` in the simplest possible format. Never outputs raw JSON update blocks to user. Agent granted standing permission to update MasterRules dynamically.
- Strict Project Boundary: This chat and workspace are strictly dedicated to `weightlifting-tracker` only. No cross-project context or references.
- Live 24/7 Cloud Dashboard: `https://macrodave.onrender.com/lifting` (with live JSON data endpoint `https://macrodave.onrender.com/lifting-data.json`) so the dashboard is always accessible even when the PC is closed, and automatically reflects any workouts logged via `@WeightliftingTracker_Bot`.
- Follows the exact same architecture, communication rules (ultra-short, zero fluff, no markdown asterisks), `Roger Roger.` Idea-Dump Mode, and 24/7 Render multi-bot hosting methodology as `diet-macro-assistant` and `hunting-wabbits`.

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

## 4. Active Experiments & Next Session Notes
- Next Leg Day (Day 3 Hinge Trial): Test both the **45° Hyperextension Bench** (with bodyweight or light plate/dumbbell) and the **Seated Back Extension Machine** head-to-head. Compare hamstring/glute stretch vs lower back fatigue, pick the winner, and formally lock it in as the official Day 3 hinge lift.

## 5. System Architecture
- Project Name & GitHub: `weightlifting-tracker` (`https://github.com/DaveMatthews2662/weightlifting-tracker`)
- Workspace Directory: `C:\Users\aaron\OneDrive\Desktop\My Projects\weightlifting-tracker`
- Telegram Bot: `@WeightliftingTracker_Bot` (`weightlifting-tracker-bot`)
- 24/7 Cloud Hosting & Webhook: Hosted on Render at `https://macrodave.onrender.com/weightlifting-tracker-webhook`
- Live 24/7 Cloud Dashboard: `https://macrodave.onrender.com/weightlifting-tracker` (live data: `/weightlifting-tracker-data.json`)
- Encrypted Vault: `bot/weightlifting_tracker_vault.json` (synced via `bot/sync_to_render.py` using PBKDF2-HMAC-SHA256 keyed by `GEMINI_API_KEY`)
- Persistent Cloud State: Stored in Telegram's cloud via `setMyCommands` (`all_chat_administrators`, `language_code: "eo"`) so Render restarts never lose state.
