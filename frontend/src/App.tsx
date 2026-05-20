import { useEffect, useState } from "react";
import {
  BarChart3,
  LogIn,
  LogOut,
  MessageSquareText,
  ShieldCheck,
} from "lucide-react";
import { AuthUser } from "./types";
import { readStoredUser, AUTH_STORAGE_KEY } from "./api";
import { Chat } from "./components/Chat";
import { AdminGate } from "./components/AdminGate";

export default function App() {
  const [path, setPath] = useState(
    window.location.pathname === "/admin" ? "/admin" : "/chat",
  );
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser());
  const isAdmin = user?.role === "ROLE_ADMIN";

  useEffect(() => {
    window.history.replaceState(null, "", path);
  }, [path]);

  function saveUser(nextUser: AuthUser) {
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(nextUser));
    setUser(nextUser);
    setPath("/admin");
  }

  function logout() {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    setUser(null);
    setPath("/chat");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={24} />
          <div>
            <strong>Tra cứu pháp luật</strong>
          </div>
        </div>
        <button
          className={path === "/chat" ? "nav active" : "nav"}
          onClick={() => setPath("/chat")}
        >
          <MessageSquareText size={18} /> Chat
        </button>
        {isAdmin ? (
          <button
            className={path === "/admin" ? "nav active" : "nav"}
            onClick={() => setPath("/admin")}
          >
            <BarChart3 size={18} /> Admin
          </button>
        ) : (
          <button
            className={path === "/admin" ? "nav active" : "nav"}
            onClick={() => setPath("/admin")}
          >
            <LogIn size={18} /> Đăng nhập
          </button>
        )}
        {user && (
          <div className="account-panel">
            <span>{user.username}</span>
            <small>{user.role === "ROLE_ADMIN" ? "Admin" : "User"}</small>
            <button className="ghost logout-button" onClick={logout}>
              <LogOut size={16} /> Đăng xuất
            </button>
          </div>
        )}
      </aside>
      <main className="main">
        {path === "/admin" ? (
          <AdminGate user={user} onLogin={saveUser} />
        ) : (
          <Chat />
        )}
      </main>
    </div>
  );
}
