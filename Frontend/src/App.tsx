import React, { useEffect, useMemo, useState } from "react";
import Section from "./components/Section";
import ServiceCard from "./components/ServiceCard";
import MetricCard from "./components/MetricCard";
import LogTable from "./components/LogTable";
import ReactECharts from "echarts-for-react";
import { login, getMe, AuthUser } from "./api/auth";
import { clearTokens, getAccessToken, setTokens } from "./api/token";
import { checkService, ServiceStatus } from "./api/health";
import {
  API_BASE,
  BACKEND_HEALTH,
  AI_HEALTH,
  ELASTIC_HEALTH,
  KIBANA_HEALTH,
  LOGSTASH_HEALTH,
  DEFAULT_TIME_RANGE_HOURS
} from "./api/config";
import { getAggregations, searchLogs, Aggregations, LogEntry } from "./api/logs";
import { listAlerts, Alert } from "./api/alerts";
import { listRules, Rule } from "./api/rules";
import { listAnomalies, Anomaly, triggerAnomalyDetection } from "./api/anomalies";

const buildDefaultRange = () => {
  const end = new Date();
  const start = new Date(end.getTime() - DEFAULT_TIME_RANGE_HOURS * 60 * 60 * 1000);
  return {
    start_time: start.toISOString(),
    end_time: end.toISOString()
  };
};

