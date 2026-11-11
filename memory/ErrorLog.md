# Error & Mistake Log — Weightlifting Tracker

This document is the permanent, continuous log of user corrections, agent errors, prompt regressions, and architectural mistakes across the `weightlifting-tracker` project.

> **Permanent Continuous Logging Rule:** Whenever Aaron corrects the agent, flags a mistake, notes a forgotten rule, or a process fails, it must be appended here immediately before replying. Never let an error go unrecorded.

---

## 1. Harvested Errors, User Corrections & Failures

### 2026-11-09 — Telegram Bot Outputted Raw JSON Mutation Block in Chat
- **Timestamp:** 2026-11-09 07:49 (from Telegram session at 07:07 AM)
- **What Went Wrong & What Aaron Said:**
  - Aaron texted a routine update on the stairclimber: *"I wanna start tracking my stair climber as two separate units or measurements..."*
  - The bot echoed internal database mutation syntax (`json_update { ... }`) directly into the Telegram conversation instead of stripping it cleanly.
  - Aaron followed up with: *"Did you not get these notes or idea dumps that I sent while I was at the gym? The point of the Telegram agent is that I'm going to say in the beginning, 'This is an idea dump,' and you just reply 'Okay,' and give a simple summary of the update."*
- **Root Cause:** Incomplete regex parsing in the response post-processing loop; the bot payload returned before stripping the trailing markdown code fence.
- **Current Status:** **Resolved**. Implemented aggressive regex stripping (`re.sub(r"```json_update[\s\S]*?```", "", reply)`) in both local `bot/telegram_agent.py` and Render cloud `bot/lifting_agent.py`.

---

### 2026-11-09 — Ambiguous Trigger for "Idea Dump" vs. Questions/Lookups
- **Timestamp:** 2026-11-09 08:02
- **What Went Wrong & What Aaron Said:**
  - The bot was initially guessing whether a user message was an idea dump or a question based on conversational context, occasionally giving full explanatory answers when Aaron just wanted a quick log, or treating lookups too rigidly.
  - Aaron instructed: *"Also, on the Telegram bot again, let's just do a thing where if it's an idea dump, I'll just say 'Idea dump' every time. If I don't say 'Idea dump,' you can consider it a question or whatever."*
- **Root Cause:** Lack of an explicit, deterministic string trigger rule in `MasterRules.md` and the bot's system prompt.
- **Current Status:** **Resolved**. Established hard case-insensitive trigger: messages starting with or containing "Idea dump" strictly receive the acknowledgment format; all other messages receive direct, helpful answers.

---

### 2026-11-09 — Cross-Project Context Bleed
- **Timestamp:** 2026-11-09 07:56
- **What Went Wrong & What Aaron Said:**
  - During early initialization and setup, the agent referenced files and architectures from sibling projects (`hunting-wabbits`, `diet-macro-assistant`).
  - Aaron firmly instructed: *"Unless I ever say otherwise, this chat and project should always stick to our weight-lifting-tracker project and not the other projects I have in my git or my files."*
- **Root Cause:** Over-reliance on cross-project blueprints during initial repo templating without setting a strict boundary rule.
- **Current Status:** **Resolved**. Codified Rule #3 (*Strict Project Boundary: Weightlifting Tracker Only*) in `MasterRules.md` and `ProjectMemory.md`.

---

### 2026-11-10 — Failure to Use "Roger Roger" Affirmation on Initial Turn
- **Timestamp:** 2026-11-10 09:45
- **What Went Wrong & What Aaron Said:**
  - Aaron gave an explicit directive: *"For any rules where I asked you to just reply 'Okay', such as but not limited to the telegram idea dumps, change it to 'Roger Roger'. And whenever I do ask you to reply just ok or okay, actually respond with 'Roger Roger'."*
  - The agent executed file changes in the background without acknowledging with "Roger Roger." directly in the initial reply turn.
  - Aaron replied: *"try again"*.
- **Root Cause:** Background task output interrupted the final direct response turn, causing the assistant to miss emitting the immediate user-mandated affirmation.
- **Current Status:** **Resolved**. Acknowledged with "Roger Roger." and codified across all agent prompts, `MasterRules.md`, and memory files.

---

### 2026-11-10 — Premature Assumptions / Making File Changes Without Approval
- **Timestamp:** 2026-11-10 20:52
- **What Went Wrong & What Aaron Said:**
  - Aaron observed the agent autonomously applying file changes after conversational turns.
  - Aaron established: *"New rule. I want you to ask me before ever making changes. Dont assume I want something. Unless I say go, or execute, ask me first."*
  - Followed by the formal project specification: *"Never assume I want something changed. Never modify files, code, configs, or system settings until I explicitly say 'go' or 'execute'. When I say 'go' or 'execute', do all the heavy lifting directly."*
- **Root Cause:** Previous standing rule granted "Autonomous Rule Evolution" which conflicted with the required confirmation-first discipline.
- **Current Status:** **Resolved**. Formally codified Rule #2 (*Mandatory Approval & Heavy Lifting Upon Approval*) and established **Backlog** vs. **Staging** in `MasterRules.md` and `ProjectMemory.md`.

---

## 2. Redundancy & Sprawl Inventory

The following potential redundancies, duplicate trackers, and overlapping files were identified during the audit:

1. **`telegram_agent.py` (Root) vs. `bot/telegram_agent.py`:**
   - `telegram_agent.py` in the root is an 81-byte shim that simply imports `from bot.telegram_agent import run_bot`.
   - *Status:* Benign structural shim (required for standard Render entrypoint compatibility), but represents a two-file entrypoint pattern.
2. **`requirements.txt` (Root) vs. `bot/requirements.txt`:**
   - Both files contain identical 70-byte content (`# No external packages required (uses Python 3 standard library only)`).
   - *Status:* Harmless redundancy, but duplicated across root and `bot/`.
3. **Double Ingestion of Workout Split (`data/workout_data.json` vs. `dashboard.html` embedded JS):**
   - Routine data, pin settings, rep counts, and exercise targets are maintained in `data/workout_data.json`, but a static fallback copy is also hardcoded inside `<script>` in `dashboard.html`.
   - *Risk:* If `workout_data.json` is edited without regenerating or fetching live cloud JSON, local `dashboard.html` opened via `file://` can display slightly divergent targets from the live server.
4. **Duplicate Repetition Tracking in `ProjectMemory.md` vs. `data/workout_data.json`:**
   - Exact set, rep, and weight targets are fully documented in Section 6 of `ProjectMemory.md` and simultaneously stored in structured form in `data/workout_data.json`.
   - *Status:* Manageable, but requires atomic dual updates whenever routine numbers change.
5. **Redundant Stairclimber Keys in Database:**
   - `workout_data.json` contains `stairclimber` (legacy singular entry: `12:00, Level 4`), `stairclimber_pull` (`12:00, Level 4`), and `stairclimber_rest` (`15:00, Level 4`).
   - *Status:* Legacy `stairclimber` key remains in fallback dictionaries for backward compatibility, but active logic uses the split keys.

---

## 3. Standard Action Commands Reference
- **"pull backlog"** &rarr; Displays current exploratory ideas, brainstorms, and gym dumps.
- **"pull staging"** &rarr; Displays pending concrete changes paused waiting for "go" or "execute".
- **"pull error log"** &rarr; Displays this document's top recurring mistakes and active rules to avoid repeating past errors.
