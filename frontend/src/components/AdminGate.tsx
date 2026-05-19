import { AuthUser } from "../types";
import { Admin } from "./Admin";
import { LoginPanel } from "./LoginPanel";

export function AdminGate({
  user,
  onLogin
}: {
  user: AuthUser | null;
  onLogin: (user: AuthUser) => void;
}) {
  if (user?.role === "ROLE_ADMIN") {
    return <Admin />;
  }
  return <LoginPanel onLogin={onLogin} />;
}
