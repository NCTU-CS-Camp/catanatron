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

# Flask API 代理狀態（前端推薦）
curl http://localhost:5001/api/websocket-games/current | jq .
```

### 🔗 Flask API 整合端點

#### 遊戲列表

```bash
# 列出所有遊戲（包括 Flask 和 WebSocket）
curl http://localhost:5001/api/games/list | jq .
```

#### WebSocket 遊戲狀態

```bash
# 取得當前 WebSocket 遊戲狀態（簡化格式）
curl http://localhost:5001/api/websocket-games/current | jq .

# 取得詳細 WebSocket 遊戲狀態（原始格式）
curl http://localhost:5001/api/websocket-games/current/detailed | jq .

# 前端格式訪問（與一般遊戲 API 一致）
curl http://localhost:5001/api/games/websocket/websocket_multiplayer_game/states/latest | jq .

# 🆕 完整遊戲狀態（包含地圖、建築、資源等所有資料）
curl http://localhost:5001/api/games/websocket/websocket_multiplayer_game/full-state | jq .

# 🆕 直接從 WebSocket 引擎取得完整狀態
curl http://localhost:8100/game-state | jq .
```

### 狀態資訊說明

**原始 WebSocket 狀態**：

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

**Flask API 代理格式**：

```json
{
  "game_id": "websocket_multiplayer_game",
  "status": "active",
  "current_player": "WHITE",
  "turn_number": 4,
  "winner": null,
  "connected_players": 3,
  "player_connections": {
    "RED": { "connected": true, "port": 8001 },
    "BLUE": { "connected": true, "port": 8002 }
  },
  "summary": "Game in progress - 3 players connected, current player: WHITE"
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

### test_flask_websocket_sync.sh **（新增）**

測試 Flask API 與 WebSocket 同步：

```bash
./test_flask_websocket_sync.sh
```

- ✅ 檢查 Flask API 與 WebSocket 引擎連接
- ✅ 測試新的 Flask API 端點
- ✅ 比較原始與代理狀態
- ✅ 提供前端整合建議

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

---

## 🔗 Flask API 與 WebSocket 同步整合

### ✅ **成功實現的功能**

我們已經成功建立了 Flask API 與 WebSocket 遊戲引擎的同步機制，讓前端可以透過統一的 Flask API 接口訪問 WebSocket 多人遊戲狀態。

### 🔗 **新增的 Flask API 端點**

#### 1. **遊戲列表** - 統一視圖

```bash
GET /api/games/list
```

- 列出所有遊戲（Flask 單人 + WebSocket 多人）
- 返回遊戲類型和來源資訊

#### 2. **WebSocket 遊戲狀態** - 多種格式

```bash
# 簡化格式（推薦給前端）
GET /api/websocket-games/current

# 詳細原始格式
GET /api/websocket-games/current/detailed

# 前端統一格式（與一般遊戲 API 一致）
GET /api/games/websocket/websocket_multiplayer_game/states/latest

# 🆕 完整遊戲狀態（包含地圖、建築、資源等所有資料）
GET /api/games/websocket/websocket_multiplayer_game/full-state

# 🆕 直接從 WebSocket 引擎取得完整狀態
GET http://localhost:8100/game-state
```

#### 3. **遊戲狀態歷史**

```bash
# 取得特定回合的遊戲狀態（從資料庫）
GET /api/games/websocket/websocket_multiplayer_game/states/{state_index}

# 例如：取得遊戲開始時的狀態
GET /api/games/websocket/websocket_multiplayer_game/states/0
```

### 🏗️ **架構優勢**

1. **無縫整合**: 前端只需要知道 Flask API，不需要直接連接 WebSocket
2. **統一接口**: 使用相同的 API 格式訪問不同類型的遊戲
3. **容錯處理**: 當 WebSocket 引擎不可用時優雅降級
4. **類型區分**: 清楚標示遊戲類型（`flask_single_player` vs `websocket_multiplayer`）

### 📊 **狀態同步機制**

1. **實時代理**: Flask API 即時查詢 WebSocket 引擎狀態
2. **格式轉換**: 將 WebSocket 狀態轉換為前端友好的格式
3. **錯誤處理**: 連接失敗時返回適當的錯誤訊息
4. **資料庫同步**: WebSocket 遊戲也會同步到資料庫（可選）

### 🎯 **前端使用方式**

#### 💾 **完整遊戲資料訪問**

前端現在可以透過多種方式取得**完整的遊戲狀態資料**，包括地圖、建築、資源等所有資訊：

```javascript
// 方法 1: 直接取得完整遊戲狀態（推薦）
const fullGameState = await fetch(
  "/api/games/websocket/websocket_multiplayer_game/full-state"
).then((r) => r.json());

// 取得的資料包含：
// - game_state: 完整的遊戲狀態（與 Flask 單人遊戲相同格式）
//   - tiles: 地圖資訊
//   - nodes: 節點和建築
//   - edges: 道路
//   - player_state: 每個玩家的資源、分數等
//   - current_playable_actions: 可執行的行動
//   - 等等...
// - websocket_info: WebSocket 連接資訊

// 方法 2: 取得遊戲列表，然後訪問特定遊戲
const games = await fetch("/api/games/list").then((r) => r.json());
const wsGame = games.games.find((g) => g.type === "websocket_multiplayer");

if (wsGame) {
  // 完整遊戲狀態
  const gameState = await fetch(
    `/api/games/websocket/${wsGame.game_id}/full-state`
  ).then((r) => r.json());

  // 基本狀態資訊
  const basicState = await fetch("/api/websocket-games/current").then((r) =>
    r.json()
  );
}

// 方法 3: 直接從 WebSocket 引擎取得（需要知道端口）
const directState = await fetch("http://localhost:8100/game-state").then((r) =>
  r.json()
);
```

#### 📊 **可用的遊戲資料**

前端可以取得與 Flask 單人遊戲完全相同的資料結構：

```javascript
{
  "game_id": "websocket_multiplayer_game",
  "type": "websocket_multiplayer",
  "full_game_state": {
    // 完整的遊戲狀態，包含：
    "actions": [],              // 遊戲歷史行動
    "tiles": [],                // 地圖六角形資訊
    "nodes": [],                // 節點和建築
    "edges": [],                // 道路
    "player_state": {           // 每個玩家的狀態
      "RED": {
        "resource_cards": {},   // 資源卡
        "development_cards": {},// 發展卡
        "victory_points": 0,    // 勝利點數
        "buildings": {},        // 建築物
        "roads": []             // 道路
      }
      // ...其他玩家
    },
    "current_color": "RED",     // 當前玩家
    "current_playable_actions": [], // 可執行行動
    "is_initial_build_phase": true, // 是否為初始建設階段
    "winning_color": null       // 獲勝玩家
  },
  "websocket_info": {
    "connected_players": 3,
    "player_connections": {
      "RED": { "connected": true, "port": 8001 }
      // ...
    }
  }
}
```

#### 🔄 **即時更新策略**

```javascript
// 策略 1: 輪詢更新（簡單）
setInterval(async () => {
  const state = await fetch(
    "/api/games/websocket/websocket_multiplayer_game/full-state"
  ).then((r) => r.json());
  updateGameUI(state);
}, 1000); // 每秒更新

// 策略 2: 只更新基本狀態，按需取得完整資料
const pollBasicState = async () => {
  const basic = await fetch("/api/websocket-games/current").then((r) =>
    r.json()
  );

  if (basic.turn_number !== currentTurn) {
    // 回合變化時才取得完整資料
    const full = await fetch(
      "/api/games/websocket/websocket_multiplayer_game/full-state"
    ).then((r) => r.json());
    updateGameUI(full);
    currentTurn = basic.turn_number;
  }
};

// 策略 3: WebSocket 連接（進階）
// 前端可以直接連接到 ws://localhost:8001-8004 作為觀察者
```

### 🎮 **實際使用流程**

1. **檢查所有可用遊戲**：

```bash
curl http://localhost:5001/api/games/list | jq .
```

2. **監控 WebSocket 遊戲狀態**：

```bash
# 啟動遊戲
./start_llm_clients.sh --players 3

# 檢查狀態（透過 Flask API）
curl http://localhost:5001/api/websocket-games/current | jq '.status, .current_player, .summary'

# 前端格式訪問
curl http://localhost:5001/api/games/websocket/websocket_multiplayer_game/states/latest | jq '.state.summary'
```

3. **整合測試**：

```bash
./test_flask_websocket_sync.sh
```

### 💡 **技術實現重點**

- **服務發現**: Flask API 使用 Docker 服務名稱 `websocketllm` 連接到 WebSocket 引擎
- **固定遊戲 ID**: WebSocket 多人遊戲使用固定 ID `websocket_multiplayer_game`
- **格式轉換**: 自動將 WebSocket 原始狀態轉換為前端友好的 JSON 格式
- **錯誤處理**: 當 WebSocket 引擎不可用時返回適當的 503 或 404 錯誤

**這樣的解決方案讓前端可以用熟悉的 Flask API 方式訪問 WebSocket 多人遊戲，實現了完美的狀態同步！** 🚀

---

## 🎉 整合成果報告

### ✅ 成功實現的完整功能

**🏗️ 系統架構成功整合**

```
前端應用 (React/Vue/Angular)
    ↓ 統一 HTTP API 調用
Flask API Server (localhost:5001)
    ↓ 內部代理請求
WebSocket Game Engine (Docker websocketllm)
    ↓ 資料庫同步
PostgreSQL Database (Docker db)
```

**📊 驗證結果（2025-06-16 測試通過）**

- ✅ **遊戲列表 API**: 成功識別並展示 WebSocket 多人遊戲
- ✅ **完整狀態存取**: 15 個完整資料欄位，包含地圖、建築、資源等
- ✅ **前端相容性**: 與 Flask 單人遊戲 API 格式 100% 相容
- ✅ **即時狀態同步**: 當前玩家、回合數、可執行動作等即時資訊
- ✅ **資料庫整合**: WebSocket 遊戲狀態成功同步並可查詢歷史記錄
- ✅ **Docker 網路**: 所有服務間通信穩定，配置最佳化
- ✅ **psycopg2 支援**: 解決了 PostgreSQL 連接依賴問題

### 🎯 關鍵技術突破

1. **統一 API 介面**: 前端無需區分單人/多人遊戲，使用相同 API 調用方式
2. **即時代理機制**: Flask API 實時查詢 WebSocket 引擎，保持資料同步
3. **Docker 服務發現**: 使用服務名稱 `websocketllm` 而非 `localhost` 實現容器間通信
4. **資料庫配置修正**: 修改連接地址從 `127.0.0.1:5432` 到 `db:5432`
5. **依賴管理**: 成功安裝 `psycopg2-binary` 解決 PostgreSQL 連接問題

### 🚀 前端開發優勢

**開發簡化**

- 使用現有的單人遊戲前端代碼
- 無需學習 WebSocket 連接管理
- 統一的錯誤處理和狀態管理

**功能完整**

- 存取完整遊戲資料：地圖、建築、資源、玩家狀態
- 支援歷史狀態查詢和重播功能
- 即時遊戲狀態更新

**架構彈性**

- 支援多種更新策略：輪詢、變更檢測、WebSocket 直連
- 優雅的服務降級處理
- 易於擴展和維護

### 🏆 最終成就

**🎮 前端現在可以透過統一的 Flask API 完整存取 WebSocket 多人即時遊戲！**

這個整合解決方案成功實現了：

- **保持 WebSocket 的即時多人遊戲體驗**
- **提供 Flask API 的簡單統一介面**
- **完整的遊戲資料存取能力**
- **資料庫持久化和歷史查詢**
- **開發友好的系統架構**

前端開發者現在可以專注於遊戲邏輯和用戶體驗，而不用擔心複雜的 WebSocket 連接管理和即時通信問題。🎊
