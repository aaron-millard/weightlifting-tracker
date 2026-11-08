# Master Rules — Weightlifting Tracker

## RULE #1: SHORT AS HUMANLY POSSIBLE & NO ASTERISK CLUTTER
- Every response must be as short, direct, and scannable as humanly possible.
- Use brief bullet points with dashes (`-`). Zero fluff, no long intros, no recaps unless asked.
- No Markdown Asterisks Clutter: Do not use asterisks (`*` or `**`) for bolding or bullet points when communicating with Aaron. Use clean plain text headers, dashes (`-`), numbers, or blank lines to separate ideas.

## RULE #2: DO ALL HEAVY LIFTING AUTOMATICALLY
- Never ask Aaron to run commands, install tools, create files, edit configs, or click through setups that the agent can execute directly.
- Execute all changes, scripts, and cloud syncs automatically.

## 3. Mandatory Pre-Response & Memory Protocol
1. Always Check First: Before answering, check `rules/MasterRules.md`, `memory/ProjectMemory.md`, `memory/DecisionLog.md`, and `data/workout_data.json`.
2. Never Lose Context: Immediately log any new requirement, rule, or workout update into `data/workout_data.json`, `memory/ProjectMemory.md`, and `memory/DecisionLog.md`.
3. Idea-Dump & Project-Communication Mode (`Okay.`):
   - Whenever Aaron is purely dumping ideas, notes, or requirements without asking a question, OR whenever he explicitly says he does not need a response returned in the chat message, reply ONLY `Okay.` and log his note to persistent storage.
   - Whenever Aaron sends an image or screenshot with no text/caption included, immediately reply `I need more context.` while keeping the image in conversation memory.

## 4. Core Domain & Tracking Rules
1. Assisted Exercise Inversion Rule:
   - For Assisted Dips, Assisted Pull-Ups, and Assisted Chin-Ups, LOWER weight means MORE strength/progress.
   - Example: Going from 40 lbs assist to 15 lbs assist on dips = +25 lbs of real strength gained. Always calculate and frame this positively as a strength gain.
2. Progress Calculation (vs July 7, 2026 Baseline):
   - Whenever Aaron logs a new weight/rep target (e.g. "Moved up to 210 lbs on leg press" or "Assisted dips down to 10 lbs"), calculate:
     1. Change from previous active weight/reps.
     2. Total progress since the July 2026 baseline (`baselines_july_2026`).
     3. Update the active database record (`current_targets_and_maxes` and `workout_logs`).
3. Machine Settings Recall:
   - Provide exact pin/seat settings whenever requested (e.g. Leg Curls: Front 2 / Medium 1 / Top 4-5; Leg Extensions: Back 5 / Front 2) and save any new machine settings Aaron reports.
4. Backup Exercises & Busy Equipment:
   - If a machine/bench is taken or Aaron asks for a swap, give the matching backup exercise and working weight from `backup_workouts` in `data/workout_data.json`.
5. Routine & Split Structure:
   - Day 1: Push (Chest, Shoulders, Triceps)
   - Day 2: Pull (Back, Biceps, Rear Delts)
   - Day 3: Legs (Quads, Hamstrings, Glutes, Calves + Incline Walk)
   - Day 4: Rest / Active Recovery (Stairclimber + Abs 1 or Abs 2 + Stretches)
