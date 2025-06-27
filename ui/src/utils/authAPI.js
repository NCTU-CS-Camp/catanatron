// API 基礎設定
<<<<<<< HEAD
const API_BASE_URL = 'http://172.18.8.215:8000';
=======
const API_BASE_URL = "http://172.18.8.215:8000";
>>>>>>> 9ff00ae574081d8a38ed8108107429995398f8e5

// 登入獲取 Token
export const loginAPI = async (username, password) => {
  const response = await fetch(`${API_BASE_URL}/token`, {
    method: "POST",
    headers: {  
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      username: username,
      password: password,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "登入失敗");
  }

  return await response.json();
};

// 獲取當前用戶資訊
export const getCurrentUser = async (accessToken) => {
  const response = await fetch(`${API_BASE_URL}/users/me/`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error("取得用戶資訊失敗");
  }

  return await response.json();
};

// 驗證 Token 是否有效
export const validateToken = async (accessToken) => {
  try {
    const userData = await getCurrentUser(accessToken);
    return { valid: true, userData };
  } catch (error) {
    return { valid: false, error: error.message };
  }
};

// 登出（清除本地資料）
export const logout = () => {
  localStorage.removeItem("user");
  window.location.href = "/login";
};

// 獲取儲存的用戶資訊
export const getStoredUser = () => {
  try {
    const userStr = localStorage.getItem("user");
    return userStr ? JSON.parse(userStr) : null;
  } catch (error) {
    console.error("解析用戶資料失敗:", error);
    return null;
  }
};

// 檢查是否已登入
export const isLoggedIn = () => {
  const user = getStoredUser();
  return user && user.access_token;
};

// 獲取 Authorization Header
export const getAuthHeader = () => {
  const user = getStoredUser();
  return user && user.access_token ? `Bearer ${user.access_token}` : null;
};

// 通用的 API 請求函數（自動帶入 Token）
export const authenticatedFetch = async (url, options = {}) => {
  const authHeader = getAuthHeader();

  if (!authHeader) {
    throw new Error("未登入，請先登入");
  }

  const defaultHeaders = {
    "Content-Type": "application/json",
    Authorization: authHeader,
  };

  const finalOptions = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  const response = await fetch(url, finalOptions);

  // 如果是 401 錯誤，可能是 Token 過期
  if (response.status === 401) {
    logout(); // 自動登出
    throw new Error("登入已過期，請重新登入");
  }

  return response;
};
