import React, { useCallback, useContext, useState, useEffect } from "react";
import cn from "classnames";
import SwipeableDrawer from "@mui/material/SwipeableDrawer";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";

import Hidden from "./Hidden";
import PlayerStateBox from "./PlayerStateBox";
import PlayerAvatar from "./PlayerAvatar";
import { humanizeAction } from "./Prompt";
import { store } from "../store";
import ACTIONS from "../actions";
import { playerKey } from "../utils/stateUtils";
import { getStoredUser,getLeaderName } from "../utils/authAPI";

import "./LeftDrawer.scss";

function DrawerContent({ gameState }) {
  const [leaderName, setLeaderName] = useState("");
  
  // 獲取隊伍名稱
  useEffect(() => {
    const fetchLeaderName = async () => {
      try {
        const user = getStoredUser();
        if (user && user.group_id) {
          const name = await getLeaderName(user.group_id);
          setLeaderName(name);
        }
      } catch (error) {
        console.error("獲取隊伍名稱失敗:", error);
        setLeaderName("未知隊伍");
      }
    };
    
    fetchLeaderName();
  }, []);

  const playerSections = gameState.colors.map((color) => {
    const key = playerKey(gameState, color);
    return (
      <React.Fragment key={color}>
        <PlayerStateBox
          playerState={gameState.player_state}
          playerKey={key}
          color={color}
        />
        <Divider />
      </React.Fragment>
    );
  });

  return (
    <>
      {playerSections}
      <div className="log">
        {gameState.actions
          .slice()
          .reverse()
          .map((action, i) => {
            const [currentPlayer, text] = humanizeAction(gameState, action);
            return (
              <div key={i} className={cn("action foreground", action[0])}>
                <div className="action-content">
                  <PlayerAvatar color={action[0]} size="small" />
                  <span className={cn("player-name foreground", action[0])}>
                    {/* {leaderName || "載入中..."} */}
                    {currentPlayer}
                  </span>
                  <span className="action-text">
                    {text}
                  </span>
                </div>
              </div>
            );
          })}
      </div>
    </>
  );
}

export default function LeftDrawer() {
  const { state, dispatch } = useContext(store);
  const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent);

  const openLeftDrawer = useCallback(
    (event) => {
      if (
        event &&
        event.type === "keydown" &&
        (event.key === "Tab" || event.key === "Shift")
      ) {
        return;
      }

      dispatch({ type: ACTIONS.SET_LEFT_DRAWER_OPENED, data: true });
    },
    [dispatch]
  );
  const closeLeftDrawer = useCallback(
    (event) => {
      if (
        event &&
        event.type === "keydown" &&
        (event.key === "Tab" || event.key === "Shift")
      ) {
        return;
      }

      dispatch({ type: ACTIONS.SET_LEFT_DRAWER_OPENED, data: false });
    },
    [dispatch]
  );

  return (
    <>
      <Hidden breakpoint={{ size: "md", direction: "up" }} implementation="js">
        <SwipeableDrawer
          className="left-drawer"
          anchor="left"
          open={state.isLeftDrawerOpen}
          onClose={closeLeftDrawer}
          onOpen={openLeftDrawer}
          disableBackdropTransition={!iOS}
          disableDiscovery={iOS}
          onKeyDown={closeLeftDrawer}
        >
          <DrawerContent gameState={state.gameState} />
        </SwipeableDrawer>
      </Hidden>
      <Hidden breakpoint={{size: "sm", direction: "down" }} implementation="css">
        <Drawer className="left-drawer" anchor="left" variant="permanent" open>
          <DrawerContent gameState={state.gameState} />
        </Drawer>
      </Hidden>
    </>
  );
}
