import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { SnackbarProvider } from "notistack";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { blue, green } from "@mui/material/colors";
import Fade from "@mui/material/Fade";

import GameScreen from "./pages/GameScreen";
import HomePage from "./pages/HomePage";
import Lobby from "./pages/Lobby";
import LoginPage from "./pages/LoginPage";
import ProtectedRoute from "./components/ProtectedRoute";
import { StateProvider } from "./store";

import "./App.scss";

const theme = createTheme({
  palette: {
    primary: {
      main: blue[900],
    },
    secondary: {
      main: green[900],
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <StateProvider>
        <SnackbarProvider
          classes={{ containerRoot: ["snackbar-container"] }}
          maxSnack={1}
          autoHideDuration={1000}
          TransitionComponent={Fade}
          TransitionProps={{ timeout: 100 }}
        >
          <Router>
            <Routes>
              <Route
                path="/games/:gameId/states/:stateIndex"
                element={
                  <ProtectedRoute>
                    <GameScreen replayMode={true} />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/games/websocket/:gameId"
                element={
                  <ProtectedRoute>
                    <GameScreen replayMode={false} websocketMode={true} />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/games/:gameId"
                element={
                  <ProtectedRoute>
                    <GameScreen replayMode={false} />
                  </ProtectedRoute>
                }
              />
              <Route 
                path="/lobby" 
                element={
                  <ProtectedRoute>
                    <Lobby />
                  </ProtectedRoute>
                } 
              />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/" exact={true} element={<HomePage />} />
            </Routes>
          </Router>
        </SnackbarProvider>
      </StateProvider>
    </ThemeProvider>
  );
}

export default App;
