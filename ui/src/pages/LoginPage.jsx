import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Button, 
  TextField, 
  Card, 
  CardContent, 
  Typography, 
  Box,
  Alert
} from "@mui/material";
import { GridLoader } from "react-spinners";
import { loginAPI, getCurrentUser } from "../utils/authAPI";

import "./HomePage.scss";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    username: "",
    password: ""
  });
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleInputChange = (field) => (event) => {
    setFormData({
      ...formData,
      [field]: event.target.value
    });
    setError("");
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // 驗證表單
      if (!formData.username || !formData.password) {
        setError("請填寫帳號和密碼");
        return;
      }

      // 1. 呼叫登入 API 取得 Token
      const tokenData = await loginAPI(formData.username, formData.password);
      
      // 2. 使用 Token 取得用戶資訊
      const userData = await getCurrentUser(tokenData.access_token);

      // 3. 儲存完整的登入資訊
      localStorage.setItem("user", JSON.stringify({
        id: userData.id,
        username: userData.username,
        group_id: userData.group_id,
        access_token: tokenData.access_token,
        token_type: tokenData.token_type,
        loginTime: new Date().toISOString()
      }));

      // 4. 跳轉到大廳
      navigate("/lobby");
      
    } catch (err) {
      console.error('登入錯誤:', err);
      
      // 更詳細的錯誤處理
      if (err.message === 'Failed to fetch') {
        setError("無法連接到伺服器，請檢查：\n1. 後端服務是否運行在 http://172.18.10.216:8000\n2. 網路連接是否正常\n3. CORS 設定是否正確");
      } else if (err.message.includes('CORS')) {
        setError("CORS 錯誤：後端需要允許跨域請求");
      } else if (err.message.includes('401') || err.message.includes('Unauthorized')) {
        setError("帳號或密碼錯誤");
      } else {
        setError(err.message || "登入失敗，請檢查網路連線或稍後再試");
      }
    } finally {
      setLoading(false);
    }
  };

  // const handleGuestLogin = () => {
  //   // 訪客登入
  //   const guestUsername = `訪客_${Math.random().toString(36).substr(2, 6)}`;
  //   localStorage.setItem("user", JSON.stringify({ 
  //     username: guestUsername,
  //     isGuest: true,
  //     loginTime: new Date().toISOString()
  //   }));
  //   navigate("/lobby");
  // };

  return (
    <div className="home-page" style={{ minHeight: '100vh', padding: '20px' }}>
      <h1 className="logo">卡坦島 - 登入</h1>

      <div className="switchable">
        {!loading ? (
          <Card sx={{ 
            maxWidth: 400, 
            margin: 'auto', 
            mt: 4,
            minHeight: 'auto',
            overflow: 'visible'
          }}>
            <CardContent sx={{ padding: 3 }}>
              <Typography variant="h5" component="h2" gutterBottom align="center">
                歡迎回來
              </Typography>

              {error && (
                <Alert severity="error" sx={{ mt: 2, mb: 2 }}>
                  {error}
                </Alert>
              )}

              <Box component="form" onSubmit={handleLogin}>
                <TextField
                  fullWidth
                  label="帳號"
                  variant="outlined"
                  value={formData.username}
                  onChange={handleInputChange('username')}
                  sx={{ mb: 2 }}
                  placeholder="請輸入帳號"
                  required
                />
                <TextField
                  fullWidth
                  label="密碼"
                  type="password"
                  variant="outlined"
                  value={formData.password}
                  onChange={handleInputChange('password')}
                  sx={{ mb: 3 }}
                  placeholder="請輸入密碼"
                  required
                />
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                  <Button
                    type="submit"
                    variant="contained"
                    color="primary"
                    size="large"
                    sx={{ minWidth: 200 }}
                  >
                    登入
                  </Button>
                </Box>
              </Box>

              {/* <Box sx={{ textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  或者
                </Typography>
                <Button
                  variant="outlined"
                  color="secondary"
                  onClick={handleGuestLogin}
                  fullWidth
                  size="large"
                  sx={{ mb: 2 }}
                >
                  訪客模式進入
                </Button>
              </Box> */}

              {/* API 連接說明
              <Box sx={{ 
                mt: 2, 
                p: 2, 
                backgroundColor: '#e3f2fd', 
                borderRadius: 1,
                fontSize: '0.75rem'
              }}>
                <Typography variant="caption" color="text.secondary">
                  <strong>API 連接設定：</strong><br/>
                  確保後端服務運行在 http://172.18.10.216:8000<br/>
                  使用真實的帳號密碼進行登入
                </Typography>
              </Box> */}
            </CardContent>
          </Card>
        ) : (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
            <GridLoader
              className="loader"
              color="#1976d2"
              height={60}
              width={60}
            />
          </Box>
        )}
      </div>
    </div>
  );
}
