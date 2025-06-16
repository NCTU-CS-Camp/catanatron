#!/bin/bash

echo "🛑 停止 LLM 客戶端"
echo "=================="

# 容器名稱
CONTAINER_NAME="catanatron-websocketllm-1"

# 檢查容器是否運行
if ! docker ps --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
  echo "❌ 容器 '$CONTAINER_NAME' 未運行"
  exit 1
fi

echo "🧹 清理 LLM 客戶端進程..."

# 清理所有 LLM 客戶端相關進程
docker exec $CONTAINER_NAME pkill -f "llm_agent_client" 2>/dev/null || true

# 清理 PID 文件
docker exec $CONTAINER_NAME sh -c "rm -f /tmp/*_agent.pid" 2>/dev/null || true

# 等待進程清理
sleep 2

echo "✅ 所有 LLM 客戶端已停止"

echo
echo "📊 檢查停止後狀態："

# 使用新的端口 8100 狀態端點
curl -s http://localhost:8100/status | jq '.player_connections' 2>/dev/null || echo "無法獲取狀態"

echo
echo "🎮 如需重新啟動客戶端："
echo "   ./start_llm_clients.sh"
