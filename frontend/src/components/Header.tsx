import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  function handleLogout() {
    logout();
    navigate("/", { replace: true });
  }

  const evalsActive = location.pathname.startsWith("/evals");

  return (
    <header className="border-b border-ink-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 md:px-6">
        <Link to="/" className="flex items-center gap-2 text-ink-900">
          <span className="grid h-8 w-8 place-items-center rounded-md bg-brand-600 text-white font-bold">
            P
          </span>
          <span className="text-base font-semibold tracking-tight md:text-lg">
            PlacementIQ
          </span>
        </Link>

        <nav className="flex items-center gap-2 text-sm">
          <Link
            to="/evals"
            className={
              "rounded-md px-3 py-1.5 transition-colors " +
              (evalsActive
                ? "bg-brand-50 text-brand-700"
                : "text-ink-600 hover:bg-ink-100")
            }
          >
            Evals
          </Link>

          {user ? (
            <>
              <span className="hidden rounded-full bg-ink-100 px-3 py-1 text-xs font-medium text-ink-700 md:inline">
                {user.role === "student" ? `Student · ${user.studentId}` : "Counselor"}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-md border border-ink-200 px-3 py-1.5 text-sm font-medium text-ink-700 hover:bg-ink-100"
              >
                Logout
              </button>
            </>
          ) : (
            <Link
              to="/"
              className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
