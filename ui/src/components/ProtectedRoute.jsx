import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { validateToken, getStoredUser } from "../utils/authAPI";
import { Box, CircularProgress, Typography } from "@mui/material";

export default function ProtectedRoute({ children }) {
  const [loading, setLoading] = useState(true);
  const [isValid, setIsValid] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      const user = getStoredUser();
      
      if (!user || !user.access_token) {
        setIsValid(false);
        setLoading(false);
        return;
      }

      // 驗證 Token 是否還有效
      const { valid } = await validateToken(user.access_token);
      setIsValid(valid);
      setLoading(false);
    };

    checkAuth();
  }, []);

  if (loading) {
    return (
      <Box 
        sx={{ 
          display: 'flex', 
          flexDirection: 'column',
          justifyContent: 'center', 
          alignItems: 'center', 
          minHeight: '100vh' 
        }}
      >
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>驗證登入狀態...</Typography>
      </Box>
    );
  }

  return isValid ? children : <Navigate to="/login" replace />;
}
