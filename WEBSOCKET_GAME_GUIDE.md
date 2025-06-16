# Catanatron WebSocket 遊戲引擎指南

## 🚀 快速開始

### 1. 啟動服務

```bash
docker compose up -d
```

### 2. 檢查狀態

```bash
./test_websocket_status.sh
```

### 3. 啟動遊戲客戶端

```bash
# 啟動3個玩家
./start_llm_clients.sh --players 3

# 啟動4個玩家（預設）
./start_llm_clients.sh
```

### 4. 停止客戶端

```bash
./stop_llm_clients.sh
```

---

## 📊 狀態 API

### 主要狀態端點

```bash
# WebSocket遊戲引擎狀態（推薦）
curl http://localhost:8100/status | jq .
```

### 狀態資訊說明

```json
{
  "websocket_game_engine": {
    "status": "running",
    "min_players": 3,
    "max_players": 4,
    "waiting_time": 20
  },
  "player_connections": {
    "RED": { "connected": true, "port": 8001 },
    "BLUE": { "connected": true, "port": 8002 }
  },
  "game_status": {
    "game_started": true,
    "connected_players": 3,
    "game_state": {
      "current_player": "WHITE",
      "turn_number": 4
    }
  },
  "summary": "Game in progress - 3 players connected"
}
```

---

## 🎮 遊戲模式

### 玩家數量配置

- **最少玩家**: 3 人（可在 docker-compose.yml 中修改）
- **最多玩家**: 4 人
- **等待時間**: 20 秒（達到最少玩家數後自動開始）

### 端口映射

| 玩家     | 端口 | 顏色   |
| -------- | ---- | ------ |
| Player 1 | 8001 | RED    |
| Player 2 | 8002 | BLUE   |
| Player 3 | 8003 | WHITE  |
| Player 4 | 8004 | ORANGE |

---

## 🔧 測試腳本

### test_websocket_status.sh

檢查所有服務狀態：

```bash
./test_websocket_status.sh
```

- ✅ 檢查 Docker 服務
- ✅ 檢查各端口狀態
- ✅ 顯示詳細遊戲狀態

### start_llm_clients.sh

啟動 LLM 客戶端：

```bash
# 基礎用法
./start_llm_clients.sh --players 3

# 自定義模型
./start_llm_clients.sh --players 2 --model gpt-4

# 查看幫助
./start_llm_clients.sh --help
```

### stop_llm_clients.sh

停止所有客戶端：

```bash
./stop_llm_clients.sh
```

---

## 🛠️ 故障排除

### 檢查服務狀態

```bash
# 檢查Docker容器
docker compose ps

# 檢查WebSocket狀態
curl http://localhost:8100/status

# 查看遊戲引擎日誌
docker compose logs websocketllm
```

### 重啟服務

```bash
# 重啟WebSocket服務
docker compose restart websocketllm

# 重啟所有服務
docker compose restart
```

### 常見問題

**Q: JSON 序列化錯誤 "Object of type Color is not JSON serializable"**

- ✅ 已修復：現在所有 Color 物件都正確轉換為字串

**Q: 端口 8100 無響應**

- 檢查 websocketllm 容器是否運行
- 等待 10-15 秒讓服務完全啟動

**Q: 遊戲不開始**

- 確保至少有 3 個客戶端連接
- 檢查.env 檔案中的 GOOGLE_API_KEY

---

## 📋 開發資訊

### 重要修改

- ✅ 修復了 Color 物件 JSON 序列化問題
- ✅ 統一使用端口 8100 作為狀態 API
- ✅ 清理了 Flask API 中的舊端點
- ✅ 更新了所有測試腳本

### 檔案結構

```
├── docker-compose.yml           # 服務配置
├── test_websocket_status.sh     # 狀態測試腳本
├── start_llm_clients.sh         # 客戶端啟動腳本
├── stop_llm_clients.sh          # 客戶端停止腳本
├── catanatron/multiplayer/
│   ├── game_engine_server.py    # 遊戲引擎（修復了JSON序列化）
│   └── llm_agent_client.py      # LLM客戶端
└── catanatron/web/
    └── api.py                   # Flask API（已清理舊端點）
```

---

## 🎯 快速診斷

一行命令檢查整個系統：

```bash
curl -s http://localhost:8100/status | jq '.summary'
```

可能的輸出：

- `"Waiting for players - 0/3 connected"` - 等待玩家連接
- `"Ready to start! 3 players connected (min: 3)"` - 準備開始
- `"Game in progress - 3 players connected, current player: RED"` - 遊戲進行中
