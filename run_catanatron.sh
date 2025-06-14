#!/bin/bash
# 🎮 Catanatron 遊戲啟動腳本
echo "🚀 啟動 Catanatron 多人遊戲..."

# 設定玩家端口映射
declare -A COLOR_PORTS
COLOR_PORTS["RED"]=8001
COLOR_PORTS["BLUE"]=8002
COLOR_PORTS["WHITE"]=8003
COLOR_PORTS["ORANGE"]=8004

COLORS=("RED" "BLUE" "WHITE" "ORANGE")

# 檢查是否已安裝 uv
if ! command -v uv &> /dev/null; then
    echo "❌ 錯誤: uv 未安裝。請先安裝 uv。"
    exit 1
fi

# 進入正確的目錄
cd /home/apollo/2025cscamp/catanatron/catanatron/catanatron/multiplayer

# 檢查必要文件是否存在
if [ ! -f "game_engine_server.py" ]; then
    echo "❌ 錯誤: 找不到 game_engine_server.py"
    exit 1
fi

if [ ! -f "llm_agent_client.py" ]; then
    echo "❌ 錯誤: 找不到 llm_agent_client.py"
    exit 1
fi

# 清理之前可能存在的進程
echo "🧹 清理舊進程..."
pkill -f "game_engine_server.py" 2>/dev/null || true
pkill -f "llm_agent_client.py" 2>/dev/null || true
sleep 2

# 啟動遊戲伺服器（不需要指定端口，它會自動使用 8001-8004）
echo "�� 啟動遊戲伺服器..."
uv run python game_engine_server.py &
SERVER_PID=$!

# 等待伺服器啟動
echo "⏳ 等待伺服器啟動..."
sleep 8

# 檢查伺服器是否成功啟動
if ! ps -p $SERVER_PID > /dev/null; then
    echo "❌ 錯誤: 遊戲伺服器啟動失敗"
    exit 1
fi

echo "✅ 遊戲伺服器已啟動 (PID: $SERVER_PID)"
echo "📊 端口配置:"
for COLOR in "${COLORS[@]}"; do
    echo "  🎯 $COLOR: 端口 ${COLOR_PORTS[$COLOR]}"
done

# 啟動客戶端
echo "🤖 啟動 LLM 客戶端..."
CLIENT_PIDS=()

for COLOR in "${COLORS[@]}"; do
    PORT=${COLOR_PORTS[$COLOR]}
    echo "🔥 啟動 $COLOR 玩家 (端口: $PORT)..."
    uv run python llm_agent_client.py --port $PORT --color $COLOR --debug &
    CLIENT_PID=$!
    CLIENT_PIDS+=($CLIENT_PID)
    echo "✅ $COLOR 玩家已啟動 (PID: $CLIENT_PID, 端口: $PORT)"
    sleep 3
done

echo ""
echo "🎮 遊戲已完全啟動！"
echo "📊 伺服器 PID: $SERVER_PID"
echo "🤖 客戶端 PIDs: ${CLIENT_PIDS[*]}"
echo ""
echo "🔗 連接配置:"
for COLOR in "${COLORS[@]}"; do
    PORT=${COLOR_PORTS[$COLOR]}
    echo "  $COLOR 玩家 → ws://localhost:$PORT"
done
echo ""
echo "📝 按 Ctrl+C 停止所有進程"

# 等待用戶中斷
cleanup() {
    echo ""
    echo "🛑 正在停止所有進程..."
    
    # 停止客戶端
    for PID in "${CLIENT_PIDS[@]}"; do
        if ps -p $PID > /dev/null; then
            kill $PID 2>/dev/null
            echo "🔴 已停止客戶端 (PID: $PID)"
        fi
    done
    
    # 停止伺服器
    if ps -p $SERVER_PID > /dev/null; then
        kill $SERVER_PID 2>/dev/null
        echo "🔴 已停止伺服器 (PID: $SERVER_PID)"
    fi
    
    echo "✅ 清理完成！"
    exit 0
}

# 設定中斷處理
trap cleanup SIGINT SIGTERM

# 監控進程狀態
while true; do
    # 檢查伺服器是否還在運行
    if ! ps -p $SERVER_PID > /dev/null; then
        echo "❌ 伺服器已停止，正在清理..."
        cleanup
    fi
    
    # 檢查是否有客戶端崩潰
    RUNNING_CLIENTS=0
    for PID in "${CLIENT_PIDS[@]}"; do
        if ps -p $PID > /dev/null; then
            ((RUNNING_CLIENTS++))
        fi
    done
    
    if [ $RUNNING_CLIENTS -eq 0 ]; then
        echo "❌ 所有客戶端已停止，正在清理..."
        cleanup
    fi
    
    sleep 5
done
