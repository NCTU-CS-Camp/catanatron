#!/bin/bash

echo "🔗 測試 Flask API 與 WebSocket 遊戲狀態同步"
echo "=============================================="

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 檢查 Flask API 是否運行
echo -e "${YELLOW}📡 檢查 Flask API (端口 5001)...${NC}"
if curl -s http://localhost:5001/api/games/list >/dev/null; then
    echo -e "${GREEN}✅ Flask API 運行中${NC}"
else
    echo -e "${RED}❌ Flask API 無法連接${NC}"
    echo "請先啟動: docker compose up -d"
    exit 1
fi

# 檢查 WebSocket 遊戲引擎是否運行
echo -e "${YELLOW}📡 檢查 WebSocket 遊戲引擎 (端口 8100)...${NC}"
if curl -s http://localhost:8100/status >/dev/null; then
    echo -e "${GREEN}✅ WebSocket 遊戲引擎運行中${NC}"
else
    echo -e "${RED}❌ WebSocket 遊戲引擎無法連接${NC}"
    echo "請先啟動: docker compose up -d"
    exit 1
fi

echo ""
echo "🎮 測試新的 Flask API 端點"
echo "=========================="

# 測試 1: 列出所有遊戲
echo -e "${YELLOW}1. 測試遊戲列表 API...${NC}"
response=$(curl -s http://localhost:5001/api/games/list)
echo "回應: $response" | jq .
echo ""

# 測試 2: 取得 WebSocket 遊戲狀態
echo -e "${YELLOW}2. 測試 WebSocket 遊戲狀態 API...${NC}"
response=$(curl -s http://localhost:5001/api/websocket-games/current)
echo "回應: $response" | jq .
echo ""

# 測試 3: 取得詳細的 WebSocket 遊戲狀態
echo -e "${YELLOW}3. 測試詳細 WebSocket 遊戲狀態 API...${NC}"
response=$(curl -s http://localhost:5001/api/websocket-games/current/detailed)
echo "回應: $response" | jq .
echo ""

# 測試 4: 模擬前端訪問 WebSocket 遊戲
echo -e "${YELLOW}4. 測試前端格式的 WebSocket 遊戲狀態...${NC}"
response=$(curl -s http://localhost:5001/api/games/websocket/websocket_multiplayer_game/states/latest)
if [[ $? -eq 0 ]]; then
    echo "回應: $response" | jq .
else
    echo -e "${RED}❌ 無法取得 WebSocket 遊戲狀態${NC}"
fi
echo ""

echo "📊 比較原始 WebSocket 狀態與 Flask API 代理"
echo "=========================================="

# 直接從 WebSocket 引擎取得狀態
echo -e "${YELLOW}原始 WebSocket 狀態:${NC}"
curl -s http://localhost:8100/status | jq '.summary'

# 透過 Flask API 取得狀態
echo -e "${YELLOW}Flask API 代理狀態:${NC}"
curl -s http://localhost:5001/api/websocket-games/current | jq '.summary // .websocket_status.summary // "無活躍遊戲"'

echo ""
echo "🚀 測試建議"
echo "=========="
echo "1. 啟動 WebSocket 遊戲："
echo "   ./start_llm_clients.sh --players 3"
echo ""
echo "2. 重新執行此測試腳本，查看有活躍遊戲時的狀態"
echo ""
echo "3. 前端可以使用以下 API："
echo "   GET /api/games/list - 列出所有遊戲"
echo "   GET /api/websocket-games/current - 取得當前 WebSocket 遊戲"
echo "   GET /api/games/websocket/websocket_multiplayer_game/states/latest - 用一般格式訪問"
echo ""
echo "✅ 測試完成！"
