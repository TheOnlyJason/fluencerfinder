import { Link, Route, Routes } from "react-router-dom";
import SearchPage from "./pages/SearchPage";
import CreatorDetailPage from "./pages/CreatorDetailPage";
import "./App.css";

export default function App() {
  return (
    <div className="app">
      <header className="header">
        <Link to="/" className="logo">
          <span className="logo-icon">◈</span>
          Creator Discovery
        </Link>
        <nav>
          <Link to="/">Search</Link>
        </nav>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/creators/:id" element={<CreatorDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
