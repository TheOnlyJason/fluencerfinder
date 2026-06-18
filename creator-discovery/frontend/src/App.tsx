import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import DatabasePage from "./pages/DatabasePage";
import SearchPage from "./pages/SearchPage";
import CreatorDetailPage from "./pages/CreatorDetailPage";
import "./App.css";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("sidebarCollapsed") === "1"
  );
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
          </NavLink>
        </nav>

        <div className="sidebar-footer">Creator Discovery MVP</div>
      </aside>

      <div className="content">
        <main className="main">
          <Routes>
            <Route path="/" element={<DatabasePage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/creators/:id" element={<CreatorDetailPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
