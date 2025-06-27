import { useCallback, useContext, useState, useEffect } from "react";
import SwipeableDrawer from "@mui/material/SwipeableDrawer";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import { 
  CircularProgress, 
  TextField, 
  IconButton,
  Typography
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import { useParams } from "react-router";

import Hidden from "./Hidden";
import { store } from "../store";
import ACTIONS from "../actions";

import "./RightDrawer.scss";

// 獲取存儲的 token
const getAuthToken = () => {
  return localStorage.getItem('access_token');
};

// API 基礎配置
const API_BASE_URL = ''; // 如果需要的話，設置你的 API 基礎 URL

// 創建帶認證的 fetch 函數
const authFetch = async (url, options = {}) => {
  const token = getAuthToken();
  
  if (!token) {
    throw new Error('未登入');
  }

  const config = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(`${API_BASE_URL}${url}`, config);
  
  if (response.status === 401) {
    // Token 可能過期，清除本地存儲
    localStorage.removeItem('access_token');
    localStorage.removeItem('currentUser');
    throw new Error('登入已過期，請重新登入');
  }
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  
  return response.json();
};

// 根據實際 API 規範的函數
const getGroupSummary = async (groupId) => {
  try {
    const data = await authFetch(`/groups/${groupId}/summary`);
    return {
      success: true,
      summary: data.summary_prompt || "暫無摘要"
    };
  } catch (error) {
    console.error('獲取群組摘要失敗:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

const getGroupPrompts = async (groupId) => {
  try {
    const prompts = await authFetch(`/prompts/group/${groupId}`);
    return {
      success: true,
      prompts: prompts.map(prompt => ({
        userId: prompt.user_id,
        content: prompt.data,
        updatedAt: prompt.timestamp,
        id: prompt.id
      }))
    };
  } catch (error) {
    console.error('獲取群組 prompts 失敗:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

const createPrompt = async (promptData) => {
  try {
    const data = await authFetch('/prompts/', {
      method: 'POST',
      body: JSON.stringify({
        data: promptData
      })
    });
    return {
      success: true,
      data: {
        userId: data.user_id,
        content: data.data,
        updatedAt: data.timestamp,
        id: data.id
      }
    };
  } catch (error) {
    console.error('創建 prompt 失敗:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

// 獲取當前用戶資訊
const getCurrentUser = async () => {
  try {
    const user = await authFetch('/users/me/');
    return {
      success: true,
      user: {
        id: user.id,
        username: user.username,
        groupId: user.group_id
      }
    };
  } catch (error) {
    console.error('獲取用戶資訊失敗:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

function DrawerContent() {
  const { groupId } = useParams(); // 從 URL 獲取 groupId 而不是 gameId
  const { state } = useContext(store);
  
  // 狀態管理
  const [promptSummary, setPromptSummary] = useState("");
  const [promptsByUser, setPromptsByUser] = useState({}); // {userId: {content, updatedAt}}
  const [currentUser, setCurrentUser] = useState(null);
  const [newPrompt, setNewPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [sendingPrompt, setSendingPrompt] = useState(false);
  const [error, setError] = useState(null);

  // 載入當前用戶資訊
  useEffect(() => {
    const loadCurrentUser = async () => {
      // 先嘗試從 localStorage 獲取
      const savedUser = localStorage.getItem('currentUser');
      if (savedUser) {
        try {
          setCurrentUser(JSON.parse(savedUser));
          return;
        } catch (e) {
          // localStorage 數據損壞，清除並重新獲取
          localStorage.removeItem('currentUser');
        }
      }

      // 從 API 獲取用戶資訊
      const result = await getCurrentUser();
      if (result.success) {
        setCurrentUser(result.user);
        localStorage.setItem('currentUser', JSON.stringify(result.user));
      } else {
        console.error('無法獲取用戶資訊:', result.error);
        setError('無法獲取用戶資訊');
      }
    };

    if (getAuthToken()) {
      loadCurrentUser();
    }
  }, []);

  // 載入數據
  useEffect(() => {
    if (groupId && currentUser) {
      loadPromptData();
    }
  }, [groupId, currentUser]);

  // 定期刷新其他用戶的 prompts（每10秒）
  useEffect(() => {
    if (!groupId || !currentUser) return;
    
    const interval = setInterval(() => {
      loadPromptData();
    }, 10000);
    
    return () => clearInterval(interval);
  }, [groupId, currentUser]);

  const loadPromptData = async () => {
    if (!groupId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // 載入群組摘要
      const summaryResult = await getGroupSummary(groupId);
      if (summaryResult.success) {
        setPromptSummary(summaryResult.summary);
      }
      
      // 載入群組中所有用戶的 prompts
      const promptsResult = await getGroupPrompts(groupId);
      if (promptsResult.success) {
        // 轉換為以 userId 為 key 的對象
        const promptsMap = {};
        promptsResult.prompts.forEach(item => {
          promptsMap[item.userId] = {
            content: item.content,
            updatedAt: item.updatedAt,
            id: item.id
          };
        });
        setPromptsByUser(promptsMap);
      }
    } catch (err) {
      console.error("Failed to load prompt data:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 發送當前用戶的 prompt
  const handleSendPrompt = async () => {
    if (!newPrompt.trim() || !groupId || sendingPrompt || !currentUser) return;
    
    try {
      setSendingPrompt(true);
      setError(null);
      
      const result = await createPrompt(newPrompt.trim());
      
      if (result.success) {
        setNewPrompt("");
        // 立即更新本地狀態
        setPromptsByUser(prev => ({
          ...prev,
          [result.data.userId]: {
            content: result.data.content,
            updatedAt: result.data.updatedAt,
            id: result.data.id
          }
        }));
      } else {
        setError(result.error || "Failed to send prompt");
      }
    } catch (err) {
      console.error("Failed to send prompt:", err);
      setError(err.message);
    } finally {
      setSendingPrompt(false);
    }
  };

  // Enter 鍵發送
  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendPrompt();
    }
  };

  // 格式化時間顯示
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-TW', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  // 如果沒有 token，不顯示內容（登入會在其他地方處理）
  if (!getAuthToken()) {
    return null;
  }

  return (
    <div className="prompt-sidebar">
      {/* Prompt Summary 區域 */}
      <div className="prompt-summary-section">
        <Typography variant="h6" className="section-title">
          群組摘要
        </Typography>
        <div className="prompt-summary-box">
          {loading ? (
            <div className="loading-container">
              <CircularProgress size={20} />
            </div>
          ) : (
            <Typography variant="body2" className="summary-text">
              {promptSummary || "暫無摘要"}
            </Typography>
          )}
        </div>
      </div>

      <Divider className="section-divider" />

      {/* 群組 Prompt 列表區域 */}
      <div className="prompt-list-section">
        <Typography variant="subtitle1" className="list-header">
          群組 Prompts
        </Typography>
        <div className="prompt-list-container">
          {loading ? (
            <div className="loading-container">
              <CircularProgress size={20} />
            </div>
          ) : (
            <div className="prompt-list">
              {Object.entries(promptsByUser).map(([userId, promptData], index) => {
                const isCurrentUser = currentUser && userId == currentUser.id;
                
                return (
                  <div 
                    key={userId} 
                    className={`prompt-item ${isCurrentUser ? 'current-user' : ''} has-content`}
                  >
                    <span className="prompt-id">{index + 1}</span>
                    <div className="prompt-content">
                      <div className="user-info">
                        <Typography variant="body2" className="user-name">
                          用戶 {userId} {isCurrentUser && '(你)'}
                        </Typography>
                        <Typography variant="caption" className="update-time">
                          {formatTime(promptData.updatedAt)}
                        </Typography>
                      </div>
                      <Typography variant="body2" className="prompt-text">
                        {promptData.content}
                      </Typography>
                    </div>
                  </div>
                );
              })}

              {/* 如果沒有任何 prompts */}
              {Object.keys(promptsByUser).length === 0 && !loading && (
                <div className="prompt-item empty">
                  <Typography variant="body2" className="empty-prompt">
                    群組中還沒有任何 prompts
                  </Typography>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 錯誤訊息 */}
      {error && (
        <div className="error-message">
          <Typography variant="body2" color="error">
            {error}
          </Typography>
        </div>
      )}

      {/* 發送 Prompt 區域 */}
      <div className="send-prompt-section">
        <Typography variant="body2" className="input-label">
          輸入你的 Prompt {currentUser && `(${currentUser.username})`}
        </Typography>
        <div className="prompt-input-container">
          <TextField
            fullWidth
            multiline
            maxRows={3}
            placeholder="輸入你的 prompt..."
            value={newPrompt}
            onChange={(e) => setNewPrompt(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={sendingPrompt || !currentUser}
            variant="outlined"
            size="small"
            className="prompt-input"
          />
          <IconButton
            onClick={handleSendPrompt}
            disabled={!newPrompt.trim() || sendingPrompt || !currentUser}
            className="send-button"
            color="primary"
          >
            {sendingPrompt ? (
              <CircularProgress size={20} />
            ) : (
              <SendIcon />
            )}
          </IconButton>
        </div>
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