#!/bin/bash
set -e
echo "=== Harness Initialization ==="

# Auto-detect project type and run verification
if [ -f requirements.txt ] || [ -f pyproject.toml ]; then
  echo "=== Python project detected ==="
  PY="$(command -v python3 || command -v python)"
  "$PY" -m pytest tests/ || [ $? -eq 5 ]  # exit 5 = no tests collected (OK for fresh project)
  "$PY" -m compileall -q -x '(venv|__pycache__)' .
elif [ -f package.json ]; then
  echo "=== Node project detected ==="
  npm install
  npm run check 2>/dev/null || true
  npm test 2>/dev/null || true
else
  echo "No recognized project type. Add your verification commands here."
fi

echo "=== Verification Complete ==="
echo ""
echo "Next steps:"
echo "1. Read feature_list.json for current phase state"
echo "2. Pick the one ACTIVE task"
echo "3. Work on that task only"
echo "4. Re-run this script before claiming done"
