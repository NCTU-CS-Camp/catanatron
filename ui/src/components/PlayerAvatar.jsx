import React, { useState, useEffect } from "react";
import { getGroupAvatar } from "../utils/authAPI";
import "./PlayerAvatar.scss";

// 全局頭像緩存
const avatarCache = {
  urls: {}, // { groupId: url }
  loading: false,
  loaded: false,
  error: false
};

// 一次性獲取所有群組頭像的函數
const loadAllGroupAvatars = async () => {
  if (avatarCache.loading || avatarCache.loaded) {
    return;
  }

  avatarCache.loading = true;
  avatarCache.error = false;

  try {
    // 並行獲取所有群組頭像
    const promises = [1, 2, 3, 4].map(async (groupId) => {
      try {
        const url = await getGroupAvatar(groupId);
        return { groupId, url, success: true };
      } catch (error) {
        console.error(`獲取群組 ${groupId} 頭像失敗:`, error);
        return { groupId, url: null, success: false };
      }
    });

    const results = await Promise.all(promises);
    
    // 將結果存入緩存
    results.forEach(({ groupId, url }) => {
      if (url) {
        avatarCache.urls[groupId] = url;
      }
    });

    avatarCache.loaded = true;
    console.log('所有群組頭像載入完成:', avatarCache.urls);
    
  } catch (error) {
    console.error('載入群組頭像時發生錯誤:', error);
    avatarCache.error = true;
  } finally {
    avatarCache.loading = false;
  }
};

// 玩家頭像組件
export default function PlayerAvatar({ 
  color, 
  size = "small", 
  showName = false,
  fallbackToColor = true // 是否在獲取頭像失敗時使用顏色圖標
}) {
  const [avatarUrl, setAvatarUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  // 玩家顏色對應的頭像配置（作為備用）
  const avatarConfig = {
    RED: {
      name: "玩家1",
      groupId: 1,
      icon: "🔴",
      bgColor: "#d32f2f",
      textColor: "#fff"
    },
    BLUE: {
      name: "玩家2", 
      groupId: 2,
      icon: "🔵",
      bgColor: "#1976d2",
      textColor: "#fff"
    },
    ORANGE: {
      name: "玩家3",
      groupId: 3,
      icon: "🟠", 
      bgColor: "#f57c00",
      textColor: "#fff"
    },
    WHITE: {
      name: "玩家4",
      groupId: 4,
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

  // 監聽緩存變化和載入頭像
  useEffect(() => {
    const groupId = config.groupId;
    
    if (!groupId) {
      return;
    }

    // 如果緩存中已有此群組的頭像，直接使用
    if (avatarCache.urls[groupId]) {
      setAvatarUrl(avatarCache.urls[groupId]);
      setError(false);
      return;
    }

    // 如果尚未開始載入，開始載入所有頭像
    if (!avatarCache.loaded && !avatarCache.loading) {
      setLoading(true);
      loadAllGroupAvatars().then(() => {
        // 載入完成後，檢查是否有此群組的頭像
        if (avatarCache.urls[groupId]) {
          setAvatarUrl(avatarCache.urls[groupId]);
          setError(false);
        } else {
          setError(true);
        }
        setLoading(false);
      });
    }
    // 如果正在載入，等待載入完成
    else if (avatarCache.loading) {
      setLoading(true);
      
      // 輪詢檢查載入狀態
      const checkLoadingStatus = () => {
        if (!avatarCache.loading) {
          if (avatarCache.urls[groupId]) {
            setAvatarUrl(avatarCache.urls[groupId]);
            setError(false);
          } else {
            setError(true);
          }
          setLoading(false);
        } else {
          setTimeout(checkLoadingStatus, 100);
        }
      };
      
      setTimeout(checkLoadingStatus, 100);
    }
    // 如果已載入完成但沒有此群組的頭像
    else if (avatarCache.loaded && !avatarCache.urls[groupId]) {
      setError(true);
    }
  }, [color, config.groupId]);

  // 渲染頭像內容
  const renderAvatarContent = () => {
    // 如果正在載入
    if (loading) {
      return (
        <span className="avatar-loading">⏳</span>
      );
    }

    // 如果有頭像 URL 且沒有錯誤
    if (avatarUrl && !error) {
      return (
        <img 
          src={avatarUrl} 
          alt={config.name}
          className="avatar-image"
          onError={() => setError(true)} // 圖片載入失敗時的處理
        />
      );
    }

    // 如果獲取頭像失敗且允許使用顏色圖標作為備用
    if (fallbackToColor) {
      return (
        <span className="avatar-icon">{config.icon}</span>
      );
    }

    // 完全失敗的情況
    return (
      <span className="avatar-icon">❌</span>
    );
  };

  return (
    <div className={`player-avatar-container ${size}`}>
      <div 
        className={`player-avatar ${color.toLowerCase()} ${avatarUrl && !error ? 'has-image' : ''}`}
        style={!avatarUrl || error ? { 
          backgroundColor: config.bgColor,
          color: config.textColor 
        } : {}}
        title={config.name}
      >
        {renderAvatarContent()}
      </div>
      {showName && (
        <span className="player-name">{config.name}</span>
      )}
    </div>
  );
}

// 可選：導出手動清除緩存的函數（用於開發調試）
export const clearAvatarCache = () => {
  avatarCache.urls = {};
  avatarCache.loading = false;
  avatarCache.loaded = false;
  avatarCache.error = false;
};
