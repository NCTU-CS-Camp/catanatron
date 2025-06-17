import React, { useEffect, useState, useContext } from "react";
import { useParams } from "react-router-dom";
import PropTypes from "prop-types";
import { GridLoader } from "react-spinners";
import { useSnackbar } from "notistack";

import ZoomableBoard from "./ZoomableBoard";
import ActionsToolbar from "./ActionsToolbar";

import "./GameScreen.scss";
import LeftDrawer from "../components/LeftDrawer";
import RightDrawer from "../components/RightDrawer";
import { store } from "../store";
import ACTIONS from "../actions";
import {
  getState,
  postAction,
  getWebSocketGameState,
} from "../utils/apiClient";
import { dispatchSnackbar } from "../components/Snackbar";
import { getHumanColor } from "../utils/stateUtils";

const ROBOT_THINKING_TIME = 300;

function GameScreen({ replayMode, websocketMode = false }) {
  const { gameId, stateIndex } = useParams();
  const { state, dispatch } = useContext(store);
  const { enqueueSnackbar, closeSnackbar } = useSnackbar();
  const [isBotThinking, setIsBotThinking] = useState(false);
  const [isWebSocketGame, setIsWebSocketGame] = useState(websocketMode);
  const [wsError, setWsError] = useState(null);
  const [wsDebugInfo, setWsDebugInfo] = useState(null);

  // 檢查是否為 WebSocket 遊戲
  useEffect(() => {
    if (
      websocketMode ||
      gameId === "websocket_multiplayer_game" ||
      gameId?.includes("websocket")
    ) {
      setIsWebSocketGame(true);
    }
  }, [gameId, websocketMode]);

  // Load game state
  useEffect(() => {
    if (!gameId) {
      return;
    }

    (async () => {
      try {
        let gameState;
        if (isWebSocketGame) {
          // 直接獲取 WebSocket 遊戲狀態
          gameState = await getWebSocketGameState();
          console.log(
            "WebSocket game state loaded successfully:",
            gameState?.current_color
          );
        } else {
          // 使用標準遊戲狀態 API
          gameState = await getState(gameId, stateIndex);
        }
        dispatch({ type: ACTIONS.SET_GAME_STATE, data: gameState });
      } catch (error) {
        console.error("Failed to load game state:", error);
        // 如果是 WebSocket 遊戲且失敗，嘗試顯示調試信息
        if (isWebSocketGame) {
          try {
            const { getCurrentWebSocketGame } = await import(
              "../utils/apiClient"
            );
            const currentGame = await getCurrentWebSocketGame();
            setWsDebugInfo(currentGame);
            setWsError(error.response?.data || error.message);

            // 創建調試狀態用於顯示
            const debugState = {
              websocket_debug: true,
              current_color: "SPECTATOR",
              bot_colors: [],
              winning_color: null,
              error: "無法獲取完整遊戲狀態",
              debug_info: currentGame,
            };
            dispatch({ type: ACTIONS.SET_GAME_STATE, data: debugState });
          } catch (debugError) {
            console.error("Failed to get debug info:", debugError);
            enqueueSnackbar(
              "無法連接到 WebSocket 遊戲，請檢查遊戲是否正在運行",
              {
                variant: "error",
              }
            );
          }
        }
      }
    })();
  }, [gameId, stateIndex, dispatch, isWebSocketGame, enqueueSnackbar]);

  // WebSocket 遊戲自動刷新
  useEffect(() => {
    if (isWebSocketGame && !replayMode) {
      const interval = setInterval(async () => {
        try {
          const gameState = await getWebSocketGameState();
          dispatch({ type: ACTIONS.SET_GAME_STATE, data: gameState });
        } catch (error) {
          console.error("Failed to refresh WebSocket game state:", error);
          // 刷新失敗時暫時跳過，等下次刷新
        }
      }, 2000); // 每 2 秒刷新一次

      return () => clearInterval(interval);
    }
  }, [isWebSocketGame, replayMode, dispatch]);

  // Maybe kick off next query?
  useEffect(() => {
    if (!state.gameState || replayMode || isWebSocketGame) {
      return;
    }
    if (
      state.gameState.bot_colors.includes(state.gameState.current_color) &&
      !state.gameState.winning_color
    ) {
      // Make bot click next action.
      (async () => {
        setIsBotThinking(true);
        const start = new Date();
        const gameState = await postAction(gameId);
        const requestTime = new Date() - start;
        setTimeout(() => {
          // simulate thinking
          setIsBotThinking(false);
          dispatch({ type: ACTIONS.SET_GAME_STATE, data: gameState });
          if (getHumanColor(gameState)) {
            dispatchSnackbar(enqueueSnackbar, closeSnackbar, gameState);
          }
        }, ROBOT_THINKING_TIME - requestTime);
      })();
    }
  }, [
    gameId,
    replayMode,
    state.gameState,
    dispatch,
    enqueueSnackbar,
    closeSnackbar,
    isWebSocketGame,
  ]);

  if (!state.gameState) {
    return (
      <main>
        <GridLoader
          className="loader"
          color="#000000"
          height={100}
          width={100}
        />
      </main>
    );
  }

  // 如果是 WebSocket 遊戲的調試模式，顯示調試信息
  if (state.gameState.websocket_debug) {
    return (
      <main
        style={{
          padding: "20px",
          backgroundColor: "#f5f5f5",
          minHeight: "100vh",
        }}
      >
        <div style={{ maxWidth: "800px", margin: "0 auto" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "16px",
              marginBottom: "20px",
            }}
          >
            <h1 className="logo">卡坦島</h1>
            <span
              style={{
                background: "linear-gradient(45deg, #667eea, #764ba2)",
                color: "white",
                padding: "4px 12px",
                borderRadius: "16px",
                fontSize: "12px",
                fontWeight: "bold",
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              🔗 即時多人遊戲 (調試模式)
            </span>
          </div>

          <div
            style={{
              backgroundColor: "white",
              padding: "20px",
              borderRadius: "8px",
              marginBottom: "20px",
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
            }}
          >
            <h2>🛠️ WebSocket 遊戲調試信息</h2>
            <p>
              <strong>狀態：</strong>
              {state.gameState.error}
            </p>

            {wsError && (
              <div
                style={{
                  backgroundColor: "#ffebee",
                  padding: "10px",
                  borderRadius: "4px",
                  marginTop: "10px",
                }}
              >
                <strong>錯誤信息：</strong>
                <pre style={{ fontSize: "12px", marginTop: "5px" }}>
                  {JSON.stringify(wsError, null, 2)}
                </pre>
              </div>
            )}

            {wsDebugInfo && (
              <div
                style={{
                  backgroundColor: "#e3f2fd",
                  padding: "10px",
                  borderRadius: "4px",
                  marginTop: "10px",
                }}
              >
                <strong>WebSocket 遊戲信息：</strong>
                <pre
                  style={{
                    fontSize: "12px",
                    marginTop: "5px",
                    maxHeight: "300px",
                    overflow: "auto",
                  }}
                >
                  {JSON.stringify(wsDebugInfo, null, 2)}
                </pre>
              </div>
            )}

            {state.gameState.debug_info && (
              <div
                style={{
                  backgroundColor: "#f3e5f5",
                  padding: "10px",
                  borderRadius: "4px",
                  marginTop: "10px",
                }}
              >
                <strong>遊戲狀態詳情：</strong>
                <pre
                  style={{
                    fontSize: "12px",
                    marginTop: "5px",
                    maxHeight: "300px",
                    overflow: "auto",
                  }}
                >
                  {JSON.stringify(state.gameState.debug_info, null, 2)}
                </pre>
              </div>
            )}
          </div>

          <div
            style={{
              backgroundColor: "white",
              padding: "20px",
              borderRadius: "8px",
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
            }}
          >
            <h3>🔧 故障排除建議</h3>
            <ul>
              <li>
                確保 WebSocket 遊戲引擎正在運行：
                <code>docker compose up -d</code>
              </li>
              <li>
                確保有活躍的遊戲：
                <code>./start_llm_clients.sh --players 3</code>
              </li>
              <li>檢查端口 8100 是否可訪問</li>
              <li>
                回到{" "}
                <button onClick={() => window.history.back()}>遊戲大廳</button>{" "}
                查看狀態
              </li>
            </ul>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "16px",
        }}
      >
        <h1 className="logo">卡坦島</h1>
        {isWebSocketGame && (
          <span
            style={{
              background: "linear-gradient(45deg, #667eea, #764ba2)",
              color: "white",
              padding: "4px 12px",
              borderRadius: "16px",
              fontSize: "12px",
              fontWeight: "bold",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            🔗 即時多人遊戲
          </span>
        )}
      </div>
      <ZoomableBoard replayMode={replayMode} />
      <ActionsToolbar
        isBotThinking={isBotThinking}
        replayMode={replayMode || isWebSocketGame}
      />
      <LeftDrawer />
      <RightDrawer />
    </main>
  );
}

GameScreen.propTypes = {
  /**
   * Injected by the documentation to work in an iframe.
   * You won't need it on your project.
   */
  window: PropTypes.func,
};

export default GameScreen;
