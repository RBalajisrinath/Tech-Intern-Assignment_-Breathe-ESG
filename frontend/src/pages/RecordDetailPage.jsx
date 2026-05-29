import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiGet, apiPost } from "../api";

export default function RecordDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet(`/records/${id}/`).then(setRecord).catch(console.error).finally(() => setLoading(false));
  }, [id]);

  const doAction = async (action) => {
    const reason = action === "flag" ? prompt("Flag reason:") : "";
    if (action === "flag" && !reason) return;
    await apiPost(`/records/${id}/${action}/`, { action, reason, performed_by: "analyst" });
    const updated = await apiGet(`/records/${id}/`);
    setRecord(updated);
  };

  if (loading) return <div className="text-center py-12 text-gray-400">Loading...</div>;
  if (!record) return <div className="text-center py-12 text-red-400">Record not found</div>;

  const { sap_detail, utility_detail, travel_detail, audit_logs } = record;

  return (
    <div>
      <button onClick={() => navigate("/dashboard")} className="text-emerald-400 hover:underline text-sm mb-4 cursor-pointer">
        &larr; Back to Dashboard
      </button>

      <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold">{record.raw_description || "Emission Record"}</h1>
            <p className="text-sm text-gray-400">Record #{record.id}</p>
          </div>
          <span className={`px-3 py-1 rounded text-sm font-medium border ${
            record.status === "APPROVED" ? "bg-green-500/20 text-green-400 border-green-500" :
            record.status === "FLAGGED" ? "bg-red-500/20 text-red-400 border-red-500" :
            record.status === "LOCKED" ? "bg-purple-500/20 text-purple-400 border-purple-500" :
            record.status === "REVIEWED" ? "bg-blue-500/20 text-blue-400 border-blue-500" :
            "bg-yellow-500/20 text-yellow-400 border-yellow-500"
          }`}>{record.status}</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
          <Field label="Source" value={record.source_type_display} />
          <Field label="Scope" value={record.scope_display} />
          <Field label="Category" value={record.category_display || record.category} />
          <Field label="Subcategory" value={record.subcategory || "—"} />
          <Field label="Raw Quantity" value={`${record.raw_quantity} ${record.raw_unit}`} />
          <Field label="Canonical Quantity" value={`${record.canonical_quantity} ${record.canonical_unit}`} />
          <Field label="Date From" value={record.raw_date_from} />
          <Field label="Date To" value={record.raw_date_to || "—"} />
          <Field label="CO2e" value={record.co2e_kg ? `${record.co2e_kg} kg` : "Not calculated"} />
          <Field label="Edited" value={record.is_edited ? `Yes by ${record.edited_by}` : "No"} />
        </div>

        {record.flag_reason && (
          <div className="bg-red-900/30 border border-red-800 rounded p-3 mb-4">
            <span className="text-xs font-semibold text-red-400">Flag Reason:</span>
            <p className="text-sm text-red-300 mt-1">{record.flag_reason}</p>
          </div>
        )}

        <div className="flex gap-2 mt-4">
          {record.status === "PENDING" && (
            <>
              <button onClick={() => doAction("review")} className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded text-sm cursor-pointer">Mark Reviewed</button>
              <button onClick={() => doAction("approve")} className="bg-green-600 hover:bg-green-500 px-4 py-2 rounded text-sm cursor-pointer">Approve</button>
              <button onClick={() => doAction("flag")} className="bg-red-600 hover:bg-red-500 px-4 py-2 rounded text-sm cursor-pointer">Flag</button>
            </>
          )}
          {record.status === "FLAGGED" && (
            <>
              <button onClick={() => doAction("approve")} className="bg-green-600 hover:bg-green-500 px-4 py-2 rounded text-sm cursor-pointer">Approve Anyway</button>
            </>
          )}
          {record.status === "APPROVED" && (
            <button onClick={() => doAction("lock")} className="bg-purple-600 hover:bg-purple-500 px-4 py-2 rounded text-sm cursor-pointer">Lock for Audit</button>
          )}
          {record.status === "LOCKED" && (
            <button onClick={() => doAction("unlock")} className="bg-yellow-600 hover:bg-yellow-500 px-4 py-2 rounded text-sm cursor-pointer">Unlock</button>
          )}
        </div>
      </div>

      {(sap_detail || utility_detail || travel_detail) && (
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 mb-6">
          <h2 className="text-lg font-semibold mb-3">Source Detail</h2>
          {sap_detail && <DetailTable title="SAP Fuel/Procurement" data={sap_detail} />}
          {utility_detail && <DetailTable title="Utility Electricity" data={utility_detail} />}
          {travel_detail && <DetailTable title="Travel" data={travel_detail} />}
        </div>
      )}

      {audit_logs && audit_logs.length > 0 && (
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
          <h2 className="text-lg font-semibold mb-3">Audit Trail</h2>
          <div className="space-y-2">
            {audit_logs.map((log, i) => (
              <div key={i} className="bg-gray-900 rounded p-3 text-sm flex items-start gap-3">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  log.action === "APPROVE" ? "bg-green-600" :
                  log.action === "FLAG" ? "bg-red-600" :
                  log.action === "LOCK" ? "bg-purple-600" : "bg-blue-600"
                }`}>{log.action}</span>
                <div className="flex-1">
                  <span className="text-gray-300">{log.performed_by}</span>
                  <span className="text-gray-500 mx-2">·</span>
                  <span className="text-gray-500 text-xs">{new Date(log.performed_at).toLocaleString()}</span>
                  {log.new_values?.reason && <p className="text-gray-400 text-xs mt-1">Reason: {log.new_values.reason}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, value }) {
  return (
    <div>
      <span className="text-gray-400 text-xs block">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function DetailTable({ title, data }) {
  return (
    <div className="mb-4">
      <h3 className="text-sm font-semibold text-emerald-400 mb-2">{title}</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm bg-gray-900 rounded p-3">
        {Object.entries(data).filter(([k]) => !k.startsWith("_")).map(([k, v]) => (
          <div key={k}>
            <span className="text-gray-500 text-xs block">{k.replace(/_/g, " ")}</span>
            <span>{v != null ? String(v) : "—"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
