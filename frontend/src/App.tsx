import { useEffect, useState } from "react";
import {
  BarChart3,
  LogIn,
  LogOut,
  MessageSquareText,
  Scale,
  ShieldCheck,
  Sparkles,
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
          <div className="brand-mark" aria-hidden="true">
            <ShieldCheck size={24} />
          </div>
          <div className="brand-copy">
            <strong>Tra cứu pháp luật</strong>
            <span>Legal RAG Assistant</span>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          <button
            className={path === "/chat" ? "nav active" : "nav"}
            onClick={() => setPath("/chat")}
            aria-current={path === "/chat" ? "page" : undefined}
          >
            <span className="nav-indicator" />
            <MessageSquareText size={18} />
            <span>Chat</span>
          </button>
          {isAdmin ? (
            <button
              className={path === "/admin" ? "nav active" : "nav"}
              onClick={() => setPath("/admin")}
              aria-current={path === "/admin" ? "page" : undefined}
            >
              <span className="nav-indicator" />
              <BarChart3 size={18} />
              <span>Admin</span>
            </button>
          ) : (
            <button
              className={path === "/admin" ? "nav active" : "nav"}
              onClick={() => setPath("/admin")}
              aria-current={path === "/admin" ? "page" : undefined}
            >
              <span className="nav-indicator" />
              <LogIn size={18} />
              <span>Đăng nhập</span>
            </button>
          )}
        </nav>

        {user && (
          <div className="account-panel">
            <div className="account-avatar" aria-hidden="true">
              <Scale size={18} />
            </div>
            <div className="account-copy">
              <span>{user.username}</span>
              <small>{user.role === "ROLE_ADMIN" ? "Administrator" : "User"}</small>
            </div>
            <div className="account-badge">
              <Sparkles size={13} />
              Active
            </div>
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
