#!/bin/bash
# Catanatron 遊戲啟動腳本
echo -e "\033[1;36m啟動 Catanatron 多人遊戲...\033[0m"

# 設定玩家端口映射 - 使用簡單的函數替代關聯陣列
get_port_for_color() {
    case $1 in
    "RED") echo 8001 ;;
    "BLUE") echo 8002 ;;
    "WHITE") echo 8003 ;;
    "ORANGE") echo 8004 ;;
    *) echo 8001 ;;
    esac
}

COLORS=("RED" "BLUE" "WHITE" "ORANGE")

# 檢查是否已安裝 uv
if ! command -v uv &>/dev/null; then
    echo -e "\033[1;31m錯誤: uv 未安裝。請先安裝 uv。\033[0m"
    exit 1
fi

# 進入正確的目錄
cd ./catanatron/catanatron/multiplayer

# 檢查必要文件是否存在
if [ ! -f "game_engine_server.py" ]; then
    echo -e "\033[1;31m錯誤: 找不到 game_engine_server.py\033[0m"
    exit 1
fi

if [ ! -f "llm_agent_client.py" ]; then
    echo -e "\033[1;31m錯誤: 找不到 llm_agent_client.py\033[0m"
    exit 1
fi

# 清理之前可能存在的進程
echo -e "\033[90m清理舊進程...\033[0m"
pkill -f "game_engine_server.py" 2>/dev/null || true
pkill -f "llm_agent_client.py" 2>/dev/null || true
sleep 2

# 啟動遊戲伺服器（不需要指定端口，它會自動使用 8001-8004）
echo -e "\033[90m啟動遊戲伺服器...\033[0m"
uv run python game_engine_server.py &
SERVER_PID=$!

# 等待伺服器啟動
echo -e "\033[90m等待伺服器啟動...\033[0m"
sleep 8

# 檢查伺服器是否成功啟動
if ! ps -p $SERVER_PID >/dev/null; then
    echo -e "\033[1;31m錯誤: 遊戲伺服器啟動失敗\033[0m"
    exit 1
fi

echo -e "\033[1;32m遊戲伺服器已啟動 (PID: $SERVER_PID)\033[0m"
echo -e "\033[37m端口配置:\033[0m"
for COLOR in "${COLORS[@]}"; do
    PORT=$(get_port_for_color $COLOR)
    echo -e "  \033[33m$COLOR\033[0m: 端口 $PORT"
done

# 啟動客戶端
echo -e "\033[90m啟動 LLM 客戶端...\033[0m"
CLIENT_PIDS=()

for COLOR in "${COLORS[@]}"; do
    PORT=$(get_port_for_color $COLOR)
    echo -e "\033[90m啟動 $COLOR 玩家 (端口: $PORT)...\033[0m"
    uv run python llm_agent_client.py --port $PORT --color $COLOR --debug &
    CLIENT_PID=$!
    CLIENT_PIDS+=($CLIENT_PID)
    echo -e "\033[32m$COLOR 玩家已啟動 (PID: $CLIENT_PID, 端口: $PORT)\033[0m"
    sleep 3
done

echo ""
echo -e "\033[1;36m遊戲已完全啟動！\033[0m"
echo -e "\033[37m伺服器 PID: $SERVER_PID\033[0m"
echo -e "\033[37m客戶端 PIDs: ${CLIENT_PIDS[*]}\033[0m"
echo ""
echo -e "\033[37m連接配置:\033[0m"
for COLOR in "${COLORS[@]}"; do
    PORT=$(get_port_for_color $COLOR)
    echo "  $COLOR 玩家 → ws://localhost:$PORT"
done
echo ""
echo -e "\033[1;33m按 Ctrl+C 停止所有進程\033[0m"

# 等待用戶中斷
cleanup() {
    echo ""
    echo -e "\033[1;31m正在停止所有進程...\033[0m"

    # 停止客戶端
    for PID in "${CLIENT_PIDS[@]}"; do
        if ps -p $PID >/dev/null; then
            kill $PID 2>/dev/null
            echo -e "\033[90m已停止客戶端 (PID: $PID)\033[0m"
        fi
    done

    # 停止伺服器
    if ps -p $SERVER_PID >/dev/null; then
        kill $SERVER_PID 2>/dev/null
        echo -e "\033[90m已停止伺服器 (PID: $SERVER_PID)\033[0m"
    fi

    echo -e "\033[1;32m清理完成！\033[0m"
    exit 0
}

# 設定中斷處理
trap cleanup SIGINT SIGTERM

# 監控進程狀態
while true; do
    # 檢查伺服器是否還在運行
    if ! ps -p $SERVER_PID >/dev/null; then
        echo -e "\033[1;31m伺服器已停止，正在清理...\033[0m"
        cleanup
    fi

    # 檢查是否有客戶端崩潰
    RUNNING_CLIENTS=0
    for PID in "${CLIENT_PIDS[@]}"; do
        if ps -p $PID >/dev/null; then
            ((RUNNING_CLIENTS++))
        fi
    done

    if [ $RUNNING_CLIENTS -eq 0 ]; then
        echo -e "\033[1;31m所有客戶端已停止，正在清理...\033[0m"
        cleanup
    fi

    sleep 5
done
