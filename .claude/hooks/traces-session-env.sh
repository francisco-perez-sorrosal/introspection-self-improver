#!/usr/bin/env bash
# traces-session-env.sh — Claude Code SessionStart hook
#
# Injects TRACES_CURRENT_TRACE_ID and TRACES_CURRENT_AGENT into the session
# environment so that `traces share --cwd "$PWD" --agent claude-code --json`
# can deterministically identify the active session.
#
# Install:
#   1. Copy this file to .claude/hooks/traces-session-env.sh
#   2. chmod +x .claude/hooks/traces-session-env.sh
#   3. Add to .claude/settings.json (or ~/.claude/settings.json for global):
#      {
#        "hooks": {
#          "SessionStart": [{
#            "matcher": "",
#            "hooks": [{
#              "type": "command",
#              "command": ".claude/hooks/traces-session-env.sh",
#              "timeout": 5
#            }]
#          }]
#        }
#      }
#
#      For global (~/.claude/settings.json), use an absolute path:
#        "command": "$HOME/.claude/hooks/traces-session-env.sh"

set -euo pipefail

# Read the hook event JSON from stdin
INPUT=$(cat)

# Extract session_id from the JSON payload
SESSION_ID=$(echo "$INPUT" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

# Write env vars to CLAUDE_ENV_FILE so they persist for all Bash tool calls
if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -n "${SESSION_ID:-}" ]; then
  echo "export TRACES_CURRENT_TRACE_ID=\"${SESSION_ID}\"" >> "$CLAUDE_ENV_FILE"
  echo "export TRACES_CURRENT_AGENT=\"claude-code\"" >> "$CLAUDE_ENV_FILE"
fi

exit 0
