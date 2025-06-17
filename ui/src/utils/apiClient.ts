import axios from "axios";

import { API_URL } from "../configuration";

type Player = "HUMAN" | "RANDOM" | "CATANATRON";
type StateIndex = number | "latest";

export async function createGame(players: Player[]) {
  const response = await axios.post(API_URL + "/api/games", { players });
  return response.data.game_id;
}

export async function getState(
  gameId: string,
  stateIndex: StateIndex = "latest"
) {
  const response = await axios.get(
    `${API_URL}/api/games/${gameId}/states/${stateIndex}`
  );
  return response.data;
}

/** action=undefined means bot action */
export async function postAction(gameId: string, action = undefined) {
  const response = await axios.post(
    `${API_URL}/api/games/${gameId}/actions`,
    action
  );
  return response.data;
}

type MCTSSuccessBody = {
  success: true;
  probabilities: any;
  state_index: number;
};
type MCTSErrorBody = {
  success: false;
  error: string;
  trace: string;
};

export async function getMctsAnalysis(
  gameId: string,
  stateIndex: StateIndex = "latest"
) {
  try {
    console.log("Getting MCTS analysis for:", {
      gameId,
      stateIndex,
      url: `${API_URL}/api/games/${gameId}/states/${stateIndex}/mcts-analysis`,
    });

    if (!gameId) {
      throw new Error("No gameId provided to getMctsAnalysis");
    }

    const response = await axios.get<MCTSSuccessBody | MCTSErrorBody>(
      `${API_URL}/api/games/${gameId}/states/${stateIndex}/mcts-analysis`
    );

    console.log("MCTS analysis response:", response.data);
    return response.data;
  } catch (error: any) {
    // AxiosResponse<MCTSErrorBody>
    console.error("MCTS analysis error:", {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      stack: error.stack,
    });
    throw error;
  }
}

// WebSocket 遊戲相關 API
export async function getGamesList() {
  try {
    const response = await axios.get(`${API_URL}/api/games/list`);
    return response.data;
  } catch (error) {
    console.error("Failed to get games list:", error);
    throw error;
  }
}

export async function getCurrentWebSocketGame() {
  try {
    const response = await axios.get(`${API_URL}/api/websocket-games/current`);
    return response.data;
  } catch (error) {
    console.error("Failed to get current WebSocket game:", error);
    throw error;
  }
}

export async function getDetailedWebSocketGame() {
  try {
    const response = await axios.get(
      `${API_URL}/api/websocket-games/current/detailed`
    );
    return response.data;
  } catch (error) {
    console.error("Failed to get detailed WebSocket game:", error);
    throw error;
  }
}

export async function getWebSocketGameState() {
  try {
    // 直接從 WebSocket 引擎獲取完整遊戲狀態
    const response = await axios.get("http://localhost:8100/game-state");
    return response.data.game_state; // 返回實際的遊戲狀態數據
  } catch (error) {
    console.error("Failed to get WebSocket game state:", error);
    // 如果直接連接失敗，嘗試通過 Flask API 代理
    try {
      const fallbackResponse = await axios.get(
        `${API_URL}/api/games/websocket/websocket_multiplayer_game/full-state`
      );
      return (
        fallbackResponse.data.full_game_state ||
        fallbackResponse.data.game_state
      );
    } catch (fallbackError) {
      console.error("Fallback API also failed:", fallbackError);
      throw error;
    }
  }
}

// WebSocket 狀態檢查
export async function checkWebSocketEngineStatus() {
  try {
    const response = await axios.get("http://localhost:8100/status");
    return response.data;
  } catch (error) {
    console.error("WebSocket engine not available:", error);
    return null;
  }
}
