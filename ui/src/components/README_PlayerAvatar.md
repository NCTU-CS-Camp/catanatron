# 卡坦島遊戲日志頭像功能

## 功能概述

為左側抽屜（LeftDrawer）的遊戲日志添加了玩家頭像功能，使每句日志消息前都會顯示對應玩家的彩色頭像，讓遊戲歷史更加直觀易讀。

## 新增文件

### 1. `PlayerAvatar.jsx` - 玩家頭像組件
- 支持四種玩家顏色：RED（紅色）、BLUE（藍色）、ORANGE（橙色）、WHITE（白色）
- 每個玩家都有獨特的圖標和漸變背景色
- 支持三種尺寸：small、medium、large
- 支持顯示/隱藏玩家名稱
- 帶有懸停動畫效果

### 2. `PlayerAvatar.scss` - 頭像組件樣式
- 圓形頭像設計，帶有漸變背景和陰影效果
- 響應式尺寸設計
- 平滑的懸停動畫
- 支持不同的玩家主題色

### 3. `test.jsx` - 測試和演示頁面
- 展示頭像功能的完整演示
- 包含模擬的遊戲日志數據
- 可切換顯示/隱藏玩家名稱
- 展示不同尺寸的頭像效果

## 修改的文件

### 1. `LeftDrawer.jsx`
- 導入了 `PlayerAvatar` 組件
- 修改了日志渲染邏輯，在每條消息前添加頭像
- 優化了日志項目的HTML結構

### 2. `LeftDrawer.scss`
- 更新了日志樣式，添加了卡片式設計
- 改善了日志項目的背景和邊框
- 添加了懸停效果
- 優化了頭像和文本的對齊

## 使用方法

### 基本用法
```jsx
import PlayerAvatar from './components/PlayerAvatar';

// 小尺寸頭像
<PlayerAvatar color="RED" size="small" />

// 中等尺寸頭像，顯示玩家名稱
<PlayerAvatar color="BLUE" size="medium" showName={true} />

// 大尺寸頭像
<PlayerAvatar color="ORANGE" size="large" />
```

### 在日志中使用
```jsx
{gameState.actions.map((action, i) => (
  <div key={i} className="action">
    <div className="action-content">
      <PlayerAvatar color={action[0]} size="small" />
      <span className="action-text">
        {humanizeAction(gameState, action)}
      </span>
    </div>
  </div>
))}
```

## 玩家配置

| 顏色   | 玩家名稱 | 圖標 | 主色調 |
|--------|----------|------|--------|
| RED    | 玩家1    | 🔴   | #d32f2f |
| BLUE   | 玩家2    | 🔵   | #1976d2 |
| ORANGE | 玩家3    | 🟠   | #f57c00 |
| WHITE  | 玩家4    | ⚪   | #616161 |

## 尺寸規格

| 尺寸   | 頭像大小 | 圖標大小 | 適用場景 |
|--------|----------|----------|----------|
| small  | 22×22px  | 10px     | 日志消息 |
| medium | 30×30px  | 14px     | 一般顯示 |
| large  | 38×38px  | 18px     | 重要展示 |

## 視覺特效

- **漸變背景**：每個頭像都有對應顏色的漸變背景
- **陰影效果**：頭像帶有柔和的陰影，增加層次感
- **懸停動畫**：鼠標懸停時頭像會放大並增強陰影
- **卡片式日志**：日志項目采用卡片式設計，帶有透明背景和模糊效果

## 測試頁面

要查看頭像功能的完整演示，可以訪問 `test.jsx` 組件：

1. 頭像尺寸展示
2. 模擬遊戲日志（帶頭像）
3. 所有玩家頭像一覽
4. 交互式控制選項

## 技術特點

- **組件化設計**：頭像作為獨立組件，可重複使用
- **響應式佈局**：適配不同屏幕尺寸
- **性能優化**：使用 CSS 動畫而非 JavaScript
- **無障礙支持**：包含 title 屬性提供輔助信息
- **主題一致性**：與現有的遊戲 UI 風格保持一致

## 未來擴展

可考慮的功能擴展：
- 自定義頭像上傳
- 動畫表情反應
- 玩家狀態指示器
- 成就徽章顯示
- 頭像框架系統
