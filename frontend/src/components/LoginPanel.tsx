import { FormEvent, useState } from "react";
import { Loader2, LogIn } from "lucide-react";
import { api } from "../api";
import { AuthUser } from "../types";

export function LoginPanel({ onLogin }: { onLogin: (user: AuthUser) => void }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await api.login({ username, password });
      if (result.role !== "ROLE_ADMIN") {
        setError("Tài khoản này không có quyền admin.");
        return;
      }
      onLogin(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không đăng nhập được");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="workspace auth-workspace">
      <header className="page-header">
        <div>
          <p className="eyebrow">Admin access</p>
          <h1>Đăng nhập quản trị</h1>
        </div>
      </header>

      <form className="auth-panel" onSubmit={submit}>
        <label>
          Tên đăng nhập
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
          />
        </label>
        <label>
          Mật khẩu
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            autoComplete="current-password"
          />
        </label>
        <button className="primary" disabled={loading || !username.trim() || !password}>
          {loading ? <Loader2 className="spin" size={18} /> : <LogIn size={18} />}
          Đăng nhập
        </button>
        {error && <div className="notice danger">{error}</div>}
      </form>
    </section>
  );
}
