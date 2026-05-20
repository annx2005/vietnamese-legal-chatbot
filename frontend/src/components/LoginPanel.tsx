import { FormEvent, useState } from "react";
import { AlertTriangle, Loader2, LockKeyhole, LogIn, ShieldCheck } from "lucide-react";
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
      <form className="auth-panel" onSubmit={submit}>
        <div className="auth-header">
          <div className="auth-icon" aria-hidden="true">
            <ShieldCheck size={26} />
          </div>
          <p className="eyebrow">Admin access</p>
          <h1>Đăng nhập quản trị</h1>
          <p>Truy cập bảng điều hành để quản lý tài liệu, ingest jobs và chất lượng chatbot.</p>
        </div>

        <label htmlFor="admin-username">
          Tên đăng nhập
          <input
            id="admin-username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
          />
        </label>
        <label htmlFor="admin-password">
          Mật khẩu
          <input
            id="admin-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            autoComplete="current-password"
          />
        </label>

        <div className="secure-note">
          <LockKeyhole size={15} />
          Chỉ tài khoản có quyền ROLE_ADMIN mới được truy cập khu vực này.
        </div>

        <button className="primary" disabled={loading || !username.trim() || !password}>
          {loading ? <Loader2 className="spin" size={18} /> : <LogIn size={18} />}
          Đăng nhập
        </button>
        {error && (
          <div className="notice danger alert-card" role="alert">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}
      </form>
    </section>
  );
}
