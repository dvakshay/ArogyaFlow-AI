import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import axios from "axios";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BrainCircuit,
  Building2,
  ChevronRight,
  CircleDot,
  HeartPulse,
  LayoutDashboard,
  MapPinned,
  Menu,
  Package,
  RefreshCw,
  ShieldCheck,
  Siren,
  Sparkles,
  Truck,
  Users,
  X,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// @ts-expect-error CSS is loaded by the bundler; TypeScript may not have CSS module declarations.
import "./styles.css";

const API = "http://127.0.0.1:8000";

type Summary = {
  phcs: number;
  critical: number;
  high_risk: number;
  watch: number;
  stable: number;
  avg_utilization: number;
  beds_available: number;
};

type PHC = {
  phc_id: string;
  district: string;
  state: string;
  latitude: number;
  longitude: number;
  beds: number;
  staff: number;
  utilization: number;
  avg_stock_days: number;
  risk: number;
  status: string;
  reason: string;
};

type Medicine = {
  medicine: string;
  stock: number;
  daily_demand: number;
  days_cover: number;
  forecast_7d: number;
  risk: number;
  status: string;
};

type Recommendation = {
  from_phc: string;
  from_district: string;
  to_phc: string;
  to_district: string;
  medicine: string;
  quantity: number;
  priority: string;
  reason: string;
};

type Forecast = {
  history: number[];
  forecast: number[];
  total_forecast: number;
};

