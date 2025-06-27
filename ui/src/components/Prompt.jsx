import React from "react";
import { isPlayersTurn } from "../utils/stateUtils";

import "./Prompt.scss";

function findTileByCoordinate(gameState, coordinate) {
  for (const tile of Object.values(gameState.tiles)) {
    if (JSON.stringify(tile.coordinate) === JSON.stringify(coordinate)) {
      return tile;
    }
  }
}

function findTileById(gameState, tileId) {
  return gameState.tiles[tileId];
}

function getTileString(tile) {
  const { number = "THE", resource = "DESERT" } = tile.tile;
  return `${number} ${resource}`;
}

function getShortTileString(tileTile) {
  return tileTile.number || tileTile.type;
}

// 控制log輸出
const resourceMap = {
  WOOD: "木頭",
  BRICK: "磚頭",
  SHEEP: "羊毛",
  WHEAT: "小麥",
  ORE: "礦石"
};

const playerMap = {
  RED: "玩家1",
  BLUE: "玩家2",
  ORANGE: "玩家3",
  WHITE: "玩家4",
}

export function humanizeAction(gameState, action) {
  // const botColors = gameState.bot_colors;
  // const player = botColors.includes(action[0]) ? "電腦" : "你";
  const player = playerMap[action[0]] || action[0];
  switch (action[1]) {
    case "ROLL":
      return `${player} 骰了 ${action[2][0] + action[2][1]}`;
    case "DISCARD":
      return `${player} 丢棄了資源`;
    case "BUY_DEVELOPMENT_CARD":
      return `${player} 購買了發展卡`;
    case "BUILD_SETTLEMENT":{
      const parts = action[1].split("_");
      const building = parts[parts.length - 1];
      const tileId = action[2];
      const tiles = gameState.adjacent_tiles[tileId];
      const tileString = tiles.map(getShortTileString).join("-");
      return `${player} 在 ${tileString} 建造了村莊`;
    }
    case "BUILD_CITY": {
      const parts = action[1].split("_");
      const building = parts[parts.length - 1];
      const tileId = action[2];
      const tiles = gameState.adjacent_tiles[tileId];
      const tileString = tiles.map(getShortTileString).join("-");
      return `${player} 在 ${tileString} 建造了城市`;
    }
    case "BUILD_ROAD": {
      const edge = action[2];
      const a = gameState.adjacent_tiles[edge[0]].map((t) => t.id);
      const b = gameState.adjacent_tiles[edge[1]].map((t) => t.id);
      const intersection = a.filter((t) => b.includes(t));
      const tiles = intersection.map(
        (tileId) => findTileById(gameState, tileId).tile
      );
      const edgeString = tiles.map(getShortTileString).join("-");
      return `${player} 在 ${edgeString} 建造了道路`;
    }
    case "PLAY_KNIGHT_CARD": {
      return `${player} 出了騎士卡`;
    }
    case "PLAY_ROAD_BUILDING": {
      return `${player} 出了道路建設卡`
    }
    case "PLAY_MONOPOLY": {
      const Resource = resourceMap[action[2]] || action[2];
      return `${player} 出了壟斷卡，壟斷了 ${Resource}`;
    }
    case "PLAY_YEAR_OF_PLENTY": {
      const firstResource = resourceMap[action[2][0]] || action[2][0];
      const secondResource = resourceMap[action[2][1]] || action[2][1];
      if (secondResource != null) {
        return `${player} 出了豐饒之年卡，獲得了 ${firstResource} 和 ${secondResource}`;
      } else {
        return `${player} 出了豐饒之年卡，獲得了 ${firstResource}`;
      }
    }
    case "MOVE_ROBBER": {
      const tile = findTileByCoordinate(gameState, action[2][0]);
      const tileString = getTileString(tile);
      const resource = action[2][2] ? resourceMap[action[2][2]] : "沒有資源";
      const enemy = action[2][1] ? playerMap[action[2][1]] : "沒有玩家";
      if (action[2][1] != null) {
        return `${player} 移動了強盜到 ${tileString}，偷取了 ${enemy} 的 ${resource}`;
      }else {
        return `${player} 移動了強盜到 ${tileString}，沒有偷取任何資源`;
      }
    }
    case "MARITIME_TRADE": {
      const [label,type] = humanizeTradeAction(action);
      if (type === "bank") {
        return `${player} 進行了銀行貿易 ${label}`;
      }else{
        return `${player} 進行了海上貿易 ${label}`;
      }
      
    }
    case "END_TURN":
      return `${player} 結束回合`;
    case "OFFER_TRADE":
      const [resource_INFO1, resource_INFO2] = trade_log(action);
      return `${player} 提出交易: ${resource_INFO1.join(", ")} 換 ${resource_INFO2.join(", ")}`;
    case "ACCEPT_TRADE":
      return `${player} 願意貿易`;
    case "REJECT_TRADE":
      return `${player} 拒絕了本次貿易`;
    case "CONFIRM_TRADE":
      const player2Color = playerMap[action[2][10]] || action[2][10];
      return `${player} 確認了 ${player2Color} 提出的貿易`;
    case "CANCEL_TRADE":
      return `${player} 取消了本次貿易`;
    default:
      return `${player} ${action.slice(1)}`;
  }
}
function trade_log(action){
  let resource = [];
    let resource2= [];
    
    for (let i = 0; i < action[2].length; i++) {
      let resourceInfo = {
        num: null,
        translated: null
      };
      let resourceInfo2 = {
        num: null,
        translated: null
      };

      switch (i % 10) {
      case(0):
        if (action[2][i] === 0) {
          resourceInfo.translated = "";
          resourceInfo.num = "";
        } else {
          resourceInfo.translated = "木頭";
          resourceInfo.num = action[2][i];
        }
        break;
      case(1):
        if (action[2][i] === 0) {
          resourceInfo.translated = "";
          resourceInfo.num = "";
        } else {
          resourceInfo.translated = "磚頭";
          resourceInfo.num = action[2][i];
        }
        break;
      case(2):
        if (action[2][i] === 0) {
          resourceInfo.translated = "";
          resourceInfo.num = "";
        } else {
          resourceInfo.translated = "羊毛";
          resourceInfo.num = action[2][i];
        }
        break;
      case(3):
        if (action[2][i] === 0) {
          resourceInfo.translated = "";
          resourceInfo.num = "";
        } else {
          resourceInfo.translated = "小麥";
          resourceInfo.num = action[2][i];
        }
        break;
      case(4):
        if (action[2][i] === 0) {
          resourceInfo.translated = "";
          resourceInfo.num = "";
        } else {
          resourceInfo.translated = "礦石";
          resourceInfo.num = action[2][i];
        }
        break;
      case(5):
        if (action[2][i] === 0) {
          resourceInfo2.translated = "";
          resourceInfo2.num = "";
        } else {
          resourceInfo2.translated = "木頭";
          resourceInfo2.num = action[2][i];
        }
        break;
      case(6):
        if (action[2][i] === 0) {
          resourceInfo2.translated = "";
          resourceInfo2.num = "";
        } else {
          resourceInfo2.translated = "磚頭";
          resourceInfo2.num = action[2][i];
        }
        break;
      case(7):
        if (action[2][i] === 0) {
          resourceInfo2.translated = "";
          resourceInfo2.num = "";
        } else {
          resourceInfo2.translated = "羊毛";
          resourceInfo2.num = action[2][i];
        } 
        break;
      case(8):
        if (action[2][i] === 0) {
          resourceInfo2.translated = "";
          resourceInfo2.num = "";
        } else {
          resourceInfo2.translated = "小麥";
          resourceInfo2.num = action[2][i];
        }
        break;
      case(9):
        if (action[2][i] === 0) {
          resourceInfo2.translated = "";
          resourceInfo2.num = "";
        } else {
          resourceInfo2.translated = "礦石";
          resourceInfo2.num = action[2][i];
        }
        break;
      }
      resource.push(resourceInfo);
      resource2.push(resourceInfo2);
    }
      
      // 組合 num + translated + resource 的輸出
    const resourceDescriptions = resource
      .filter(item => item.num && item.translated) // 過濾掉空值
      .map(item => `${item.num}個${item.translated}`);
    const resourceDescriptions2 = resource2
      .filter(item => item.num && item.translated) // 過濾掉空值
      .map(item => `${item.num}個${item.translated}`);
  return [resourceDescriptions,resourceDescriptions2];
}
export function humanizeTradeAction(action) {
  const out = action[2].slice(0, 4).filter((resource) => resource !== null);
  const fromResource = resourceMap[out[0]] || out[0];
  const toResource = resourceMap[action[2][4]] || action[2][4];
  if (out.length === 4) {
    return [`${out.length} ${fromResource} 換 ${toResource}`, "bank"];
  }else{
    return [`${out.length} ${fromResource} 換 ${toResource}`, "maritime"];
  }
}

function humanizePrompt(current_prompt) {
  switch (current_prompt) {
    case "ROLL":
      return `YOUR TURN`;
    case "PLAY_TURN":
      return `YOUR TURN`;
    case "BUILD_INITIAL_SETTLEMENT":
    case "BUILD_INITIAL_ROAD":
    default: {
      const prompt = current_prompt.replaceAll("_", " ");
      return `PLEASE ${prompt}`;
    }
  }
}

export default function Prompt({ gameState, isBotThinking }) {
  let prompt = "";
  if (isBotThinking) {
    // Do nothing, but still render.
  } else if (gameState.winning_color) {
    const color = playerMap[gameState.winning_color] || gameState.winning_color;
    prompt = `遊戲結束 恭喜, ${color} 勝利!`;
    return <div className="prompt-fin">{prompt}</div>;
  } else if (isPlayersTurn(gameState)) {
    prompt = humanizePrompt(gameState.current_prompt);
  } else {
    // prompt = humanizeAction(gameState.actions[gameState.actions.length - 1], gameState.bot_colors);
  }
  return <div className="prompt">{prompt}</div>;
}
