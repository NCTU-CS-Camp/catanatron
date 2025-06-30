import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Container, Typography, Box, Fade, Grow } from "@mui/material";
import { GridLoader } from "react-spinners";
import { createGame } from "../utils/apiClient";
import { SportsEsports } from "@mui/icons-material";

import "./HomePage.scss";

// Enum of Type of Game Mode
const GameMode = Object.freeze({
  HUMAN_VS_CATANATRON: "HUMAN_VS_CATANATRON",
  RANDOM_BOTS: "RANDOM_BOTS",
  CATANATRON_BOTS: "CATANATRON_BOTS",
});

function getPlayers(gameMode, numPlayers) {
  switch (gameMode) {
    case GameMode.HUMAN_VS_CATANATRON:
      const players = ["HUMAN"];
      for (let i = 1; i < numPlayers; i++) {
        players.push("CATANATRON");
      }
      return players;
    case GameMode.RANDOM_BOTS:
      return Array(numPlayers).fill("RANDOM");
    case GameMode.CATANATRON_BOTS:
      return Array(numPlayers).fill("CATANATRON");
    default:
      throw new Error("Invalid Game Mode");
  }
}

export default function HomePage() {
  const [loading, setLoading] = useState(false);
  const [numPlayers, setNumPlayers] = useState(2);
  const navigate = useNavigate();

  const handleCreateGame = async (gameMode) => {
    setLoading(true);
    const players = getPlayers(gameMode, numPlayers);
    const gameId = await createGame(players);
    setLoading(false);
    navigate("/games/" + gameId);
  };

  return (
    <div className="home-page">
      {/* 海底世界背景 */}
      <div className="underwater-background">
        <div className="water-surface"></div>
        
        {/* 輕微的泡泡效果 */}
        <div className="bubble bubble-1"></div>
        <div className="bubble bubble-2"></div>
        <div className="bubble bubble-3"></div>
      </div>

      <Container maxWidth="lg" className="home-container">
        <Fade in={true} timeout={1000}>
          <div className="home-header">
            <div className="game-icon-container">
              <SportsEsports className="main-game-icon" />
            </div>
            <Typography variant="h1" component="h1" className="main-title">
              CS Camp Catan
            </Typography>
            <Typography variant="h5" component="h2" className="sub-title">
              使用LLM來玩卡坦島吧！
            </Typography>
          </div>
        </Fade>

        <Grow in={true} timeout={1200}>
          <div className="action-container">
            {!loading ? (
              <div className="button-group">
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => navigate("/login")}
                  className="enter-game-button"
                  fullWidth
                >
                  進入遊戲
                </Button>
              </div>
            ) : (
              <div className="loading-section">
                <GridLoader
                  color="#2196f3"
                  size={15}
                  margin={5}
                  speedMultiplier={0.8}
                />
                <Typography variant="h6" className="loading-text">
                  正在準備遊戲...
                </Typography>
              </div>
            )}
          </div>
        </Grow>
      </Container>
    </div>
  );
}
