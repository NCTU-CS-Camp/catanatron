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
  Divider,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  PlayArrow as PlayIcon,
  Visibility as WatchIcon,
  Home as HomeIcon,
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
  const navigate = useNavigate();

  const fetchAllData = async () => {
    try {
      const [gamesData, wsGame, wsStatus] = await Promise.allSettled([
        getGamesList(),
        getCurrentWebSocketGame(),
        checkWebSocketEngineStatus(),
      ]);

      if (gamesData.status === "fulfilled") {
        setGames(gamesData.value.games || []);
      }

      if (wsGame.status === "fulfilled") {
        setCurrentWebSocketGame(wsGame.value);

        // 如果有當前遊戲，獲取詳細信息
        if (wsGame.value && !wsGame.value.error) {
          try {
            const detailed = await getDetailedWebSocketGame();
            setDetailedGame(detailed);
          } catch (error) {
            console.error("Failed to get detailed game info:", error);
          }
        }
      }

      if (wsStatus.status === "fulfilled") {
        setWebsocketStatus(wsStatus.value);
      }
    } catch (error) {
      console.error("Failed to fetch lobby data:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAllData();

    // 每 5 秒自動刷新一次
    const interval = setInterval(fetchAllData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchAllData();
  };

  const handleJoinWebSocketGame = () => {
    if (currentWebSocketGame && !currentWebSocketGame.error) {
      navigate("/games/websocket/websocket_multiplayer_game");
    }
  };

  const getPlayerColorDisplay = (color) => {
    const colorMap = {
      RED: "紅色",
      BLUE: "藍色",
      WHITE: "白色",
      ORANGE: "橙色",
    };
    return colorMap[color] || color;
  };

  const getGameStatusChip = (game) => {
    // 處理 WebSocket 遊戲狀態
    if (game.type === "websocket_multiplayer" && game.status) {
      if (game.status.status === "active") {
        return <Chip label="進行中" color="success" size="small" />;
      } else if (game.status.status === "finished") {
        return <Chip label="已結束" color="default" size="small" />;
      }
    }

    // 處理一般遊戲狀態
    if (game.status === "IN_PROGRESS" || game.status === "active") {
      return <Chip label="進行中" color="success" size="small" />;
    } else if (game.status === "FINISHED" || game.status === "finished") {
      return <Chip label="已結束" color="default" size="small" />;
    } else {
      return <Chip label="等待中" color="warning" size="small" />;
    }
  };

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="60vh"
      >
        <CircularProgress />
        <Typography variant="h6" sx={{ ml: 2 }}>
          載入遊戲大廳...
        </Typography>
      </Box>
    );
  }

  return (
    <div className="lobby-container">
      <Box sx={{ p: 3 }}>
        {/* 標題和控制項 */}
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={3}
        >
          <Typography variant="h4" component="h1">
            🎮 遊戲大廳
          </Typography>
          <Box>
            <Tooltip title="返回主頁">
              <IconButton onClick={() => navigate("/")} color="primary">
                <HomeIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="刷新">
              <IconButton onClick={handleRefresh} disabled={refreshing}>
                <RefreshIcon className={refreshing ? "rotating" : ""} />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* WebSocket 引擎狀態 */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🔗 WebSocket 遊戲引擎狀態
            </Typography>
            {websocketStatus ? (
              <Alert severity="success">
                引擎運行中 - 端口 8100
                {websocketStatus.summary && (
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    {websocketStatus.summary}
                  </Typography>
                )}
              </Alert>
            ) : (
              <Alert severity="error">
                WebSocket 遊戲引擎離線。請啟動：
                <code>docker compose up -d</code>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* 當前 WebSocket 遊戲 */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🎯 當前 WebSocket 遊戲
            </Typography>

            {currentWebSocketGame && !currentWebSocketGame.error ? (
              <Box>
                {getGameStatusChip("IN_PROGRESS")}
                <Typography variant="body1" sx={{ mt: 2 }}>
                  有活躍的多人遊戲正在進行中
                </Typography>

                {detailedGame && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      遊戲詳情：
                    </Typography>
                    <div className="game-details">
                      <pre>{JSON.stringify(detailedGame, null, 2)}</pre>
                    </div>
                  </Box>
                )}

                <Box sx={{ mt: 2 }}>
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<WatchIcon />}
                    onClick={handleJoinWebSocketGame}
                    sx={{ mr: 1 }}
                  >
                    觀看遊戲
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<PlayIcon />}
                    onClick={handleJoinWebSocketGame}
                  >
                    加入遊戲
                  </Button>
                </Box>
              </Box>
            ) : (
              <Box>
                <Alert severity="info">目前沒有活躍的 WebSocket 遊戲</Alert>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  你可以啟動 LLM 客戶端來創建新遊戲：
                </Typography>
                <Typography
                  variant="body2"
                  component="code"
                  sx={{
                    mt: 1,
                    display: "block",
                    background: "#f5f5f5",
                    p: 1,
                    borderRadius: 1,
                  }}
                >
                  ./start_llm_clients.sh --players 3
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>

        {/* 遊戲列表 */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              📋 所有遊戲列表
            </Typography>

            {games.length > 0 ? (
              <div className="games-grid-container">
                <Grid container spacing={2}>
                  {games.map((game, index) => (
                    <Grid item xs={12} md={6} lg={4} key={index}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="h6">
                            遊戲 #{index + 1}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            遊戲 ID: {game.game_id || "未知"}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            類型:{" "}
                            {game.type === "websocket_multiplayer"
                              ? "WebSocket 多人遊戲"
                              : "Flask 單人遊戲"}
                          </Typography>
                          <Box sx={{ mt: 1 }}>{getGameStatusChip(game)}</Box>

                          {/* WebSocket 遊戲詳細信息 */}
                          {game.type === "websocket_multiplayer" &&
                            game.status && (
                              <Box sx={{ mt: 1 }}>
                                <Typography variant="body2">
                                  連接玩家: {game.status.connected_players}/3
                                </Typography>
                                <Typography variant="body2">
                                  當前玩家: {game.status.current_player}
                                </Typography>
                                <Typography variant="body2">
                                  回合: {game.status.turn_number}
                                </Typography>
                              </Box>
                            )}

                          {/* 一般遊戲玩家信息 */}
                          {game.players && (
                            <Box sx={{ mt: 1 }}>
                              <Typography variant="body2">
                                玩家: {game.players.join(", ")}
                              </Typography>
                            </Box>
                          )}
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => {
                              if (game.type === "websocket_multiplayer") {
                                // WebSocket 遊戲使用特殊路由
                                navigate(`/games/websocket/${game.game_id}`);
                              } else {
                                // 一般遊戲
                                navigate(`/games/${game.game_id}`);
                              }
                            }}
                            sx={{ mt: 1 }}
                            disabled={!game.game_id}
                          >
                            {game.type === "websocket_multiplayer"
                              ? "觀看 WebSocket 遊戲"
                              : "查看遊戲"}
                          </Button>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </div>
            ) : (
              <Alert severity="info">目前沒有遊戲記錄</Alert>
            )}
          </CardContent>
        </Card>

        {/* 使用說明 */}
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              💡 使用說明
            </Typography>
            <Typography variant="body2" paragraph>
              1. <strong>WebSocket 遊戲</strong>：即時多人對戰遊戲，使用
              WebSocket 技術
            </Typography>
            <Typography variant="body2" paragraph>
              2. <strong>啟動遊戲</strong>：運行{" "}
              <code>./start_llm_clients.sh --players 3</code> 來創建新的多人遊戲
            </Typography>
            <Typography variant="body2" paragraph>
              3. <strong>觀看遊戲</strong>
              ：點擊「觀看遊戲」來實時觀看正在進行的遊戲
            </Typography>
            <Typography variant="body2">
              4. <strong>自動刷新</strong>：頁面每 5
              秒自動刷新一次，顯示最新狀態
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </div>
  );
}
