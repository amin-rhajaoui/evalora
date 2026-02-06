#!/usr/bin/env bash
# Démarre backend, frontend et agent Evalora.
# Usage: ./start.sh
# Arrêt: Ctrl+C (tue tous les processus).

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

cleanup() {
  echo ""
  echo "Arrêt des services..."
  kill $(jobs -p) 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

echo "Démarrage Evalora (backend, frontend, agent)..."
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo "  Arrêt    → Ctrl+C"
echo ""

(cd "$ROOT/backend" && source venv/bin/activate && uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

(cd "$ROOT/frontend" && npm run dev) &
FRONTEND_PID=$!

(cd "$ROOT/agent" && source venv/bin/activate && python agent.py dev) &
AGENT_PID=$!

wait
