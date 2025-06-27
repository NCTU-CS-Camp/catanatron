import React from "react";
import "./PlayerAvatar.scss";

// 玩家頭像組件
export default function PlayerAvatar({ color, size = "small", showName = false }) {
  // 玩家顏色對應的頭像配置
  const avatarConfig = {
    RED: {
      name: "玩家1",
      icon: "🔴",
      bgColor: "#d32f2f",
      textColor: "#fff"
    },
    BLUE: {
      name: "玩家2", 
      icon: "🔵",
      bgColor: "#1976d2",
      textColor: "#fff"
    },
    ORANGE: {
      name: "玩家3",
      icon: "🟠", 
      bgColor: "#f57c00",
      textColor: "#fff"
    },
    WHITE: {
      name: "玩家4",
      icon: "⚪",
      bgColor: "#616161",
      textColor: "#fff"
    }
  };

  const config = avatarConfig[color] || {
    name: color,
    icon: "⚫",
    bgColor: "#9e9e9e",
    textColor: "#fff"
  };

  return (
    <div className={`player-avatar-container ${size}`}>
      <div 
        className={`player-avatar ${color.toLowerCase()}`}
        style={{ 
          backgroundColor: config.bgColor,
          color: config.textColor 
        }}
        title={config.name}
      >
        <span className="avatar-icon">{config.icon}</span>
      </div>
      {showName && (
        <span className="player-name">{config.name}</span>
      )}
    </div>
  );
}
