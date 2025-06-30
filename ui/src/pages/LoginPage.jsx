import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Button, 
  TextField, 
  Card, 
  CardContent, 
  Typography, 
  Box,
  Alert,
  Container,
  Avatar,
  Fade,
  Grow
} from "@mui/material";
import { GridLoader } from "react-spinners";
import { loginAPI, getCurrentUser } from "../utils/authAPI";
import { SportsEsports, Lock, Person } from "@mui/icons-material";

import "./HomePage.scss";
import "./LoginPage.scss";

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
    <div className="login-page">
      {/* 海洋泡泡動畫背景 */}
      <div className="background-animation">
        <div className="floating-shape shape-1"></div>
        <div className="floating-shape shape-2"></div>
        <div className="floating-shape shape-3"></div>
        <div className="floating-shape shape-4"></div>
        <div className="floating-shape shape-5"></div>
        {/* 額外的小泡泡 */}
        <div className="floating-shape" style={{
          width: '25px', height: '25px', top: '15%', right: '25%',
          animationDelay: '7s', animationDuration: '10s'
        }}></div>
        <div className="floating-shape" style={{
          width: '35px', height: '35px', bottom: '20%', left: '70%',
          animationDelay: '5s', animationDuration: '9s'
        }}></div>
        <div className="floating-shape" style={{
          width: '15px', height: '15px', top: '70%', left: '80%',
          animationDelay: '9s', animationDuration: '11s'
        }}></div>
      </div>

      <Container maxWidth="sm" className="login-container">
        <Fade in={true} timeout={1000}>
          <div className="login-header">
            <Avatar className="game-icon">
              <SportsEsports sx={{ fontSize: 40 }} />
            </Avatar>
            <Typography variant="h2" component="h1" className="main-title">
              CS CAMP CATAN
            </Typography>
            <Typography variant="h5" component="h2" className="sub-title">
              歡迎來到卡坦島世界
            </Typography>
          </div>
        </Fade>

        <Grow in={true} timeout={1200}>
          <div className="login-form-container">
            {!loading ? (
              <Card className="login-card">
                <CardContent className="login-card-content">
                  <Box className="login-form-header">
                    <Avatar className="login-avatar">
                      <Lock />
                    </Avatar>
                    <Typography variant="h5" component="h3" className="form-title">
                      登入遊戲
                    </Typography>
                  </Box>

                  {error && (
                    <Fade in={!!error}>
                      <Alert severity="error" className="error-alert">
                        {error}
                      </Alert>
                    </Fade>
                  )}

                  <Box component="form" onSubmit={handleLogin} className="login-form">
                    <Box className="input-group">
                      <Person className="input-icon" />
                      <TextField
                        fullWidth
                        label="帳號"
                        variant="outlined"
                        value={formData.username}
                        onChange={handleInputChange('username')}
                        placeholder="請輸入帳號"
                        required
                        className="styled-input"
                      />
                    </Box>
                    
                    <Box className="input-group">
                      <Lock className="input-icon" />
                      <TextField
                        fullWidth
                        label="密碼"
                        type="password"
                        variant="outlined"
                        value={formData.password}
                        onChange={handleInputChange('password')}
                        placeholder="請輸入密碼"
                        required
                        className="styled-input"
                      />
                    </Box>

                    <Button
                      type="submit"
                      variant="contained"
                      size="large"
                      className="login-button"
                      fullWidth
                    >
                      開始遊戲
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            ) : (
              <Card className="loading-card">
                <CardContent className="loading-content">
                  <GridLoader
                    color="#2196f3"
                    size={15}
                    margin={5}
                    speedMultiplier={0.8}
                  />
                  <Typography variant="h6" className="loading-text">
                    正在連接伺服器...
                  </Typography>
                </CardContent>
              </Card>
            )}
          </div>
        </Grow>
      </Container>
    </div>
  );
}
