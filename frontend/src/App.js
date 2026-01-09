import { useEffect, useState } from "react";
import {
  LineChart, Line,
  BarChart, Bar,
  XAxis, YAxis,
  Tooltip, CartesianGrid
} from "recharts";
import "./App.css";

function App() {
  // ---------------- DATA STATE ----------------
  const [bcvaTrend, setBcvaTrend] = useState([]);
  const [injData, setInjData] = useState([]);
  const [fluidData, setFluidData] = useState([]);
  const [hardHrfData, setHardHrfData] = useState([]);

  // ---------------- FILTER STATE ----------------
  const [diagnosis, setDiagnosis] = useState("");
  const [minAge, setMinAge] = useState("");
  const [maxAge, setMaxAge] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  // ---------------- FETCH BCVA WITH FILTERS ----------------
  const fetchFilteredBCVA = () => {
    let url = "http://127.0.0.1:8000/analytics/bcva-filtered?";

    if (diagnosis !== "") url += `diagnosis=${diagnosis}&`;
    if (minAge !== "") url += `min_age=${minAge}&`;
    if (maxAge !== "") url += `max_age=${maxAge}&`;
    if (startDate !== "") url += `start_date=${startDate}&`;
    if (endDate !== "") url += `end_date=${endDate}&`;

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error("Backend error");
        return res.json();
      })
      .then((data) => setBcvaTrend(data))
      .catch((err) => console.error("BCVA fetch error:", err));
  };

  // ---------------- FETCH OTHER CHARTS ----------------
  const fetchOtherCharts = () => {
    fetch("http://127.0.0.1:8000/analytics/injection-bcva")
      .then((res) => res.json())
      .then((data) => setInjData(data));

    fetch("http://127.0.0.1:8000/analytics/fluid")
      .then((res) => res.json())
      .then((data) => setFluidData(data));

    fetch("http://127.0.0.1:8000/analytics/hard-hrf")
      .then((res) => res.json())
      .then((data) => setHardHrfData(data));
  };

  // ---------------- EXPORT PDF ----------------
  const exportPDF = () => {
    let url = "http://127.0.0.1:8000/export/pdf?";

    if (diagnosis !== "") url += `diagnosis=${diagnosis}&`;
    if (minAge !== "") url += `min_age=${minAge}&`;
    if (maxAge !== "") url += `max_age=${maxAge}&`;
    if (startDate !== "") url += `start_date=${startDate}&`;
    if (endDate !== "") url += `end_date=${endDate}&`;

    window.open(url, "_blank");
  };

  // ---------------- INITIAL LOAD ----------------
  useEffect(() => {
    fetchFilteredBCVA();
    fetchOtherCharts();
  }, []);

  // ---------------- UI ----------------
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

        <button onClick={fetchFilteredBCVA}>Apply Filters</button>
        <button onClick={exportPDF}>Export PDF</button>
      </div>

      {/* DASHBOARD */}
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
    </div>
  );
}

export default App;
