# Catanatron 變數玩家支援指南

## 概述

Catanatron 現在支援 **2-4 人變數玩家** 遊戲，不再需要固定 4 人才能開始。系統會智能等待玩家加入，並在達到條件時自動開始遊戲。

## 🚀 快速開始

### 使用自動化腳本（推薦）

```bash
# 預設模式：2-4 人遊戲，等待 10 秒
./run_catanatron.sh

# 2 人遊戲模式
./run_catanatron.sh --min-players 2 --max-players 2 --wait-time 5

# 3 人遊戲模式
./run_catanatron.sh --min-players 3 --max-players 3 --wait-time 8

# 查看所有選項
./run_catanatron.sh --help
```

### 手動啟動

```bash
# 啟動伺服器
python start_server.py --min-players 2 --max-players 4 --wait-time 10

# 在另一個終端啟動 LLM 客戶端
cd catanatron/catanatron/multiplayer
uv run python llm_agent_client.py --port 8001 --color RED --debug
uv run python llm_agent_client.py --port 8002 --color BLUE --debug
```

## 📋 功能特色

### ✅ 智能等待機制

- **最少玩家數達成**: 開始倒數計時
- **最多玩家數達成**: 立即開始遊戲
- **靈活配置**: 支援 2-4 人任意組合

### ✅ 自動化管理

- **端口衝突處理**: 自動檢測並清理佔用的端口
- **進程管理**: 優雅的啟動和關閉
- **完整日誌**: 詳細的運行記錄

### ✅ LLM 整合

- **Google Gemini 2.0 Flash**: 最新的 AI 模型
- **多玩家支援**: 每個玩家獨立的 AI 決策
- **調試模式**: 詳細的決策過程記錄

## 🎮 遊戲模式

### 2 人遊戲

```bash
./run_catanatron.sh --min-players 2 --max-players 2
```

- **玩家**: RED, BLUE
- **特點**: 快速開始，適合測試和快速遊戲

### 3 人遊戲

```bash
./run_catanatron.sh --min-players 3 --max-players 3
```

- **玩家**: RED, BLUE, WHITE
- **特點**: 平衡的競爭環境

### 4 人遊戲（傳統模式）

```bash
./run_catanatron.sh --min-players 4 --max-players 4
```

- **玩家**: RED, BLUE, WHITE, ORANGE
- **特點**: 完整的 Catan 體驗

### 彈性模式

```bash
./run_catanatron.sh --min-players 2 --max-players 4 --wait-time 15
```

- **行為**: 2 人即可開始，最多等待 4 人，15 秒後自動開始

## ⚙️ 配置選項

### 伺服器參數

| 參數            | 預設值  | 說明             |
| --------------- | ------- | ---------------- |
| `--min-players` | 2       | 最少玩家數 (2-4) |
| `--max-players` | 4       | 最多玩家數 (2-4) |
| `--wait-time`   | 10      | 等待時間（秒）   |
| `--host`        | 0.0.0.0 | 伺服器主機地址   |
| `--no-cleanup`  | False   | 跳過端口清理     |

### 端口配置

| 玩家顏色 | 端口 | WebSocket 地址      |
| -------- | ---- | ------------------- |
| RED      | 8001 | ws://localhost:8001 |
| BLUE     | 8002 | ws://localhost:8002 |
| WHITE    | 8003 | ws://localhost:8003 |
| ORANGE   | 8004 | ws://localhost:8004 |

## 🔧 技術實現

### 核心修改

1. **GameEngineServer 類增強**

   - 新增 `min_players` 和 `max_players` 參數
   - 實現智能等待邏輯
   - 支援動態玩家數量

2. **start_server.py 腳本**

   - 命令行參數解析
   - 自動端口清理
   - 參數驗證

3. **run_catanatron.sh 自動化腳本**
   - 完整的生命週期管理
   - 多進程協調
   - 錯誤處理和清理

### 遊戲開始邏輯

```python
async def check_all_players_connected(self):
    connected_count = len([conn for conn in self.player_connections.values() if conn.connected])

    if connected_count >= self.max_players:
        # 達到最大玩家數，立即開始
        await self.start_game()
    elif connected_count >= self.min_players:
        # 達到最少玩家數，開始倒數
        if not self.start_game_timer:
            self.start_game_timer = asyncio.create_task(self._start_game_after_delay())
    else:
        # 等待更多玩家
        await self.broadcast_waiting_message()
```

## 📊 使用範例

### 範例 1: 快速 2 人遊戲

```bash
# 啟動 2 人遊戲，5 秒等待
./run_catanatron.sh --min-players 2 --max-players 2 --wait-time 5

# 預期行為：
# - 第 1 個玩家連接：等待更多玩家
# - 第 2 個玩家連接：立即開始遊戲
```

### 範例 2: 彈性 3-4 人遊戲

```bash
# 啟動彈性遊戲，12 秒等待
./run_catanatron.sh --min-players 3 --max-players 4 --wait-time 12

# 預期行為：
# - 1-2 個玩家：等待更多玩家
# - 3 個玩家：開始 12 秒倒數，期間可加入第 4 個玩家
# - 4 個玩家：立即開始遊戲
# - 12 秒後：以 3 個玩家開始遊戲
```

## 🐛 故障排除

### 常見問題

**Q: 端口被佔用怎麼辦？**

```bash
# 自動清理（推薦）
./run_catanatron.sh

# 手動清理
python start_server.py --min-players 2 --max-players 2
```

**Q: 遊戲沒有開始？**

- 檢查是否有足夠的客戶端連接
- 查看 `server.log` 日誌文件
- 確認 LLM 客戶端正常運行

**Q: 如何停止遊戲？**

```bash
# 如果使用 run_catanatron.sh
Ctrl+C

# 手動清理
pkill -f "start_server.py"
pkill -f "llm_agent_client.py"
```

### 日誌檢查

```bash
# 查看即時日誌
tail -f server.log

# 查看最近的日誌
tail -n 50 server.log

# 搜尋特定內容
grep "game_started" server.log
```

## 🔄 向後兼容性

- ✅ 完全向後兼容原有的 4 人遊戲模式
- ✅ 現有的 LLM 客戶端無需修改
- ✅ 原有的遊戲邏輯保持不變
- ✅ API 接口完全兼容

## 📈 性能優化

- **並行處理**: 多個玩家同時連接處理
- **智能等待**: 避免不必要的延遲
- **資源管理**: 自動清理無用進程和端口
- **錯誤恢復**: 優雅的錯誤處理和恢復機制

## 🎯 未來擴展

- [ ] Web UI 支援變數玩家
- [ ] 觀戰模式
- [ ] 遊戲重播功能
- [ ] 更多 AI 模型支援
- [ ] 自定義地圖支援

---

## 📞 支援

如有問題或建議，請查看：

- 日誌文件：`server.log`
- 進程狀態：`ps aux | grep -E "(start_server|llm_agent)"`
- 端口狀態：`lsof -i :8001-8004`

**享受你的 Catanatron 變數玩家遊戲！** 🎲🏆
