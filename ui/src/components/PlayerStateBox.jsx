import React from "react";
import cn from "classnames";

import "./PlayerStateBox.scss";
import { Paper } from "@mui/material";
import PlayerAvatar from "./PlayerAvatar";
import { getStoredUser } from "../utils/authAPI";

export function ResourceCards({ playerState, playerKey }) {
  const amount = (card) => playerState[`${playerKey}_${card}_IN_HAND`];
  return (
    <div className="resource-cards" title="Resource Cards">
      {amount("WOOD") !== 0 && (
        <div className="wood-cards center-text card">
          <Paper>{amount("WOOD")}</Paper>
        </div>
      )}
      {amount("BRICK") !== 0 && (
        <div className="brick-cards center-text card">
          <Paper>{amount("BRICK")}</Paper>
        </div>
      )}
      {amount("SHEEP") !== 0 && (
        <div className="sheep-cards center-text card">
          <Paper>{amount("SHEEP")}</Paper>
        </div>
      )}
      {amount("WHEAT") !== 0 && (
        <div className="wheat-cards center-text card">
          <Paper>{amount("WHEAT")}</Paper>
        </div>
      )}
      {amount("ORE") !== 0 && (
        <div className="ore-cards center-text card">
          <Paper>{amount("ORE")}</Paper>
        </div>
      )}
      <div className="separator"></div>
      {amount("VICTORY_POINT") !== 0 && (
        <div
          className="victory-cards center-text card"
          title={amount("VICTORY_POINT") + " Victory Point Card(s)"}
        >
          <Paper>
            <span>{amount("VICTORY_POINT")}</span>
            <span>VP</span>
          </Paper>
        </div>
      )}
      {amount("KNIGHT") !== 0 && (
        <div
          className="knight-cards center-text card"
          title={amount("KNIGHT") + " Knight Card(s)"}
        >
          <Paper>
            <span>{amount("KNIGHT")}</span>
            <span>KN</span>
          </Paper>
        </div>
      )}
      {amount("MONOPOLY") !== 0 && (
        <div
          className="monopoly-cards center-text card"
          title={amount("MONOPOLY") + " Monopoly Card(s)"}
        >
          <Paper>
            <span>{amount("MONOPOLY")}</span>
            <span>MO</span>
          </Paper>
        </div>
      )}
      {amount("YEAR_OF_PLENTY") !== 0 && (
        <div
          className="year-of-plenty-cards center-text card"
          title={amount("YEAR_OF_PLENTY") + " Year of Plenty Card(s)"}
        >
          <Paper>
            <span>{amount("YEAR_OF_PLENTY")}</span>
            <span>YP</span>
          </Paper>
        </div>
      )}
      {amount("ROAD_BUILDING") !== 0 && (
        <div
          className="road-cards center-text card"
          title={amount("ROAD_BUILDING") + " Road Building Card(s)"}
        >
          <Paper>
            <span>{amount("ROAD_BUILDING")}</span>
            <span>RB</span>
          </Paper>
        </div>
      )}
    </div>
  );
}

const colorClass1 = {
    RED: "第1小隊",
    BLUE: "第2小隊",
    WHITE: "第3小隊",
    ORANGE: "第4小隊",
};
const colorClass2 = {
    RED: "第5小隊",
    BLUE: "第6小隊",
    WHITE: "第7小隊",
    ORANGE: "第8小隊",
};

const colorClass3 = {
    RED: "第8小隊",
    BLUE: "第9小隊",
    WHITE: "第10小隊",
    ORANGE: "第11小隊",
};

const getPlayerConfig = () => {
  const user = getStoredUser();
  if (!user || !user.group_id) {
    return colorClass1; // 預設配置
  }

  switch (user.group_id) {
    case 1:
    case 2:
    case 3:
    case 4:
      return colorClass1;
    case 5:
    case 6:
    case 7:
      return colorClass2;
    case 8:
    case 9:
    case 10:
      return colorClass3;
    default:
      return colorClass1; // 預設配置
  }
}
export default function PlayerStateBox({ playerState, playerKey, color }) {
  const actualVps = playerState[`${playerKey}_ACTUAL_VICTORY_POINTS`];
  const playerConfig = getPlayerConfig();
  
  return (
    <div className={cn("player-state-box foreground", color)}>
      <div className="player-section-header">
        <PlayerAvatar color={color} size="small" />
        <span className="player-title">{playerConfig[color]}</span>
      </div>
      <ResourceCards playerState={playerState} playerKey={playerKey} />
      <div className="scores">
        <div
          className={cn("num-knights center-text", {
            bold: playerState[`${playerKey}_HAS_ARMY`],
          })}
          title="Knights Played"
        >
          <span>{playerState[`${playerKey}_PLAYED_KNIGHT`]}</span>
          <small>騎士</small>
        </div>
        <div
          className={cn("num-roads center-text", {
            bold: playerState[`${playerKey}_HAS_ROAD`],
          })}
          title="Longest Road"
        >
          {playerState[`${playerKey}_LONGEST_ROAD_LENGTH`]}
          <small>道路</small>
        </div>
        <div
          className={cn("victory-points center-text", {
            bold: actualVps >= 10,
          })}
          title="Victory Points"
        >
          {actualVps}
          <small>分數</small>
        </div>
      </div>
    </div>
  );
}
