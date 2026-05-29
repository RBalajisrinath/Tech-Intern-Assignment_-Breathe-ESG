import { useState } from "react";
import { apiUploadFile } from "../api";

const SOURCE_TYPES = [
  { value: "SAP", label: "SAP - Fuel & Procurement", desc: "German CSV with MATNR, MENGE, MEINS columns. Supports semicolon delimiters." },
  { value: "UTILITY", label: "Utility - Electricity", desc: "CSV with Meter ID, Billing Start/End, Consumption (kWh), Tariff." },
  { value: "TRAVEL", label: "Corporate Travel", desc: "CSV with expense type, vendor, dates, origin/destination airport codes, class of service." },
];

export default function UploadPage() {
  const [sourceType, setSourceType] = useState("SAP");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) { setError("Please select a file"); return; }
    setUploading(true);
    setError("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("source_type", sourceType);
      form.append("organization", "1");
      form.append("file", file);
      form.append("uploaded_by", "analyst");
      const data = await apiUploadFile("/uploads/upload_file/", form);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Upload Data</h1>
      <p className="text-gray-400 mb-6">Select a source type and upload a CSV file. The system will parse, validate, and normalize the data.</p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
        {SOURCE_TYPES.map((st) => (
          <button key={st.value} onClick={() => setSourceType(st.value)}
            className={`text-left p-4 rounded-lg border-2 transition cursor-pointer ${
              sourceType === st.value ? "border-emerald-500 bg-gray-800" : "border-gray-700 bg-gray-800/50 hover:border-gray-500"
            }`}>
            <h3 className="font-semibold text-emerald-400">{st.label}</h3>
            <p className="text-sm text-gray-400 mt-1">{st.desc}</p>
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">CSV File</label>
          <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files[0])}
            className="w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-emerald-600 file:text-white hover:file:bg-emerald-500 cursor-pointer" />
        </div>
        <button type="submit" disabled={uploading}
          className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2 rounded font-medium disabled:opacity-50 cursor-pointer">
          {uploading ? "Uploading & Parsing..." : "Upload & Parse"}
        </button>
      </form>

      {error && <div className="mt-6 bg-red-900/50 border border-red-700 p-4 rounded text-red-300">{error}</div>}

      {result && (
        <div className="mt-6 bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-lg font-semibold text-emerald-400 mb-2">Upload Result</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><span className="text-gray-400">Status:</span> <span className="font-medium">{result.status}</span></div>
            <div><span className="text-gray-400">Total rows:</span> <span className="font-medium">{result.row_count}</span></div>
            <div><span className="text-gray-400">Parsed:</span> <span className="font-medium text-green-400">{result.parsed_count}</span></div>
            <div><span className="text-gray-400">Errors:</span> <span className="font-medium text-red-400">{result.error_count}</span></div>
          </div>
          {result.error_log?.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-red-400 mb-1">Errors ({result.error_log.length})</h3>
              <div className="bg-gray-900 rounded p-3 text-xs text-red-300 max-h-40 overflow-y-auto font-mono">
                {result.error_log.map((e, i) => <div key={i}>Row {e.row}: {e.error}</div>)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
