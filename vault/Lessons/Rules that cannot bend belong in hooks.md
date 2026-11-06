---
tags: [lesson]
updated: 2026-11-06
---
# Rules that cannot bend belong in hooks

**What happened:** 29 Oct research (Anthropic docs): emphasis like NEVER / IMPORTANT does not make Claude follow a rule better; long instruction files lose lines.

**Rule:** Keep CLAUDE.md short, put area rules in `.claude/rules/` (loaded by path), and enforce must-always rules with a hook (`.claude/hooks/on_stop.sh`: STL check, uncommitted / unpushed check).

Related: [[Agent Protocol]], [[STEP only, never STL]], [[Commit and push right away - sessions die]]
