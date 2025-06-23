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
export function humanizeAction(gameState, action) {
  const botColors = gameState.bot_colors;
  const player = botColors.includes(action[0]) ? "電腦" : "你";
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
      return `${player} 出了壟斷卡，壟斷了 ${action[2]}`;
    }
    case "PLAY_YEAR_OF_PLENTY": {
      const firstResource = action[2][0];
      const secondResource = action[2][1];
      if (secondResource) {
        return `${player} 出了豐饒之年卡，獲得了 ${firstResource} 和 ${secondResource}`;
      } else {
        return `${player} 出了豐饒之年卡，獲得了 ${firstResource}`;
      }
    }
    case "MOVE_ROBBER": {
      const tile = findTileByCoordinate(gameState, action[2][0]);
      const tileString = getTileString(tile);
      const stolenResource = action[2][2] ? ` (得到了 ${action[2][2]})` : '';
      return `${player} 偷了 ${tileString}${stolenResource}`;
    }
    case "MARITIME_TRADE": {
      const label = humanizeTradeAction(action);
      return `${player} 進行了海上貿易 ${label}`;
    }
    case "END_TURN":
      return `${player} 結束回合`;
    default:
      return `${player} ${action.slice(1)}`;
  }
}

export function humanizeTradeAction(action) {
  const out = action[2].slice(0, 4).filter((resource) => resource !== null);
  return `${out.length} ${out[0]} => ${action[2][4]}`;
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
    prompt = `遊戲結束 恭喜, ${gameState.winning_color}!`;
  } else if (isPlayersTurn(gameState)) {
    prompt = humanizePrompt(gameState.current_prompt);
  } else {
    // prompt = humanizeAction(gameState.actions[gameState.actions.length - 1], gameState.bot_colors);
  }
  return <div className="prompt">{prompt}</div>;
}
