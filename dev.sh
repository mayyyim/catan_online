#!/bin/bash
# Catan Online — 本地开发快速启动
# 用法: ./dev.sh          启动全部 (Redis + Postgres + Backend + Frontend)
#       ./dev.sh stop      停止全部
#       ./dev.sh restart   重启全部
#       ./dev.sh logs      查看日志

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── 停止 ──
stop_all() {
  echo -e "${YELLOW}Stopping services...${NC}"
  docker compose stop redis postgres 2>/dev/null || true
  # Kill background processes by PID file
  for pid_file in "$ROOT"/.pid.*; do
    [ -f "$pid_file" ] && kill "$(cat "$pid_file")" 2>/dev/null && rm "$pid_file"
  done
  echo -e "${GREEN}All stopped.${NC}"
}

# ── 日志 ──
show_logs() {
  echo -e "${CYAN}=== Backend log ===${NC}"
  tail -30 "$ROOT/.log.backend" 2>/dev/null || echo "(no backend log)"
  echo ""
  echo -e "${CYAN}=== Frontend log ===${NC}"
  tail -30 "$ROOT/.log.frontend" 2>/dev/null || echo "(no frontend log)"
}

case "${1:-start}" in
  stop)    stop_all; exit 0 ;;
  restart) stop_all ;;
  logs)    show_logs; exit 0 ;;
  start)   ;;
  *)       echo "Usage: $0 [start|stop|restart|logs]"; exit 1 ;;
esac

# ── 1. Redis + Postgres (Docker) ──
echo -e "${CYAN}[1/4] Starting Redis + Postgres...${NC}"
docker compose up -d redis postgres
# Wait for Redis
for i in $(seq 1 10); do
  docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG && break
  sleep 0.5
done
echo -e "${GREEN}  Redis + Postgres ready.${NC}"

# ── 2. Backend dependencies ──
echo -e "${CYAN}[2/4] Checking backend dependencies...${NC}"
cd "$ROOT/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null

# ── 3. Backend ──
echo -e "${CYAN}[3/4] Starting backend (port 8080)...${NC}"
export REDIS_URL="redis://localhost:6379/0"
export DATABASE_URL="postgresql://catan:catan_secret@localhost:5432/catan"
python main.py > "$ROOT/.log.backend" 2>&1 &
echo $! > "$ROOT/.pid.backend"
# Wait for backend
for i in $(seq 1 20); do
  curl -s http://localhost:8080/health >/dev/null 2>&1 && break
  sleep 0.5
done
echo -e "${GREEN}  Backend ready: http://localhost:8080${NC}"

# ── 4. Frontend ──
echo -e "${CYAN}[4/4] Starting frontend (port 3000)...${NC}"
cd "$ROOT/frontend"
if [ ! -d "node_modules" ]; then
  npm install --silent
fi
npm run dev > "$ROOT/.log.frontend" 2>&1 &
echo $! > "$ROOT/.pid.frontend"
sleep 2
echo -e "${GREEN}  Frontend ready: http://localhost:3000${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Catan Online is running!${NC}"
echo -e "${GREEN}  Frontend: ${CYAN}http://localhost:3000${NC}"
echo -e "${GREEN}  Backend:  ${CYAN}http://localhost:8080${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}  ./dev.sh stop   — 停止全部${NC}"
echo -e "${YELLOW}  ./dev.sh logs   — 查看日志${NC}"
