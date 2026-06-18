import { useEffect, useState, ReactNode } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import DatabasePage from "./pages/DatabasePage";
import SearchPage from "./pages/SearchPage";
import GroupsPage from "./pages/GroupsPage";
import LoginPage from "./pages/LoginPage";
import CreatorDetailPage from "./pages/CreatorDetailPage";
import SelectionBar from "./components/SelectionBar";
import { useAuth } from "./auth";
import { useGroups } from "./groupsContext";
import "./App.css";

function RequireAuth({ feature, children }: { feature: string; children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="loading">Loading…</div>;
  if (!user) {
    return (
      <div className="auth-gate">
        <div className="auth-gate-icon">🔒</div>
        <h1>Sign in to use {feature}</h1>
        <p>{feature} is available to signed-in users. Sign in or create an account to continue.</p>
        <Link to="/login" state={{ from: location.pathname }} className="btn btn-primary">
          Sign in
        </Link>
      </div>
    );
  }
  return <>{children}</>;
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("sidebarCollapsed") === "1"
  );
  const { user, signOut } = useAuth();
  const { groups } = useGroups();
  const closeSidebar = () => setSidebarOpen(false);

  useEffect(() => {
    localStorage.setItem("sidebarCollapsed", collapsed ? "1" : "0");
  }, [collapsed]);

  return (
    <div className={`app${collapsed ? " sidebar-collapsed" : ""}`}>
      <div className="mobile-topbar">
        <button
          type="button"
          className="sidebar-toggle"
          aria-label="Toggle navigation"
          aria-expanded={sidebarOpen}
          onClick={() => setSidebarOpen((o) => !o)}
        >
          ☰
        </button>
        <Link to="/" className="logo" onClick={closeSidebar}>
          <span className="logo-icon">◈</span>
          Creator Discovery
        </Link>
      </div>

      {sidebarOpen && <div className="sidebar-overlay" onClick={closeSidebar} />}

      <aside className={`sidebar${sidebarOpen ? " is-open" : ""}${collapsed ? " is-collapsed" : ""}`}>
        <div className="sidebar-head">
          <Link to="/" className="logo sidebar-logo" onClick={closeSidebar} title="Creator Discovery">
            <span className="logo-icon">◈</span>
            <span className="logo-text">Creator Discovery</span>
          </Link>
          <button
            type="button"
            className="sidebar-collapse-btn"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => setCollapsed((c) => !c)}
          >
            {collapsed ? "»" : "«"}
          </button>
        </div>

        <nav className="sidebar-nav">
          <NavLink to="/" end className="sidebar-link" onClick={closeSidebar} title="Database">
            <span className="sidebar-link-icon">🗂️</span>
            <span className="sidebar-link-label">Database</span>
          </NavLink>
          <NavLink to="/search" className="sidebar-link" onClick={closeSidebar} title="Search">
            <span className="sidebar-link-icon">🔍</span>
            <span className="sidebar-link-label">Search</span>
            {!user && <span className="sidebar-link-lock" title="Sign in required">🔒</span>}
          </NavLink>
          <NavLink to="/groups" end className="sidebar-link" onClick={closeSidebar} title="Groups">
            <span className="sidebar-link-icon">📁</span>
            <span className="sidebar-link-label">Groups</span>
            {!user && <span className="sidebar-link-lock" title="Sign in required">🔒</span>}
          </NavLink>
          {user && groups.length > 0 && (
            <div className="sidebar-subnav">
              {groups.map((g) => (
                <NavLink
                  key={g.id}
                  to={`/groups/${g.id}`}
                  className="sidebar-sublink"
                  onClick={closeSidebar}
                  title={g.name}
                >
                  <span className="sidebar-sublink-dot">•</span>
                  <span className="sidebar-sublink-label">{g.name}</span>
                  <span className="sidebar-sublink-count">{g.member_count ?? 0}</span>
                </NavLink>
              ))}
            </div>
          )}
        </nav>

        <div className="sidebar-account">
          {user ? (
            <>
              <div className="sidebar-account-email" title={user.email ?? ""}>
                {user.email}
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm sidebar-signout"
                onClick={() => signOut()}
              >
                Sign out
              </button>
            </>
          ) : (
            <Link to="/login" className="btn btn-primary btn-sm sidebar-signin" onClick={closeSidebar}>
              Sign in
            </Link>
          )}
        </div>
      </aside>

      <div className="content">
        <main className="main">
          <Routes>
            <Route path="/" element={<DatabasePage />} />
            <Route
              path="/search"
              element={
                <RequireAuth feature="Search">
                  <SearchPage />
                </RequireAuth>
              }
            />
            <Route
              path="/groups"
              element={
                <RequireAuth feature="Groups">
                  <GroupsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/groups/:groupId"
              element={
                <RequireAuth feature="Groups">
                  <GroupsPage />
                </RequireAuth>
              }
            />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/creators/:id" element={<CreatorDetailPage />} />
          </Routes>
        </main>
        <SelectionBar />
      </div>
    </div>
  );
}
