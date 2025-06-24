import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Container,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  Visibility as WatchIcon,
  Home as HomeIcon,
  SportsEsports as GameIcon,
  Circle as CircleIcon,
} from "@mui/icons-material";
import {
  getGamesList,
  getCurrentWebSocketGame,
  getDetailedWebSocketGame,
  checkWebSocketEngineStatus,
} from "../utils/apiClient";

import "./Lobby.scss";

export default function Lobby() {
  const [games, setGames] = useState([]);
  const [currentWebSocketGame, setCurrentWebSocketGame] = useState(null);
  const [detailedGame, setDetailedGame] = useState(null);
  const [websocketStatus, setWebsocketStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const navigate = useNavigate();

  const fetchAllData = async () => {
    try {
      setError(null);

      // 並行獲取所有數據
      const [gamesResult, wsGameResult, wsStatusResult] =
        await Promise.allSettled([
          getGamesList(),
          getCurrentWebSocketGame(),
          checkWebSocketEngineStatus(),
        ]);

      // 處理遊戲列表
      if (gamesResult.status === "fulfilled") {
        setGames(gamesResult.value.games || []);
      } else {
        console.error("Failed to fetch games:", gamesResult.reason);
      }

      // 處理當前 WebSocket 遊戲
      if (wsGameResult.status === "fulfilled") {
        setCurrentWebSocketGame(wsGameResult.value);

        // 如果有當前遊戲且不是錯誤，獲取詳細信息
        if (
          wsGameResult.value &&
          !wsGameResult.value.error &&
          wsGameResult.value.status !== "no_active_game"
        ) {
          try {
            const detailed = await getDetailedWebSocketGame();
            setDetailedGame(detailed);
          } catch (error) {
            console.error("Failed to get detailed game info:", error);
          }
        }
      } else {
        console.error("Failed to fetch WebSocket game:", wsGameResult.reason);
      }

      // 處理 WebSocket 狀態
      if (wsStatusResult.status === "fulfilled") {
        setWebsocketStatus(wsStatusResult.value);
      } else {
        console.error(
          "Failed to fetch WebSocket status:",
          wsStatusResult.reason
        );
      }

      setLastUpdated(new Date());
    } catch (error) {
      console.error("Failed to fetch lobby data:", error);
      setError("無法載入遊戲數據，請檢查伺服器連接");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAllData();

    // 每 1 秒自動刷新一次
    const interval = setInterval(fetchAllData, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchAllData();
  };

  const handleJoinWebSocketGame = () => {
    navigate("/games/websocket/websocket_multiplayer_game");
  };

  const getPlayerColorDisplay = (color) => {
    const colorMap = {
      RED: "RED Player",
      BLUE: "BLUE Player",
      WHITE: "WHITE Player",
      ORANGE: "ORANGE Player",
    };
    return colorMap[color] || `${color} Player`;
  };

  const getPlayerIcon = (color) => {
    const colorStyle = {
      RED: "#f44336",
      BLUE: "#2196f3",
      WHITE: "#9e9e9e",
      ORANGE: "#ff9800",
    };
    return colorStyle[color] || "#000";
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString("en-US", {
      hour12: true,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const getConnectedPlayersCount = () => {
    if (!websocketStatus?.player_connections) return 0;
    return Object.values(websocketStatus.player_connections).filter(
      (p) => p.connected
    ).length;
  };

  const getTotalPlayersNeeded = () => {
    return websocketStatus?.websocket_game_engine?.max_players || 4;
  };

  const getMinPlayersNeeded = () => {
    return websocketStatus?.websocket_game_engine?.min_players || 3;
  };

  const getCountdownRemaining = () => {
    return websocketStatus?.game_status?.countdown_remaining;
  };

  if (loading) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          background:
            "linear-gradient(135deg, #4fc3f7 0%, #29b6f6 50%, #03a9f4 100%)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Box sx={{ textAlign: "center", color: "white" }}>
          <CircularProgress sx={{ color: "white", mb: 2 }} size={60} />
          <Typography variant="h6">載入遊戲大廳...</Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background:
          "linear-gradient(135deg, #4fc3f7 0%, #29b6f6 50%, #03a9f4 100%)",
        position: "relative",
        overflow: "auto",
        "&::before": {
          content: '""',
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: `
            radial-gradient(circle at 20% 30%, rgba(255,255,255,0.1) 1px, transparent 1px),
            radial-gradient(circle at 80% 70%, rgba(255,255,255,0.1) 1px, transparent 1px),
            radial-gradient(circle at 60% 20%, rgba(255,255,255,0.05) 2px, transparent 2px)
          `,
          backgroundSize: "100px 100px, 150px 150px, 200px 200px",
          animation: "float 6s ease-in-out infinite",
          pointerEvents: "none",
        },
      }}
    >
      <Container maxWidth="lg" sx={{ position: "relative", zIndex: 1 }}>
        <Box sx={{ py: 4 }}>
          {/* 標題區域 */}
          <Box sx={{ textAlign: "center", mb: 4 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                mb: 2,
              }}
            >
              <GameIcon sx={{ fontSize: 40, color: "#333", mr: 2 }} />
              <Typography
                variant="h3"
                component="h1"
                sx={{
                  color: "#333",
                  fontWeight: "bold",
                  textShadow: "2px 2px 4px rgba(0,0,0,0.1)",
                }}
              >
                Catanatron Game Lobby
              </Typography>
            </Box>

            <Box
              sx={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                gap: 3,
              }}
            >
              <Typography
                variant="h5"
                sx={{
                  color: websocketStatus ? "#2e7d32" : "#d32f2f",
                  fontWeight: "bold",
                }}
              >
                {websocketStatus
                  ? `${getConnectedPlayersCount()}/${getTotalPlayersNeeded()} Players Connected`
                  : "API 連接中..."}
              </Typography>
              <Typography variant="body1" sx={{ color: "#555" }}>
                Last updated: {formatTime(lastUpdated)}
              </Typography>
              <IconButton
                onClick={handleRefresh}
                disabled={refreshing}
                sx={{
                  color: "#333",
                  "&:hover": { backgroundColor: "rgba(255,255,255,0.2)" },
                }}
              >
                <RefreshIcon className={refreshing ? "rotating" : ""} />
              </IconButton>
            </Box>
          </Box>

          {/* 錯誤提示 */}
          {error && (
            <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
              {error}
            </Alert>
          )}

          {/* 玩家狀態卡片 */}
          {websocketStatus && (
            <Grid container spacing={3} sx={{ mb: 4 }}>
              {websocketStatus?.port_assignments &&
                Object.entries(websocketStatus.port_assignments).map(
                  ([port, playerInfo]) => {
                    const isConnected =
                      websocketStatus.player_connections[playerInfo.color]
                        ?.connected || false;
                    const connectionTime =
                      websocketStatus.player_connections[playerInfo.color]
                        ?.connected_at;
                    const ipAddress =
                      websocketStatus.player_connections[playerInfo.color]
                        ?.client_info?.remote_ip || "192.168.65.1";

                    return (
                      <Grid item xs={12} sm={6} md={3} key={port}>
                        <Card
                          sx={{
                            borderRadius: 3,
                            border: isConnected
                              ? "2px solid transparent"
                              : "2px solid #f44336",
                            backgroundColor: isConnected
                              ? "rgba(255,255,255,0.95)"
                              : "rgba(255,235,238,0.95)",
                            backdropFilter: "blur(10px)",
                            transition: "all 0.3s ease",
                            "&:hover": {
                              transform: "translateY(-2px)",
                              boxShadow: "0 8px 25px rgba(0,0,0,0.15)",
                            },
                          }}
                        >
                          <CardContent sx={{ p: 3 }}>
                            <Box
                              sx={{
                                display: "flex",
                                alignItems: "center",
                                mb: 2,
                              }}
                            >
                              <Box
                                sx={{
                                  width: 24,
                                  height: 60,
                                  backgroundColor: getPlayerIcon(
                                    playerInfo.color
                                  ),
                                  borderRadius: 2,
                                  mr: 2,
                                }}
                              />
                              <Box>
                                <Typography
                                  variant="h6"
                                  sx={{ fontWeight: "bold", color: "#333" }}
                                >
                                  {getPlayerColorDisplay(playerInfo.color)}
                                </Typography>
                                <Box
                                  sx={{
                                    display: "flex",
                                    alignItems: "center",
                                    mt: 0.5,
                                  }}
                                >
                                  <CircleIcon
                                    sx={{
                                      fontSize: 12,
                                      color: isConnected
                                        ? "#4caf50"
                                        : "#f44336",
                                      mr: 0.5,
                                    }}
                                  />
                                  <Typography
                                    variant="body2"
                                    sx={{
                                      color: isConnected
                                        ? "#4caf50"
                                        : "#f44336",
                                      fontWeight: "bold",
                                    }}
                                  >
                                    {isConnected ? "Connected" : "Offline"}
                                  </Typography>
                                </Box>
                              </Box>
                            </Box>

                            <Box sx={{ color: "#666", fontSize: "0.875rem" }}>
                              <Typography variant="body2">
                                Port: {port}
                              </Typography>
                              <Typography variant="body2">
                                IP: {ipAddress}
                              </Typography>
                              {isConnected && connectionTime && (
                                <Typography variant="body2">
                                  Connected:{" "}
                                  {new Date(connectionTime).toLocaleTimeString(
                                    "en-US",
                                    {
                                      hour12: true,
                                      hour: "2-digit",
                                      minute: "2-digit",
                                      second: "2-digit",
                                    }
                                  )}
                                </Typography>
                              )}
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    );
                  }
                )}
            </Grid>
          )}

          {/* 遊戲狀態區域 */}
          <Card
            sx={{
              borderRadius: 3,
              backgroundColor: "rgba(255,255,255,0.95)",
              backdropFilter: "blur(10px)",
              mb: 3,
            }}
          >
            <CardContent sx={{ p: 4 }}>
              <Typography
                variant="h5"
                sx={{ fontWeight: "bold", color: "#333", mb: 3 }}
              >
                Game Status
              </Typography>

              {websocketStatus?.game_status?.game_started ? (
                <Box
                  sx={{
                    p: 3,
                    backgroundColor: "#e8f5e8",
                    borderRadius: 2,
                    border: "2px solid #4caf50",
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                    <Box
                      sx={{
                        width: 20,
                        height: 20,
                        backgroundColor: "#4caf50",
                        borderRadius: 1,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        mr: 2,
                      }}
                    >
                      <Typography
                        sx={{
                          color: "white",
                          fontSize: "14px",
                          fontWeight: "bold",
                        }}
                      >
                        ✓
                      </Typography>
                    </Box>
                    <Typography
                      variant="h6"
                      sx={{ color: "#2e7d32", fontWeight: "bold" }}
                    >
                      遊戲進行中！
                    </Typography>
                  </Box>

                  <Button
                    variant="contained"
                    size="large"
                    startIcon={<WatchIcon />}
                    onClick={handleJoinWebSocketGame}
                    sx={{
                      backgroundColor: "#1976d2",
                      "&:hover": { backgroundColor: "#1565c0" },
                      borderRadius: 2,
                      px: 4,
                      py: 1.5,
                    }}
                  >
                    觀看遊戲
                  </Button>
                </Box>
              ) : websocketStatus &&
                getConnectedPlayersCount() >= getMinPlayersNeeded() ? (
                <Box
                  sx={{
                    p: 3,
                    backgroundColor: "#fff3e0",
                    borderRadius: 2,
                    border: "2px solid #ff9800",
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                    <Box
                      sx={{
                        width: 20,
                        height: 20,
                        backgroundColor: "#ff9800",
                        borderRadius: 1,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        mr: 2,
                      }}
                    >
                      <Typography
                        sx={{
                          color: "white",
                          fontSize: "14px",
                          fontWeight: "bold",
                        }}
                      >
                        ⏳
                      </Typography>
                    </Box>
                    <Typography
                      variant="h6"
                      sx={{ color: "#f57c00", fontWeight: "bold" }}
                    >
                      {getConnectedPlayersCount() >= getTotalPlayersNeeded()
                        ? "準備就緒！等待遊戲開始..."
                        : `遊戲將在 ${getCountdownRemaining() || 0} 秒後開始`}
                    </Typography>
                  </Box>
                  <Typography variant="body1" sx={{ color: "#555" }}>
                    {getConnectedPlayersCount() >= getTotalPlayersNeeded()
                      ? "所有玩家已連接，遊戲即將自動開始"
                      : `已達到最少玩家數 (${getConnectedPlayersCount()}/${getMinPlayersNeeded()})，等待更多玩家加入或倒數結束`}
                  </Typography>
                </Box>
              ) : websocketStatus ? (
                <Box
                  sx={{
                    p: 3,
                    backgroundColor: "rgba(33, 150, 243, 0.1)",
                    borderRadius: 2,
                    border: "2px solid #2196f3",
                  }}
                >
                  <Typography
                    variant="h6"
                    sx={{ color: "#1976d2", fontWeight: "bold" }}
                  >
                    等待玩家加入... ({getConnectedPlayersCount()}/
                    {getTotalPlayersNeeded()} 已連接)
                  </Typography>
                  <Typography variant="body1" sx={{ color: "#555", mt: 1 }}>
                    需要至少 {getMinPlayersNeeded()} 名玩家才能開始遊戲
                  </Typography>
                </Box>
              ) : (
                <Box
                  sx={{
                    p: 3,
                    backgroundColor: "rgba(244, 67, 54, 0.1)",
                    borderRadius: 2,
                    border: "2px solid #f44336",
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                    <Box
                      sx={{
                        width: 20,
                        height: 20,
                        backgroundColor: "#f44336",
                        borderRadius: 1,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        mr: 2,
                      }}
                    >
                      <Typography
                        sx={{
                          color: "white",
                          fontSize: "14px",
                          fontWeight: "bold",
                        }}
                      >
                        ⚠
                      </Typography>
                    </Box>
                    <Typography
                      variant="h6"
                      sx={{ color: "#d32f2f", fontWeight: "bold" }}
                    >
                      等待 API 連接...
                    </Typography>
                  </Box>
                  <Typography variant="body1" sx={{ color: "#555" }}>
                    正在嘗試連接遊戲伺服器，請稍候或檢查伺服器狀態
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>

          {/* 返回主頁按鈕 */}
          <Box sx={{ position: "fixed", top: 20, left: 20 }}>
            <IconButton
              onClick={() => navigate("/")}
              sx={{
                backgroundColor: "rgba(255,255,255,0.9)",
                color: "#333",
                "&:hover": { backgroundColor: "rgba(255,255,255,1)" },
              }}
            >
              <HomeIcon />
            </IconButton>
          </Box>
        </Box>
      </Container>

      <style jsx>{`
        @keyframes float {
          0%,
          100% {
            transform: translateY(0px) rotate(0deg);
          }
          33% {
            transform: translateY(-10px) rotate(1deg);
          }
          66% {
            transform: translateY(-5px) rotate(-1deg);
          }
        }
        .rotating {
          animation: rotate 1s linear infinite;
        }
        @keyframes rotate {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </Box>
  );
}
