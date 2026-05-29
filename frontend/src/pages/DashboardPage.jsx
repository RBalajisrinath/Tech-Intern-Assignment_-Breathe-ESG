import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiGet, apiPost } from "../api";

const STATUS_COLORS = {
  PENDING: "bg-yellow-500/20 text-yellow-400 border-yellow-500",
  REVIEWED: "bg-blue-500/20 text-blue-400 border-blue-500",
  APPROVED: "bg-green-500/20 text-green-400 border-green-500",
  FLAGGED: "bg-red-500/20 text-red-400 border-red-500",
  LOCKED: "bg-purple-500/20 text-purple-400 border-purple-500",
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const [records, setRecords] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: "", source_type: "", scope: "" });
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState(new Set());

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ organization: "1", page, page_size: "50" });
      if (filters.status) params.set("status", filters.status);
      if (filters.source_type) params.set("source_type", filters.source_type);
      if (filters.scope) params.set("scope", filters.scope);

      const [data, statsData] = await Promise.all([
        apiGet(`/records/?${params}`),
        apiGet(`/records/stats/?organization=1`),
      ]);
      setRecords(data.results || []);
      setTotal(data.count || 0);
      setStats(statsData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [page, filters]);

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const bulkApprove = async () => {
    if (selected.size === 0) return;
    await apiPost("/records/bulk_approve/", { ids: Array.from(selected), performed_by: "analyst" });
    setSelected(new Set());
    fetchData();
  };

  const actionRecord = async (id, action) => {
    await apiPost(`/records/${id}/${action}/`, { action, performed_by: "analyst" });
    fetchData();
  };

  const totalPages = Math.ceil(total / 50);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Review Dashboard</h1>
        {selected.size > 0 && (
          <button onClick={bulkApprove}
            className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded text-sm font-medium cursor-pointer">
            Approve {selected.size} Selected
          </button>
        )}
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
          <StatBox label="Total" value={stats.total} />
          <StatBox label="Pending" value={stats.pending} color="text-yellow-400" />
          <StatBox label="Reviewed" value={stats.reviewed} color="text-blue-400" />
          <StatBox label="Approved" value={stats.approved} color="text-green-400" />
          <StatBox label="Flagged" value={stats.flagged} color="text-red-400" />
          <StatBox label="Scope 1" value={stats.scope_1} />
          <StatBox label="Scope 2" value={stats.scope_2} />
          <StatBox label="Scope 3" value={stats.scope_3} />
        </div>
      )}

      <div className="flex gap-3 mb-4 flex-wrap">
        <select value={filters.status} onChange={(e) => { setFilters(f => ({...f, status: e.target.value})); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm">
          <option value="">All Status</option>
          <option value="PENDING">Pending</option>
          <option value="REVIEWED">Reviewed</option>
          <option value="APPROVED">Approved</option>
          <option value="FLAGGED">Flagged</option>
          <option value="LOCKED">Locked</option>
        </select>
        <select value={filters.source_type} onChange={(e) => { setFilters(f => ({...f, source_type: e.target.value})); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm">
          <option value="">All Sources</option>
          <option value="SAP">SAP</option>
          <option value="UTILITY">Utility</option>
          <option value="TRAVEL">Travel</option>
        </select>
        <select value={filters.scope} onChange={(e) => { setFilters(f => ({...f, scope: e.target.value})); setPage(1); }}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm">
          <option value="">All Scopes</option>
          <option value="1">Scope 1</option>
          <option value="2">Scope 2</option>
          <option value="3">Scope 3</option>
        </select>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading...</div>
      ) : (
        <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-left text-gray-400">
                <th className="p-3 w-8"><input type="checkbox" className="cursor-pointer" /></th>
                <th className="p-3">Description</th>
                <th className="p-3">Source</th>
                <th className="p-3">Scope</th>
                <th className="p-3">Category</th>
                <th className="p-3">Quantity</th>
                <th className="p-3">Status</th>
                <th className="p-3">Date</th>
                <th className="p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id} className="border-b border-gray-700 hover:bg-gray-700/50">
                  <td className="p-3">
                    <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSelect(r.id)} className="cursor-pointer" />
                  </td>
                  <td className="p-3">
                    <button onClick={() => navigate(`/records/${r.id}`)} className="text-emerald-400 hover:underline text-left cursor-pointer">
                      {r.raw_description?.substring(0, 50) || "(no description)"}
                    </button>
                  </td>
                  <td className="p-3">{r.source_type_display}</td>
                  <td className="p-3">{r.scope_display}</td>
                  <td className="p-3">{r.category_display || r.category}</td>
                  <td className="p-3">{r.raw_quantity} {r.raw_unit}</td>
                  <td className="p-3">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${STATUS_COLORS[r.status] || "bg-gray-600"}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="p-3 text-gray-400 text-xs">{r.raw_date_from}</td>
                  <td className="p-3 flex gap-1">
                    {r.status === "PENDING" && (
                      <>
                        <button onClick={() => actionRecord(r.id, "approve")} className="text-xs bg-green-600 hover:bg-green-500 px-2 py-1 rounded cursor-pointer">Approve</button>
                        <button onClick={() => {
                          const reason = prompt("Flag reason:");
                          if (reason) apiPost(`/records/${r.id}/flag/`, { action: "flag", reason, performed_by: "analyst" }).then(fetchData);
                        }} className="text-xs bg-red-600 hover:bg-red-500 px-2 py-1 rounded cursor-pointer">Flag</button>
                      </>
                    )}
                    {r.status === "FLAGGED" && (
                      <button onClick={() => actionRecord(r.id, "approve")} className="text-xs bg-green-600 hover:bg-green-500 px-2 py-1 rounded cursor-pointer">Approve</button>
                    )}
                    {r.status === "APPROVED" && (
                      <button onClick={() => actionRecord(r.id, "lock")} className="text-xs bg-purple-600 hover:bg-purple-500 px-2 py-1 rounded cursor-pointer">Lock</button>
                    )}
                    {r.status === "LOCKED" && (
                      <span className="text-xs text-purple-400 px-2 py-1">Locked</span>
                    )}
                  </td>
                </tr>
              ))}
              {records.length === 0 && (
                <tr><td colSpan={9} className="p-6 text-center text-gray-500">No records found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          <button disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}
            className="px-3 py-1 bg-gray-800 border border-gray-700 rounded text-sm disabled:opacity-50 cursor-pointer">Previous</button>
          <span className="px-3 py-1 text-sm text-gray-400">Page {page} of {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
            className="px-3 py-1 bg-gray-800 border border-gray-700 rounded text-sm disabled:opacity-50 cursor-pointer">Next</button>
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value, color = "text-gray-100" }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded p-3 text-center">
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      <div className="text-xs text-gray-400">{label}</div>
    </div>
  );
}
