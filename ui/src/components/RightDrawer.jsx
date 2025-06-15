import { useCallback, useContext, useState } from "react";
import SwipeableDrawer from "@mui/material/SwipeableDrawer";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import { CircularProgress, Button } from "@mui/material";
import AssessmentIcon from "@mui/icons-material/Assessment";
import { getMctsAnalysis } from "../utils/apiClient";
import { useParams } from "react-router";

import Hidden from "./Hidden";
import { store } from "../store";
import ACTIONS from "../actions";

import "./RightDrawer.scss";

function DrawerContent() {
  const { gameId } = useParams();
  const { state } = useContext(store);
  const [mctsResults, setMctsResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyzeClick = async () => {
    if (!gameId || !state.gameState || state.gameState.winning_color) return;

    try {
      setLoading(true);
      setError(null);
      const result = await getMctsAnalysis(gameId);
      if (result.success) {
        setMctsResults(result.probabilities);
      } else {
        setError(result.error || "Analysis failed");
      }
    } catch (err) {
      console.error("MCTS Analysis failed:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  // Analyze

  // 道具卡規則
  const devCardRules = [
    {
      name: "騎士卡 (Knight)",
      desc: "移動強盜，並可偷取一名相鄰玩家的資源。"
    },
    {
      name: "壟斷卡 (Monopoly)",
      desc: "宣告一種資源，所有其他玩家必須交出該資源給你。"
    },
    {
      name: "豐饒之年 (Year of Plenty)",
      desc: "從資源堆獲得任意兩種資源，也可以都選同種資源。"
    },
    {
      name: "道路建設 (Road Building)",
      desc: "免費建造兩條道路。"
    },
    {
      name: "勝利點 (Victory Point)",
      desc: "立即獲得一分，無需公開。"
    }
  ];

  const devBuildsRules = [
    {
      name: "購買發展卡 (Buy Development Card)",
      desc: "移動強盜，並可偷取一名相鄰玩家的資源。",
      cost: "所需資源：1個木材 + 1個磚頭 + 1個羊毛"
    },
    {
      name: "建造城市 (Build City)",
      desc: "將一個村莊升級為城市，獲得額外資源。",
      cost: "所需資源：2個小麥 + 3個礦石"
    },
    {
      name: "建造村莊 (Build Settlement)",
      desc: "在交叉點建造一個村莊，獲得資源。",
      cost: "所需資源：1個木材 + 1個磚頭 + 1個羊毛 + 1個小麥"
    },
    {
      name: "建造道路 (Build Road)",
      desc: "在邊界上建造一條道路，連接兩個交叉點。",
      cost: "所需資源：1個木材 + 1個磚頭"
    }
  ];

  return (
    <div className="analysis-box">
      {/*
      <div className="analysis-header">
        <h3>勝率分析</h3>
        <Button
          variant="contained"
          color="primary"
          onClick={handleAnalyzeClick}
          disabled={loading || state.gameState?.winning_color}
          startIcon={loading ? <CircularProgress size={20} /> : <AssessmentIcon />}
        >
          {loading ? "分析中..." : "分析"}
        </Button>
      </div>*/}

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {mctsResults && !loading && !error && (
        <div className="probability-bars">
          {Object.entries(mctsResults).map(([color, probability]) => (
            <div key={color} className={`probability-row ${color.toLowerCase()}`}>
              <span className="player-color">{color}</span>
              <span className="probability-bar">
                <div
                  className="bar-fill"
                  style={{ width: `${probability}%` }}
                />
              </span>
              <span className="probability-value">{probability}%</span>
            </div>
          ))}
        </div>
      )}
      <Divider />
      <div className="devcard-rules">
        <h3>發展卡規則</h3>
        <ul>
          {devCardRules.map(card => (
            <li key={card.name}>
              <strong>{card.name}：</strong>{card.desc}
            </li>
          ))}
        </ul>
      </div>
      <Divider />
      <div className="devcard-rules">
        <h3>買卡/建造規則</h3>
        <ul>
          {devBuildsRules.map(rule => (
            <li key={rule.name}>
              <strong>{rule.name}：</strong>
              {rule.desc}
              <br />
              {rule.cost}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function RightDrawer() {
  const { state, dispatch } = useContext(store);
  const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent);

  const openRightDrawer = useCallback(
    (event) => {
      if (
        event &&
        event.type === "keydown" &&
        (event.key === "Tab" || event.key === "Shift")
      ) {
        return;
      }

      dispatch({ type: ACTIONS.SET_RIGHT_DRAWER_OPENED, data: true });
    },
    [dispatch]
  );

  const closeRightDrawer = useCallback(
    (event) => {
      if (
        event &&
        event.type === "keydown" &&
        (event.key === "Tab" || event.key === "Shift")
      ) {
        return;
      }

      dispatch({ type: ACTIONS.SET_RIGHT_DRAWER_OPENED, data: false });
    },
    [dispatch]
  );

  return (
    <>
      <Hidden breakpoint={{ size: "lg", direction: "up" }} implementation="js">
        <SwipeableDrawer
          className="right-drawer"
          anchor="right"
          open={state.isRightDrawerOpen}
          onClose={closeRightDrawer}
          onOpen={openRightDrawer}
          disableBackdropTransition={!iOS}
          disableDiscovery={iOS}
          onKeyDown={closeRightDrawer}
        >
          <DrawerContent />
        </SwipeableDrawer>
      </Hidden>
      <Hidden breakpoint={{ size: "md", direction: "down" }} implementation="css">
        <Drawer
          className="right-drawer"
          anchor="right"
          variant="permanent"
          open
        >
          <DrawerContent />
        </Drawer>
      </Hidden>
    </>
  );
}
