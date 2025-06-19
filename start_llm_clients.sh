#!/bin/bash

# 默認配置
DEFAULT_PLAYERS=4
DEFAULT_MODEL="gemini-2.5-flash-preview-04-17"
DEFAULT_CONTAINER="catanatron-websocketllm-1"

# 解析命令行參數
PLAYERS=$DEFAULT_PLAYERS
MODEL=$DEFAULT_MODEL
CONTAINER=$DEFAULT_CONTAINER

while [[ $# -gt 0 ]]; do
    case $1 in
    --players)
        PLAYERS="$2"
        shift 2
        ;;
    --model)
        MODEL="$2"
        shift 2
        ;;
    --container)
        CONTAINER="$2"
        shift 2
        ;;
    -h | --help)
        echo "用法: $0 [選項]"
        echo "選項:"
        echo "  --players NUM     設置玩家數量 (1-4, 默認: $DEFAULT_PLAYERS)"
        echo "  --model MODEL     設置 LLM 模型 (默認: $DEFAULT_MODEL)"
        echo "  --container NAME  設置容器名稱 (默認: $DEFAULT_CONTAINER)"
        echo "  -h, --help        顯示此幫助信息"
        exit 0
        ;;
    *)
        echo "未知選項: $1"
        echo "使用 -h 或 --help 查看幫助"
        exit 1
        ;;
    esac
done

# 驗證玩家數量
if [[ ! "$PLAYERS" =~ ^[1-4]$ ]]; then
    echo "錯誤: 玩家數量必須在 1-4 之間"
    exit 1
fi

# 顏色配置
COLORS=("RED" "BLUE" "WHITE" "ORANGE")
PORTS=(8001 8002 8003 8004)

echo "🤖 Manual LLM Client Launcher"
echo "=============================="
echo "📊 啟動配置："
echo "   玩家數量: $PLAYERS"
echo "   LLM 模型: $MODEL"
echo "   容器名稱: $CONTAINER"
echo

# 檢查容器是否存在並運行中
if ! docker ps | grep -q "$CONTAINER"; then
    echo "❌ 錯誤: 容器 '$CONTAINER' 未運行"
    echo "   請先啟動服務: docker compose up -d websocketllm"
    exit 1
fi

echo "🧹 清理現有的 LLM 客戶端..."

# 清理現有的客戶端進程
for i in $(seq 0 3); do
    color=${COLORS[$i]}
    port=${PORTS[$i]}

    # 清理可能的舊進程
    docker exec "$CONTAINER" pkill -f "llm_agent_client.*--port $port" 2>/dev/null || true
    docker exec "$CONTAINER" pkill -f "llm_agent_client.*--color $color" 2>/dev/null || true
done

# 等待清理完成
sleep 2

echo "🚀 啟動 LLM 客戶端..."

# 啟動指定數量的客戶端
for i in $(seq 0 $((PLAYERS - 1))); do
    color=${COLORS[$i]}
    port=${PORTS[$i]}
    color_lower=$(echo "$color" | tr '[:upper:]' '[:lower:]')

    echo "🎮 啟動 $color 玩家 (端口 $port)..."

    # 在背景啟動客戶端並重定向輸出
    docker exec -d "$CONTAINER" bash -c "
        cd /app && 
        uv run python -m catanatron.multiplayer.llm_agent_client \
            --host websocketllm \
            --port $port \
            --color $color \
            --model '$MODEL' \
            > /tmp/${color_lower}_agent.log 2>&1
    "

    # 短暫等待以確保啟動順序
    sleep 1

    echo "   ✅ $color 玩家已啟動"
done

echo
echo "🎉 所有客戶端已啟動！"
echo

echo "📊 檢查連接狀態："
# 使用新的端口 8100 狀態端點
curl -s http://localhost:8100/status | jq '.player_connections' 2>/dev/null || echo "無法獲取狀態，請手動檢查"

echo
echo "📋 查看客戶端日誌："
for i in $(seq 0 $((PLAYERS - 1))); do
    color=${COLORS[$i]}
    color_lower=$(echo "$color" | tr '[:upper:]' '[:lower:]')
    echo "   docker exec $CONTAINER tail -f /tmp/${color_lower}_agent.log"
done

echo
echo "🛑 停止所有客戶端："
echo "   ./stop_llm_clients.sh"

echo
echo "🎮 監控遊戲："
echo "   docker logs -f $CONTAINER"
