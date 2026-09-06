# Codex development guidance

- When `.agents/skills/using-superpowers/SKILL.md` exists, read it before responding or running a command, then follow its skill-selection workflow.
- A skill explicitly named with `$skill-name` is mandatory. Read `.agents/skills/<skill-name>/SKILL.md` before acting.
- Use the Windows PowerShell commands and Python virtual environment documented in this repository.
- If the current tool set has no `apply_patch` tool, make a small, direct edit with PowerShell instead of retrying an unavailable tool.
- Report a test as passing only after its actual command output shows a successful exit and zero failures.
