import { Navigate, Route, Routes } from "react-router-dom";
import Nav from "./components/Nav.jsx";
import Today from "./pages/Today.jsx";
import Chat from "./pages/Chat.jsx";
import History from "./pages/History.jsx";
import Profile from "./pages/Profile.jsx";
import "./App.css";

export default function App() {
  return (
    <div className="app">
      <Nav />
      <main className="app-content">
        <Routes>
          <Route path="/" element={<Navigate to="/today" replace />} />
          <Route path="/today" element={<Today />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/history" element={<History />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="*" element={<Navigate to="/today" replace />} />
        </Routes>
      </main>
    </div>
  );
}