function App() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [phcs, setPhcs] = useState<PHC[]>([]);
  const [medicines, setMedicines] = useState<Medicine[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>(
    []
  );
  const [forecast, setForecast] = useState<Forecast | null>(null);

  const [active, setActive] = useState("Overview");
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [simulation, setSimulation] = useState<any>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);

      const [
        summaryRes,
        phcRes,
        medicineRes,
        recommendationRes,
        forecastRes,
      ] = await Promise.all([
        axios.get(`${API}/api/summary`),
        axios.get(`${API}/api/phcs`),
        axios.get(`${API}/api/medicines`),
        axios.get(`${API}/api/recommendations`),
        axios.get(`${API}/api/forecast/PHC-001`),
      ]);

      setSummary(summaryRes.data);
      setPhcs(phcRes.data);
      setMedicines(medicineRes.data);
      setRecommendations(recommendationRes.data);
      setForecast(forecastRes.data);
    } catch (error) {
      console.error("Failed to load ArogyaFlow data", error);
    } finally {
      setLoading(false);
    }
  }

  async function runSimulation() {
    try {
      setSimulating(true);

      const response = await axios.post(`${API}/api/simulate`, {
        outbreak: true,
        demand_multiplier: 1.35,
      });

      setSimulation(response.data);
      setActive("Simulation");
    } catch (error) {
      console.error(error);
    } finally {
      setSimulating(false);
    }
  }

  const chartData = useMemo(() => {
    if (!forecast) return [];

    return forecast.history.map((value, index) => ({
      day: `D-${13 - index}`,
      demand: value,
    }));
  }, [forecast]);

  const forecastData = useMemo(() => {
    if (!forecast) return [];

    return forecast.forecast.map((value, index) => ({
      day: `D+${index + 1}`,
      demand: value,
    }));
  }, [forecast]);

  const criticalPHCs = phcs.filter((p) => p.risk >= 75);
  const highRiskPHCs = phcs.filter((p) => p.risk >= 50 && p.risk < 75);

  const navigation = [
    { label: "Overview", icon: LayoutDashboard },
    { label: "PHC Intelligence", icon: Building2 },
    { label: "Medicines", icon: Package },
    { label: "Redistribution", icon: Truck },
    { label: "Simulation", icon: Siren },
  ];

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <HeartPulse size={23} />
          </div>
          <div>
            <div className="brand-name">ArogyaFlow</div>
            <div className="brand-subtitle">AI RESILIENCE NETWORK</div>
          </div>
          <button
            className="mobile-close"
            onClick={() => setMobileOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        <div className="sidebar-section">
          <span>COMMAND CENTER</span>

          {navigation.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.label}
                className={`nav-item ${
                  active === item.label ? "active" : ""
                }`}
                onClick={() => {
                  setActive(item.label);
                  setMobileOpen(false);
                }}
              >
                <Icon size={18} />
                <span>{item.label}</span>
                {active === item.label && <ChevronRight size={15} />}
              </button>
            );
          })}
        </div>

        <div className="sidebar-bottom">
          <div className="ai-card">
            <div className="ai-icon">
              <BrainCircuit size={18} />
            </div>
            <div>
              <strong>AI Engine</strong>
              <span>Predictive models active</span>
            </div>
            <div className="pulse-dot" />
          </div>

          <div className="version">
            AROGYAFLOW AI · MVP 1.0
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setMobileOpen(true)}
          >
            <Menu size={22} />
          </button>

          <div>
            <div className="breadcrumb">
              HEALTH RESOURCE NETWORK
              <ChevronRight size={13} />
              {active.toUpperCase()}
            </div>
          </div>

          <div className="topbar-actions">
            <div className="live-status">
              <span className="live-dot" />
              SYSTEM OPERATIONAL
            </div>

            <button className="icon-button" onClick={loadData}>
              <RefreshCw size={17} />
            </button>
          </div>
        </header>

        <div className="content">
          {active === "Overview" && (
            <>
              <section className="hero">
                <div>
                  <div className="eyebrow">
                    <Sparkles size={14} />
                    PREDICTIVE HEALTH INTELLIGENCE
                  </div>

                  <h1>
                    National Health
                    <br />
                    Resource <span>Command Center</span>
                  </h1>

                  <p>
                    AI-powered visibility across Primary Health Centres,
                    predicting resource shortages before they become
                    emergencies.
                  </p>
                </div>

                <button className="simulation-button" onClick={runSimulation}>
                  <Siren size={18} />
                  Run Emergency Simulation
                </button>
              </section>

              <section className="metrics-grid">
                <MetricCard
                  label="PHCs MONITORED"
                  value={summary?.phcs ?? "--"}
                  icon={<Building2 />}
                  trend="+12.4%"
                  trendUp
                />

                <MetricCard
                  label="CRITICAL FACILITIES"
                  value={summary?.critical ?? "--"}
                  icon={<AlertTriangle />}
                  danger
                  trend={
                    summary?.critical
                      ? `${summary.critical} require action`
                      : "No critical alerts"
                  }
                />

                <MetricCard
                  label="AVAILABLE BEDS"
                  value={summary?.beds_available ?? "--"}
                  icon={<Activity />}
                  trend="Network capacity"
                  trendUp
                />

                <MetricCard
                  label="AVG. UTILIZATION"
                  value={`${summary?.avg_utilization ?? "--"}%`}
                  icon={<Users />}
                  trend="Live network average"
                />
              </section>

              <section className="dashboard-grid">
                <div className="panel large-panel">
                  <div className="panel-header">
                    <div>
                      <span className="panel-kicker">
                        DEMAND INTELLIGENCE
                      </span>
                      <h2>Medicine demand trajectory</h2>
                    </div>

                    <div className="chart-legend">
                      <span>
                        <i className="legend-history" />
                        Historical
                      </span>
                      <span>
                        <i className="legend-forecast" />
                        AI Forecast
                      </span>
                    </div>
                  </div>

                  <div className="chart-wrapper">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart
                        data={[
                          ...chartData,
                          ...forecastData,
                        ]}
                      >
                        <defs>
                          <linearGradient
                            id="demandGradient"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="0%"
                              stopColor="#36d6a0"
                              stopOpacity={0.28}
                            />
                            <stop
                              offset="100%"
                              stopColor="#36d6a0"
                              stopOpacity={0}
                            />
                          </linearGradient>
                        </defs>

                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="#24313c"
                          vertical={false}
                        />

                        <XAxis
                          dataKey="day"
                          stroke="#657482"
                          tickLine={false}
                          axisLine={false}
                        />

                        <YAxis
                          stroke="#657482"
                          tickLine={false}
                          axisLine={false}
                        />

                        <Tooltip
                          contentStyle={{
                            background: "#10171d",
                            border: "1px solid #293842",
                            borderRadius: 10,
                            color: "#fff",
                          }}
                        />

                        <Area
                          type="monotone"
                          dataKey="demand"
                          stroke="#36d6a0"
                          strokeWidth={2}
                          fill="url(#demandGradient)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="panel risk-panel">
                  <div className="panel-header">
                    <div>
                      <span className="panel-kicker">
                        NETWORK STATUS
                      </span>
                      <h2>Risk distribution</h2>
                    </div>
                  </div>

                  <RiskDistribution summary={summary} />

                  <div className="risk-note">
                    <ShieldCheck size={18} />
                    <div>
                      <strong>Network resilience</strong>
                      <span>
                        AI is continuously evaluating stock,
                        utilization and staffing pressure.
                      </span>
                    </div>
                  </div>
                </div>
              </section>

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <span className="panel-kicker">
                      PRIORITY MONITORING
                    </span>
                    <h2>Facilities requiring attention</h2>
                  </div>

                  <button
                    className="text-button"
                    onClick={() => setActive("PHC Intelligence")}
                  >
                    View all <ArrowUpRight size={15} />
                  </button>
                </div>

                <PHCTable data={[...criticalPHCs, ...highRiskPHCs].slice(0, 6)} />
              </section>
            </>
          )}

          {active === "PHC Intelligence" && (
            <section className="page-section">
              <PageTitle
                eyebrow="PHC INTELLIGENCE"
                title="Facility risk landscape"
                description="Predictive operational risk across the PHC network."
              />

              <section className="panel">
                <PHCTable data={phcs} />
              </section>
            </section>
          )}

          {active === "Medicines" && (
            <section className="page-section">
              <PageTitle
                eyebrow="MEDICINE INTELLIGENCE"
                title="Supply & demand monitoring"
                description="AI-assisted demand forecasts and stock-out risk detection."
              />

              <div className="medicine-grid">
                {medicines.map((medicine) => (
                  <MedicineCard
                    key={medicine.medicine}
                    medicine={medicine}
                  />
                ))}
              </div>

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <span className="panel-kicker">
                      STOCK-OUT WATCH
                    </span>
                    <h2>Medicines requiring attention</h2>
                  </div>
                </div>

                <div className="stockout-list">
                  {medicines
                    .filter((m) => m.risk >= 50)
                    .map((medicine) => (
                      <div className="stockout-row" key={medicine.medicine}>
                        <div className="medicine-icon">
                          <Package size={18} />
                        </div>

                        <div className="stockout-name">
                          <strong>{medicine.medicine}</strong>
                          <span>
                            {medicine.days_cover} days of cover
                          </span>
                        </div>

                        <div className="stockout-number">
                          {medicine.stock.toLocaleString()}
                          <span>units</span>
                        </div>

                        <StatusBadge status={medicine.status} />
                      </div>
                    ))}
                </div>
              </section>
            </section>
          )}

          {active === "Redistribution" && (
            <section className="page-section">
              <PageTitle
                eyebrow="RESOURCE OPTIMIZATION"
                title="AI redistribution planner"
                description="Recommended resource transfers between lower-risk and vulnerable facilities."
              />

              <div className="recommendation-banner">
                <div className="banner-icon">
                  <BrainCircuit size={24} />
                </div>

                <div>
                  <strong>AI-generated action plan</strong>
                  <span>
                    Recommendations prioritize critical facilities while
                    preserving donor capacity.
                  </span>
                </div>

                <div className="banner-count">
                  {recommendations.length}
                  <span>actions</span>
                </div>
              </div>

              <section className="recommendation-grid">
                {recommendations.map((item, index) => (
                  <RecommendationCard
                    key={`${item.from_phc}-${item.to_phc}-${index}`}
                    item={item}
                  />
                ))}
              </section>
            </section>
          )}

          {active === "Simulation" && (
            <section className="page-section">
              <PageTitle
                eyebrow="EMERGENCY RESPONSE"
                title="Outbreak impact simulation"
                description="Simulate demand pressure and observe how the network responds."
              />

              {!simulation ? (
                <div className="simulation-empty">
                  <div className="simulation-icon">
                    <Siren size={34} />
                  </div>

                  <h2>Ready to simulate an emergency</h2>

                  <p>
                    Simulate a 35% increase in healthcare demand and
                    identify vulnerable PHCs before stock-outs occur.
                  </p>

                  <button
                    className="simulation-button"
                    onClick={runSimulation}
                    disabled={simulating}
                  >
                    <Siren size={18} />
                    {simulating
                      ? "Running simulation..."
                      : "Run Simulation"}
                  </button>
                </div>
              ) : (
                <>
                  <div className="emergency-banner">
                    <div className="emergency-icon">
                      <Siren size={23} />
                    </div>

                    <div>
                      <span>SIMULATION ACTIVE</span>
                      <strong>
                        Demand increased by{" "}
                        {Math.round(
                          (simulation.demand_multiplier - 1) * 100
                        )}
                        %
                      </strong>
                    </div>
                  </div>

                  <div className="metrics-grid">
                    <MetricCard
                      label="CRITICAL PHCs"
                      value={simulation.critical_count}
                      icon={<AlertTriangle />}
                      danger
                      trend="Immediate intervention"
                    />

                    <MetricCard
                      label="STOCK-OUT RISKS"
                      value={simulation.stockout_risks.length}
                      icon={<Package />}
                      danger
                      trend="Projected shortages"
                    />

                    <MetricCard
                      label="DEMAND MULTIPLIER"
                      value={`${Math.round(
                        simulation.demand_multiplier * 100
                      )}%`}
                      icon={<ArrowUpRight />}
                      trend="Emergency scenario"
                    />

                    <MetricCard
                      label="AI RESPONSE"
                      value="READY"
                      icon={<BrainCircuit />}
                      trend="Redistribution available"
                      trendUp
                    />
                  </div>

                  <section className="panel">
                    <div className="panel-header">
                      <div>
                        <span className="panel-kicker">
                          CRITICAL FACILITIES
                        </span>
                        <h2>Priority response queue</h2>
                      </div>
                    </div>

                    <PHCTable
                      data={simulation.critical_phcs}
                    />
                  </section>
                </>
              )}
            </section>
          )}

          <footer>
            <span>AROGYAFLOW AI</span>
            <span>Predictive Health Resource Resilience Platform</span>
            <span>Hackathon MVP · Synthetic Data</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon,
  trend,
  trendUp,
  danger,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: string;
  trendUp?: boolean;
  danger?: boolean;
}) {
  return (
    <div className={`metric-card ${danger ? "danger" : ""}`}>
      <div className="metric-top">
        <span>{label}</span>
        <div className="metric-icon">{icon}</div>
      </div>

      <strong>{value}</strong>

      {trend && (
        <div className={`metric-trend ${trendUp ? "up" : ""}`}>
          {trendUp ? (
            <ArrowUpRight size={14} />
          ) : danger ? (
            <AlertTriangle size={14} />
          ) : (
            <CircleDot size={12} />
          )}

          {trend}
        </div>
      )}
    </div>
  );
}

