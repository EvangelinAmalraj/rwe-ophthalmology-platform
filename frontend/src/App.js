import { useEffect, useState } from "react";
import {
  LineChart, Line,
  BarChart, Bar,
  XAxis, YAxis,
  Tooltip, CartesianGrid
} from "recharts";
import "./App.css";

/* ================= BACKEND BASE URL ================= */
const API_BASE = "http://127.0.0.1:8000";

function App() {
  /* ================= DATA STATE ================= */
  const [bcvaTrend, setBcvaTrend] = useState([]);
  const [injData, setInjData] = useState([]);
  const [fluidData, setFluidData] = useState([]);
  const [hardHrfData, setHardHrfData] = useState([]);
  const [hasAppliedFilters, setHasAppliedFilters] = useState(false);

  /* ================= FILTER STATE ================= */
  const [diagnosis, setDiagnosis] = useState("");
  const [minAge, setMinAge] = useState("");
  const [maxAge, setMaxAge] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  /* ================= BUILD QUERY STRING FROM FILTERS ================= */
  const buildFilterQuery = () => {
    const params = new URLSearchParams();

    if (diagnosis) params.append("diagnosis", diagnosis);
    if (minAge) params.append("min_age", minAge);
    if (maxAge) params.append("max_age", maxAge);
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);

    return params.toString();
  };

  /* ================= FETCH BCVA WITH FILTERS ================= */
  const fetchFilteredBCVA = async (queryString) => {
    try {
      const url = queryString
        ? `${API_BASE}/analytics/bcva-filtered?${queryString}`
        : `${API_BASE}/analytics/bcva-filtered`;

      const res = await fetch(url);

      if (!res.ok) {
        throw new Error(`BCVA API failed: ${res.status}`);
      }

      const data = await res.json();
      setBcvaTrend(data);
    } catch (err) {
      console.error("BCVA fetch error:", err);
      setBcvaTrend([]);
    }
  };

  /* ================= FETCH OTHER CHARTS (FILTER AWARE) ================= */
  const fetchOtherCharts = async (queryString) => {
    try {
      const qs = queryString ? `?${queryString}` : "";

      const injRes = await fetch(`${API_BASE}/analytics/injection-bcva${qs}`);
      if (injRes.ok) {
        setInjData(await injRes.json());
      } else {
        setInjData([]);
      }

      const fluidRes = await fetch(`${API_BASE}/analytics/fluid${qs}`);
      if (fluidRes.ok) {
        setFluidData(await fluidRes.json());
      } else {
        setFluidData([]);
      }

      const hardHrfRes = await fetch(`${API_BASE}/analytics/hard-hrf${qs}`);
      if (hardHrfRes.ok) {
        setHardHrfData(await hardHrfRes.json());
      } else {
        setHardHrfData([]);
      }
    } catch (err) {
      console.error("Other charts fetch error:", err);
    }
  };

  /* ================= EXPORT PDF ================= */
  const exportPDF = () => {
    const queryString = buildFilterQuery();
    const url = queryString
      ? `${API_BASE}/export/pdf?${queryString}`
      : `${API_BASE}/export/pdf`;

    window.open(url, "_blank");
  };

  /* ================= APPLY FILTERS HANDLER ================= */
  const applyFilters = () => {
    const queryString = buildFilterQuery();

    // Fetch all charts based on the current filters
    fetchFilteredBCVA(queryString);
    fetchOtherCharts(queryString);

    // Show the charts only after filters have been applied at least once
    setHasAppliedFilters(true);
  };

  // No initial data load: charts will stay hidden until filters are applied
  useEffect(() => {
    // intentionally empty
  }, []);

  /* ================= UI ================= */
  return (
    <div className="container">
      <h1>Ophthalmology RWE Dashboard</h1>

      {/* FILTERS */}
      <div className="filters">
        <label>Diagnosis</label>
        <select onChange={(e) => setDiagnosis(e.target.value)}>
          <option value="">All</option>
          <option value="DME">DME</option>
          <option value="AMD">AMD</option>
        </select>

        <label>Min Age</label>
        <input type="number" value={minAge} onChange={(e) => setMinAge(e.target.value)} />

        <label>Max Age</label>
        <input type="number" value={maxAge} onChange={(e) => setMaxAge(e.target.value)} />

        <label>Start Date</label>
        <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />

        <label>End Date</label>
        <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />

        <button onClick={applyFilters}>Apply Filters</button>
        <button onClick={exportPDF}>Export PDF</button>
      </div>

      {/* DASHBOARD */}
      {hasAppliedFilters ? (
        <div className="grid">
          <div>
            <h3>BCVA Trend</h3>
            <LineChart width={400} height={250} data={bcvaTrend}>
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <CartesianGrid strokeDasharray="3 3" />
              <Line type="monotone" dataKey="bcva" />
            </LineChart>
          </div>

          <div>
            <h3>Injection vs BCVA</h3>
            <BarChart width={400} height={250} data={injData}>
              <XAxis dataKey="injections" />
              <YAxis />
              <Tooltip />
              <CartesianGrid strokeDasharray="3 3" />
              <Bar dataKey="avg_bcva" />
            </BarChart>
          </div>

          <div>
            <h3>IRF / SRF</h3>
            <BarChart width={400} height={250} data={fluidData}>
              <XAxis dataKey="type" />
              <YAxis />
              <Tooltip />
              <CartesianGrid strokeDasharray="3 3" />
              <Bar dataKey="count" />
            </BarChart>
          </div>

          <div>
            <h3>Hard Exudates / HRF</h3>
            <BarChart width={400} height={250} data={hardHrfData}>
              <XAxis dataKey="type" />
              <YAxis />
              <Tooltip />
              <CartesianGrid strokeDasharray="3 3" />
              <Bar dataKey="count" />
            </BarChart>
          </div>
        </div>
      ) : (
        <p style={{ marginTop: "2rem" }}>Apply filters and click "Apply Filters" to see the charts.</p>
      )}
    </div>
  );
}

export default App;
