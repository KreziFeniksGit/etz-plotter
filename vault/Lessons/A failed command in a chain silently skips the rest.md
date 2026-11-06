---
tags: [lesson]
updated: 2026-11-06
---
# A failed command in a chain silently skips the rest

**What happened:** 29 Oct: a `.venv=...` assignment broke a `&&` chain; three doc edits (status, ideas, CLAUDE.md) never happened, and it looked done.

**Rule:** After a commit, check `git status` and `git log -1 --stat`. Keep chains short; never set shell variables mid-chain.

Related: [[Agent Protocol]], [[Use the Edit tool, not shell tricks, on Windows]]
