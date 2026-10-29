#!/usr/bin/env bash
# Stop hook: before Claude ends a turn, check two standing rules from CLAUDE.md.
#  1. no STL files anywhere in the project (STEP only)
#  2. no tracked change left uncommitted or unpushed
# Exit 2 = Claude must continue and gets the message on stderr. Fires only once per turn (stop_hook_active).
input=$(cat)
case "$input" in *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;; esac

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

msg=""
stl=$(find . \( -path ./.git -o -path ./laptop/.venv -o -path ./firmware/.pio \) -prune -o -iname '*.stl' -print 2>/dev/null | head -5)
[ -n "$stl" ] && msg="${msg}STL files found (Egor's rule: STEP only, never STL) - delete them if you made them:
$stl
"

dirty=$(git status --porcelain --untracked-files=no 2>/dev/null | head -10)
[ -n "$dirty" ] && msg="${msg}Uncommitted changes to tracked files:
$dirty
"

if git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
  ahead=$(git rev-list --count '@{u}..HEAD' 2>/dev/null)
  [ "${ahead:-0}" -gt 0 ] && msg="${msg}$ahead commit(s) not pushed.
"
fi

[ -z "$msg" ] && exit 0
{
  echo "$msg"
  echo "If this is your finished work and its checks are clean: commit and push now (CLAUDE.md)."
  echo "If it is work in progress, Egor's own edits, or a push is impossible here: say so to Egor in one line and stop."
} >&2
exit 2
