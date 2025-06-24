#!/bin/bash
# Catanatron 遊戲啟動腳本 - 支援變數玩家

# 設定日誌檔案
LOG_FILE="server.log"

# 清理舊的日誌檔案
>"$LOG_FILE"

# 重定向所有輸出到 tee，同時顯示在終端和保存到日誌檔案
exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo -e "\033[1;36m啟動 Catanatron 多人遊戲 (支援變數玩家)...\033[0m"
echo -e "\033[90m日誌將保存到: $LOG_FILE\033[0m"

# 預設配置
DEFAULT_MIN_PLAYERS=2
DEFAULT_MAX_PLAYERS=4
DEFAULT_WAIT_TIME=10

# 解析命令行參數
MIN_PLAYERS=$DEFAULT_MIN_PLAYERS
MAX_PLAYERS=$DEFAULT_MAX_PLAYERS
WAIT_TIME=$DEFAULT_WAIT_TIME

while [[ $# -gt 0 ]]; do
    case $1 in
    --min-players)
        MIN_PLAYERS="$2"
        shift 2
        ;;
    --max-players)
        MAX_PLAYERS="$2"
        shift 2
        ;;
    --wait-time)
        WAIT_TIME="$2"
        shift 2
        ;;
    -h | --help)
        echo "用法: $0 [選項]"
        echo "選項:"
        echo "  --min-players NUM    最少玩家數 (預設: $DEFAULT_MIN_PLAYERS)"
        echo "  --max-players NUM    最多玩家數 (預設: $DEFAULT_MAX_PLAYERS)"
        echo "  --wait-time SEC      等待時間秒數 (預設: $DEFAULT_WAIT_TIME)"
        echo "  -h, --help          顯示此幫助訊息"
        echo ""
        echo "範例:"
        echo "  $0                           # 2-4 玩家，等待 10 秒"
        echo "  $0 --min-players 2 --max-players 2  # 只允許 2 玩家"
        echo "  $0 --min-players 3 --max-players 3  # 只允許 3 玩家"
        exit 0
        ;;
    *)
        echo "未知選項: $1"
        echo "使用 --help 查看幫助"
        exit 1
        ;;
    esac
done

# 驗證參數
if [ "$MIN_PLAYERS" -lt 2 ] || [ "$MIN_PLAYERS" -gt 4 ]; then
    echo -e "\033[1;31m錯誤: 最少玩家數必須在 2-4 之間\033[0m"
    exit 1
fi

if [ "$MAX_PLAYERS" -lt 2 ] || [ "$MAX_PLAYERS" -gt 4 ]; then
    echo -e "\033[1;31m錯誤: 最多玩家數必須在 2-4 之間\033[0m"
    exit 1
fi

if [ "$MIN_PLAYERS" -gt "$MAX_PLAYERS" ]; then
    echo -e "\033[1;31m錯誤: 最少玩家數不能大於最多玩家數\033[0m"
    exit 1
fi

echo -e "\033[1;33m遊戲配置:\033[0m"
echo -e "  最少玩家: $MIN_PLAYERS"
echo -e "  最多玩家: $MAX_PLAYERS"
echo -e "  等待時間: $WAIT_TIME 秒"

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

# 根據最大玩家數決定要啟動的顏色
ALL_COLORS=("RED" "BLUE" "WHITE" "ORANGE")
COLORS=("${ALL_COLORS[@]:0:$MAX_PLAYERS}")

# 檢查是否已安裝 uv
if ! command -v uv &>/dev/null; then
    echo -e "\033[1;31m錯誤: uv 未安裝。請先安裝 uv。\033[0m"
    exit 1
fi

# 檢查必要文件是否存在
if [ ! -f "start_server.py" ]; then
    echo -e "\033[1;31m錯誤: 找不到 start_server.py\033[0m"
    exit 1
fi

if [ ! -f "catanatron/catanatron/multiplayer/llm_agent_client.py" ]; then
    echo -e "\033[1;31m錯誤: 找不到 llm_agent_client.py\033[0m"
    exit 1
fi

# 清理之前可能存在的進程
echo -e "\033[90m清理舊進程...\033[0m"
pkill -f "start_server.py" 2>/dev/null || true
pkill -f "game_engine_server.py" 2>/dev/null || true
pkill -f "llm_agent_client.py" 2>/dev/null || true
sleep 2

# 啟動遊戲伺服器 - 使用新的 start_server.py
echo -e "\033[90m啟動遊戲伺服器...\033[0m"
python start_server.py --min-players $MIN_PLAYERS --max-players $MAX_PLAYERS --wait-time $WAIT_TIME --no-cleanup &
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
    cd catanatron/catanatron/multiplayer
    uv run python llm_agent_client.py --port $PORT --color $COLOR --debug &
    CLIENT_PID=$!
    cd ../../..
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
    echo -e "\033[90m完整日誌已保存到: $LOG_FILE\033[0m"
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