function RiskDistribution({
  summary,
}: {
  summary: Summary | null;
}) {
  const total = summary?.phcs || 1;

  const values = [
    {
      label: "Critical",
      value: summary?.critical || 0,
      className: "critical",
    },
    {
      label: "High",
      value: summary?.high_risk || 0,
      className: "high",
    },
    {
      label: "Watch",
      value: summary?.watch || 0,
      className: "watch",
    },
    {
      label: "Stable",
      value: summary?.stable || 0,
      className: "stable",
    },
  ];

  return (
    <div className="risk-distribution">
      <div className="risk-ring">
        <div>
          <strong>{summary?.stable || 0}</strong>
          <span>stable</span>
        </div>
      </div>

      <div className="risk-legend">
        {values.map((item) => (
          <div className="risk-row" key={item.label}>
            <span>
              <i className={`risk-dot ${item.className}`} />
              {item.label}
            </span>

            <strong>{item.value}</strong>

            <small>
              {Math.round((item.value / total) * 100)}%
            </small>
          </div>
        ))}
      </div>
    </div>
  );
}

function PHCTable({ data }: { data: PHC[] }) {
  if (!data.length) {
    return (
      <div className="empty-table">
        No facilities match the current filter.
      </div>
    );
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>FACILITY</th>
            <th>LOCATION</th>
            <th>UTILIZATION</th>
            <th>STOCK COVER</th>
            <th>RISK</th>
            <th>STATUS</th>
          </tr>
        </thead>

        <tbody>
          {data.map((phc) => (
            <tr key={phc.phc_id}>
              <td>
                <div className="facility-cell">
                  <div className="facility-icon">
                    <Building2 size={15} />
                  </div>
                  <div>
                    <strong>{phc.phc_id}</strong>
                    <span>{phc.beds} beds</span>
                  </div>
                </div>
              </td>

              <td>
                <div className="location-cell">
                  <MapPinned size={14} />
                  {phc.district}, {phc.state}
                </div>
              </td>

              <td>
                <div className="progress-cell">
                  <div className="progress">
                    <span
                      style={{
                        width: `${Math.min(
                          phc.utilization,
                          100
                        )}%`,
                      }}
                    />
                  </div>
                  {phc.utilization}%
                </div>
              </td>

              <td>
                <strong>{phc.avg_stock_days}d</strong>
              </td>

              <td>
                <strong
                  className={
                    phc.risk >= 75
                      ? "risk-critical"
                      : phc.risk >= 50
                      ? "risk-high"
                      : "risk-normal"
                  }
                >
                  {phc.risk}
                </strong>
              </td>

              <td>
                <StatusBadge status={phc.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();

  return (
    <span className={`status-badge ${normalized}`}>
      <span />
      {status}
    </span>
  );
}

function MedicineCard({
  medicine,
}: {
  medicine: Medicine;
}) {
  return (
    <div className="medicine-card">
      <div className="medicine-card-top">
        <div className="medicine-icon">
          <Package size={18} />
        </div>

        <StatusBadge status={medicine.status} />
      </div>

      <h3>{medicine.medicine}</h3>

      <div className="medicine-value">
        {medicine.stock.toLocaleString()}
        <span>units</span>
      </div>

      <div className="medicine-stats">
        <div>
          <span>Daily demand</span>
          <strong>
            {medicine.daily_demand.toFixed(0)}
          </strong>
        </div>

        <div>
          <span>Cover</span>
          <strong>{medicine.days_cover}d</strong>
        </div>

        <div>
          <span>7d forecast</span>
          <strong>
            {medicine.forecast_7d.toLocaleString()}
          </strong>
        </div>
      </div>

      <div className="medicine-risk">
        <div>
          <span>Stock-out risk</span>
          <strong>{medicine.risk}%</strong>
        </div>

        <div className="risk-progress">
          <span
            style={{
              width: `${medicine.risk}%`,
            }}
          />
        </div>
      </div>
    </div>
  );
}

function RecommendationCard({
  item,
}: {
  item: Recommendation;
}) {
  return (
    <div className="recommendation-card">
      <div className="recommendation-head">
        <span className="priority-badge">
          {item.priority}
        </span>
        <Truck size={19} />
      </div>

      <div className="transfer-flow">
        <div>
          <span>SOURCE</span>
          <strong>{item.from_phc}</strong>
          <small>{item.from_district}</small>
        </div>

        <div className="transfer-arrow">
          <ArrowDownRight size={22} />
        </div>

        <div>
          <span>DESTINATION</span>
          <strong>{item.to_phc}</strong>
          <small>{item.to_district}</small>
        </div>
      </div>

      <div className="transfer-detail">
        <span>{item.medicine}</span>
        <strong>
          {item.quantity.toLocaleString()} units
        </strong>
      </div>

      <p>{item.reason}</p>
    </div>
  );
}

function PageTitle({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <section className="page-title">
      <div className="eyebrow">
        <Sparkles size={14} />
        {eyebrow}
      </div>

      <h1>{title}</h1>

      <p>{description}</p>
    </section>
  );
}

ReactDOM.createRoot(
  document.getElementById("root")!
).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);