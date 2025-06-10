#!/bin/bash

echo "=== Starting Catanatron Multiplayer Game ==="

# 設置 Gemini API 密鑰
export GOOGLE_API_KEY="AIzaSyCxbVjDyqLssYuc4VWqbHK34YDeuCz7_uQ"

# 檢查是否有 Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is required but not installed."
    exit 1
fi

# 停止已存在的進程（如果有的話）
echo "Stopping any existing processes..."
./stop_all.sh 2>/dev/null || true

# 啟動 Game Engine Server
echo "Starting Game Engine Server..."
python3 start_server.py &
SERVER_PID=$!

# 等待服務器啟動
echo "Waiting for server to start..."
sleep 5

# 啟動 LLM Agents
echo "Starting LLM Agents..."

python3 scripts/start_red_agent.py &
RED_PID=$!
echo "RED agent started (PID: $RED_PID)"

sleep 2

python3 scripts/start_blue_agent.py &
BLUE_PID=$!
echo "BLUE agent started (PID: $BLUE_PID)"

sleep 2

python3 scripts/start_white_agent.py &
WHITE_PID=$!
echo "WHITE agent started (PID: $WHITE_PID)"

sleep 2

python3 scripts/start_orange_agent.py &
ORANGE_PID=$!
echo "ORANGE agent started (PID: $ORANGE_PID)"

echo ""
echo "=== All components started successfully! ==="
echo "Server PID: $SERVER_PID"
echo "Agent PIDs: RED=$RED_PID, BLUE=$BLUE_PID, WHITE=$WHITE_PID, ORANGE=$ORANGE_PID"
echo ""
echo "Press Ctrl+C to stop all components"

# 等待用戶中斷
trap 'echo -e "\n=== Shutting down all components ==="; kill $SERVER_PID $RED_PID $BLUE_PID $WHITE_PID $ORANGE_PID 2>/dev/null; exit' INT

# 等待所有進程
wait