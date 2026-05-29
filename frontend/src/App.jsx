import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import DashboardPage from "./pages/DashboardPage";
import RecordDetailPage from "./pages/RecordDetailPage";

function Layout({ children }) {
  const linkClass = ({ isActive }) =>
    `px-3 py-2 rounded text-sm font-medium ${isActive ? "bg-emerald-600 text-white" : "text-gray-300 hover:bg-emerald-700 hover:text-white"}`;

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <nav className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex items-center gap-6">
        <span className="text-emerald-400 font-bold text-lg">Breathe ESG</span>
        <NavLink to="/upload" className={linkClass}>Upload</NavLink>
        <NavLink to="/dashboard" className={linkClass}>Review Dashboard</NavLink>
      </nav>
      <main className="p-6 max-w-7xl mx-auto">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/records/:id" element={<RecordDetailPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