const App = () => {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [emailInput, setEmailInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");

  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [serviceLoading, setServiceLoading] = useState(false);

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logMeta, setLogMeta] = useState({ total: 0, page: 1, page_size: 50, total_pages: 0 });
  const [logError, setLogError] = useState<string | null>(null);
  const [logLoading, setLogLoading] = useState(false);

  const [aggregations, setAggregations] = useState<Aggregations | null>(null);
  const [aggError, setAggError] = useState<string | null>(null);

  const [rules, setRules] = useState<Rule[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [opsError, setOpsError] = useState<string | null>(null);

  const [query, setQuery] = useState({
    ...buildDefaultRange(),
    service: "",
    level: "",
    search: "",
    trace_id: "",
    page: 1,
    page_size: 50
  });

  const levelDistribution = useMemo(() => {
    if (!aggregations?.level_distribution) {
      return [];
    }
    return Object.entries(aggregations.level_distribution).map(([level, count]) => ({
      level,
      count
    }));
  }, [aggregations]);

  const levelPieOption = useMemo(() => {
    return {
      tooltip: { trigger: "item" },
      series: [
        {
          name: "Levels",
          type: "pie",
          radius: ["45%", "75%"],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
          label: { show: false },
          emphasis: {
            label: { show: true, fontSize: 14, fontWeight: "bold" }
          },
          data: levelDistribution.map((item) => ({
            name: item.level,
            value: item.count
          }))
        }
      ]
    };
  }, [levelDistribution]);

  const latencyBarOption = useMemo(() => {
    const items = aggregations?.latency_by_service || [];
    return {
      tooltip: { trigger: "axis" },
      grid: { left: 0, right: 8, top: 20, bottom: 0, containLabel: true },
      xAxis: { type: "value", axisLabel: { formatter: "{value} ms" } },
      yAxis: { type: "category", data: items.map((item) => item.service), inverse: true },
      series: [
        {
          type: "bar",
          data: items.map((item) => item.p99 || 0),
          itemStyle: { color: "#0f766e" },
          barWidth: 16
        }
      ]
    };
  }, [aggregations]);

  const volumeLineOption = useMemo(() => {
    const points = aggregations?.volume_over_time || [];
    return {
      tooltip: { trigger: "axis" },
      grid: { left: 0, right: 8, top: 20, bottom: 0, containLabel: true },
      xAxis: {
        type: "category",
        data: points.map((p) => new Date(p.timestamp).toLocaleTimeString())
      },
      yAxis: { type: "value" },
      series: [
        {
          type: "line",
          smooth: true,
          data: points.map((p) => p.total),
          areaStyle: { color: "rgba(29, 78, 216, 0.2)" },
          lineStyle: { color: "#1d4ed8" },
          symbol: "circle",
          symbolSize: 6
        }
      ]
    };
  }, [aggregations]);

  const refreshServices = async () => {
    setServiceLoading(true);
    const results = await Promise.all([
      checkService("Django API", BACKEND_HEALTH),
      checkService("AI Service", AI_HEALTH),
      checkService("Elasticsearch", ELASTIC_HEALTH),
      checkService("Logstash", LOGSTASH_HEALTH),
      checkService("Kibana", KIBANA_HEALTH)
    ]);
    setServices(results);
    setServiceLoading(false);
  };

  const loadLogs = async () => {
    setLogLoading(true);
    setLogError(null);
    try {
      const result = await searchLogs(query);
      setLogs(result.results || []);
      setLogMeta({
        total: result.total,
        page: result.page,
        page_size: result.page_size,
        total_pages: result.total_pages
      });
    } catch (error) {
      setLogError(error instanceof Error ? error.message : "Log search failed");
      setLogs([]);
    } finally {
      setLogLoading(false);
    }
  };

  const loadAggregations = async () => {
    setAggError(null);
    try {
      const result = await getAggregations(query);
      setAggregations(result);
    } catch (error) {
      setAggError(error instanceof Error ? error.message : "Aggregation query failed");
      setAggregations(null);
    }
  };

  const loadOps = async () => {
    setOpsError(null);
    try {
      const [rulesResponse, alertsResponse, anomaliesResponse] = await Promise.all([
        listRules(),
        listAlerts(),
        listAnomalies()
      ]);
      setRules(rulesResponse || []);
      setAlerts(alertsResponse || []);
      setAnomalies(anomaliesResponse || []);
    } catch (error) {
      setOpsError(error instanceof Error ? error.message : "Operational endpoints unavailable");
    }
  };

  const loadMe = async () => {
    if (!getAccessToken()) {
      setAuthUser(null);
      return;
    }
    try {
      const me = await getMe();
      setAuthUser(me);
    } catch (error) {
      setAuthUser(null);
    }
  };

  useEffect(() => {
    refreshServices();
    loadLogs();
    loadAggregations();
    loadOps();
    loadMe();
  }, []);

  const handleLogin = async () => {
    setAuthError(null);
    setAuthLoading(true);
    try {
      const result = await login(emailInput.trim(), passwordInput);
      setTokens({ access: result.access, refresh: result.refresh });
      setAuthUser(result.user);
      await Promise.all([loadLogs(), loadAggregations(), loadOps()]);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Login failed");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    clearTokens();
    setAuthUser(null);
  };

  const handleQueryChange = (field: string, value: string) => {
    setQuery((prev) => ({ ...prev, [field]: value }));
  };

  const handleSearch = async () => {
    await Promise.all([loadLogs(), loadAggregations()]);
  };

  const handleDetect = async () => {
    try {
      await triggerAnomalyDetection();
      loadOps();
    } catch (error) {
      setOpsError(error instanceof Error ? error.message : "AI detection call failed");
    }
  };

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">Observability Command Center</p>
          <h1>Log Intelligence Platform</h1>
          <p className="lead">
            Unified visibility across ingestion, search, alerting, and anomaly detection. Designed to
            keep every microservice healthy and every incident traceable.
          </p>
          <div className="hero-actions">
            <button className="btn" onClick={refreshServices} disabled={serviceLoading}>
              {serviceLoading ? "Refreshing..." : "Refresh Health"}
            </button>
            <a className="btn ghost" href="#explorer">Jump to Logs</a>
          </div>
        </div>
        <div className="hero-panel">
          <div className="token-box">
            <div>
              <h3>Operator Login</h3>
              <p className="muted">Sign in to unlock rules, alerts, anomalies, and secured logs.</p>
            </div>
            {authUser ? (
              <div className="auth-state">
                <p className="muted">Signed in as</p>
                <h4>{authUser.full_name || authUser.email}</h4>
                <p className="muted small">Role: {authUser.role}</p>
                <button className="btn ghost small" onClick={handleLogout}>Sign out</button>
              </div>
            ) : (
              <div className="token-input">
                <input
                  type="email"
                  value={emailInput}
                  onChange={(event) => setEmailInput(event.target.value)}
                  placeholder="admin@company.com"
                />
                <input
                  type="password"
                  value={passwordInput}
                  onChange={(event) => setPasswordInput(event.target.value)}
                  placeholder="Password"
                />
                <button className="btn small" onClick={handleLogin} disabled={authLoading}>
                  {authLoading ? "Signing in..." : "Sign in"}
                </button>
              </div>
            )}
            {authError ? <p className="notice">{authError}</p> : null}
            <p className="muted small">API base: {API_BASE}</p>
          </div>
        </div>
      </header>

      <main>
        <Section
          id="health"
          title="Service Health"
          subtitle="Live status for every backend, pipeline, and microservice surface."
          actions={
            <span className="muted small">Last refresh: {new Date().toLocaleTimeString()}</span>
          }
        >
          <div className="grid cards">
            {services.map((service) => (
              <ServiceCard key={service.name} service={service} />
            ))}
          </div>
        </Section>

        <Section
          id="insights"
          title="Realtime Signals"
          subtitle="Summaries derived from Elasticsearch aggregations."
        >
          <div className="grid metrics">
            <MetricCard label="Total Logs" value={logMeta.total} hint="Matching query" />
            <MetricCard label="Page" value={`${logMeta.page} / ${logMeta.total_pages || 1}`} />
            <MetricCard label="Top Error" value={aggregations?.top_errors?.[0]?.message || "-"} />
            <MetricCard label="Error Count" value={aggregations?.top_errors?.[0]?.count || 0} />
          </div>
          {aggError ? <div className="notice">{aggError}</div> : null}
          <div className="grid charts">
            <div className="card chart">
              <h3>Level Distribution</h3>
              {levelDistribution.length ? (
                <ReactECharts option={levelPieOption} style={{ height: 260 }} />
              ) : (
                <p className="muted">No aggregation data.</p>
              )}
            </div>
            <div className="card chart">
              <h3>Latency by Service (p99)</h3>
              {aggregations?.latency_by_service?.length ? (
                <ReactECharts option={latencyBarOption} style={{ height: 260 }} />
              ) : (
                <p className="muted">No latency data yet.</p>
              )}
            </div>
          </div>
          <div className="card chart">
            <h3>Log Volume Over Time</h3>
            {aggregations?.volume_over_time?.length ? (
              <ReactECharts option={volumeLineOption} style={{ height: 260 }} />
            ) : (
              <p className="muted">No volume data yet.</p>
            )}
            </div>
          </div>
        </Section>

        <Section
          id="explorer"
          title="Log Explorer"
          subtitle="Filter, trace, and diagnose production traffic."
          actions={
            <button className="btn" onClick={handleSearch} disabled={logLoading}>
              {logLoading ? "Searching..." : "Run Query"}
            </button>
          }
        >
          <div className="card query">
            <div className="form-grid">
              <label>
                Start Time
                <input
                  type="datetime-local"
                  value={query.start_time.slice(0, 16)}
                  onChange={(event) => handleQueryChange("start_time", new Date(event.target.value).toISOString())}
                />
              </label>
              <label>
                End Time
                <input
                  type="datetime-local"
                  value={query.end_time.slice(0, 16)}
                  onChange={(event) => handleQueryChange("end_time", new Date(event.target.value).toISOString())}
                />
              </label>
              <label>
                Service
                <input
                  type="text"
                  value={query.service}
                  onChange={(event) => handleQueryChange("service", event.target.value)}
                  placeholder="billing-api"
                />
              </label>
              <label>
                Level
                <input
                  type="text"
                  value={query.level}
                  onChange={(event) => handleQueryChange("level", event.target.value)}
                  placeholder="ERROR"
                />
              </label>
              <label>
                Search
                <input
                  type="text"
                  value={query.search}
                  onChange={(event) => handleQueryChange("search", event.target.value)}
                  placeholder="timeout"
                />
              </label>
              <label>
                Trace Id
                <input
                  type="text"
                  value={query.trace_id}
                  onChange={(event) => handleQueryChange("trace_id", event.target.value)}
                  placeholder="trace-id"
                />
              </label>
            </div>
          </div>

          {logError ? <div className="notice">{logError}</div> : null}
          <LogTable logs={logs} />
        </Section>

        <Section
          id="ops"
          title="Rules, Alerts, Anomalies"
          subtitle="Operational endpoints wired for end-to-end connectivity."
          actions={
            <button className="btn ghost" onClick={handleDetect}>Trigger AI Detection</button>
          }
        >
          {opsError ? <div className="notice">{opsError}</div> : null}
          <div className="grid ops">
            <div className="card">
              <h3>Active Rules</h3>
              {rules.length ? (
                <div className="list">
                  {rules.map((rule) => (
                    <div key={rule.id || rule.name} className="list-row">
                      <span>{rule.name || "Rule"}</span>
                      <span className="muted">{rule.metric || rule.condition || "metric"}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">No rules returned yet.</p>
              )}
            </div>
            <div className="card">
              <h3>Latest Alerts</h3>
              {alerts.length ? (
                <div className="list">
                  {alerts.map((alert) => (
                    <div key={alert.id || alert.title} className="list-row">
                      <span>{alert.title || alert.message || "Alert"}</span>
                      <span className="muted">{alert.status || "open"}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">No alerts returned yet.</p>
              )}
            </div>
            <div className="card">
              <h3>Anomalies</h3>
              {anomalies.length ? (
                <div className="list">
                  {anomalies.map((anomaly) => (
                    <div key={anomaly.id || anomaly.summary} className="list-row">
                      <span>{anomaly.summary || anomaly.description || "Anomaly"}</span>
                      <span className="muted">Score: {anomaly.score ?? anomaly.anomaly_score ?? "-"}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">No anomalies returned yet.</p>
              )}
            </div>
          </div>
        </Section>
      </main>

      <footer className="footer">
        <p>Log Intelligence Platform - wired to every service surface.</p>
      </footer>
    </div>
  );
};

export default App;
