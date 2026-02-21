#!/bin/bash
#
# Ralph Activation Script
# Launches the Scrum Master agent via Claude CLI with full context
#

set -e

RALPH_DIR="/data/.openclaw/workspace/agents/scrum-master"
DNA_DIR="/data/.openclaw/workspace/DNA"

echo "🎯 RALPH — Scrum Master Agent"
echo "================================"
echo ""

# Ensure DNA repo exists
if [ ! -d "$DNA_DIR" ]; then
    echo "❌ DNA repo not found at $DNA_DIR"
    echo "Clone it first: git clone https://github.com/launchplugai/DNA.git $DNA_DIR"
    exit 1
fi

# Create memory structure if missing
mkdir -p "$RALPH_DIR/memory/daily-notes"
mkdir -p "$RALPH_DIR/tasks/active"
mkdir -p "$RALPH_DIR/tasks/completed"
mkdir -p "$RALPH_DIR/sprints/current"
mkdir -p "$RALPH_DIR/sprints/archive"
mkdir -p "$RALPH_DIR/metrics"

# Build context payload
SYSTEM_PROMPT="$RALPH_DIR/docs/ralph-system-prompt.md"
RALPH_SOUL="$RALPH_DIR/SOUL.md"

echo "Loading context..."
echo "  📄 System prompt: $SYSTEM_PROMPT"
echo "  🦞 Ralph's soul: $RALPH_SOUL"
echo "  🧬 DNA repo: $DNA_DIR"
echo ""

# Construct the activation command
# Claude CLI reads the system prompt, then executes Ralph's initialization
claude --system-prompt "$SYSTEM_PROMPT" \
       --context-file "$RALPH_SOUL" \
       --working-dir "$DNA_DIR" \
       "
You are Ralph, the Scrum Master Agent for the DNA/BetApp project.

INITIALIZATION SEQUENCE:
1. Read and parse the PDC (Product Design Concept) from DNA/docs/ or find it
2. Analyze the codebase structure in DNA/ - understand:
   - app/ (FastAPI + web UI)
   - sherlock/ (audit module)
   - protocol/ (alerts/notifications)
   - dna-matrix/core/ (FROZEN - do not modify)
   - app/tests/ (840 pytest tests)
3. Check for any existing Ralph state in $RALPH_DIR/memory/
4. Identify current sprint/tasks if defined
5. Check production health (use DNA_BASE_URL from .env or docs/deployments.md)

OUTPUT YOUR KNOWLEDGE DIGEST:
- Project summary (what DNA is, core loop)
- Current state (what's working, what's broken)
- Active work (sprints, tasks in progress)
- Immediate concerns (failing tests, prod issues)
- Your recommended next actions

Then wait for task assignment.
"
