# Weightlifting Tracker Workspace Rules

## 1. Two-Beat Confirmation Rule & Staging Gate
- Never modify, delete, or overwrite files, code, configs, or system settings during an audit, diagnosis, or explanation turn.
- Always stage proposed changes in Staging first, explain clearly what will be done, and ask: "Ready to execute?".
- Only execute file or system changes when Aaron explicitly replies "go", "execute", or "3".

## 2. Heavy Lifting Upon Approval
- Once approved with "go", "execute", or "3", do all the heavy lifting directly.
- Never instruct Aaron to run shell commands, manually edit configs, or update files himself. Execute all edits, script runs, and cloud syncs autonomously.

## 3. Continuous Error Logging
- Whenever Aaron corrects the agent, flags a mistake, or points out a forgotten rule, automatically append the incident, root cause, and resolution to `memory/ErrorLog.md` before replying.
- Never let an error go unrecorded.

## 4. No Asterisk Clutter
- Never use asterisks (* or **) for bolding or bullet points in chat communications with Aaron.
- Use clean dashes (-), numbers, blank lines, or plain text headers to structure messages and lists.
- Use explicit double line breaks between list items and paragraphs so text never collapses into unreadable blocks.

## 5. Strict Project Boundary
- Unless Aaron explicitly instructs otherwise, focus exclusively on the `weightlifting-tracker` workspace and project.
- Do not reference or bleed context from sibling projects in responses or memory files.

## 6. Standing Response Affirmation Rule
- Whenever Aaron asks to reply "OK" or "Okay" (or for Telegram idea dumps), always respond with "Roger Roger." instead.

## 7. Numbered Action Command System
Typing the single digit or the phrase triggers the action immediately:
- [1] pull backlog (or 1): Displays current exploratory ideas and Telegram dumps from `memory/ProjectMemory.md`.
- [2] pull staging (or 2): Displays concrete pending changes paused waiting for approval.
- [3] execute staging (or 3): The official green light. Applies all staged changes across files and configs.
- [4] sync all (or 4): Multi-level full sync (local files <-> cloud bot/Render <-> git remote <-> live dashboard).
- [5] pull error log (or 5): Displays the top recurring mistakes and guardrails from `memory/ErrorLog.md`.
- [6] status (or 6): Quick 3-bullet summary of project health, active files, and last sync timestamp.
- [7] list actions (or 7): Displays the numbered action command menu.
