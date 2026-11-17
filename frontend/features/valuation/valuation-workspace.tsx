"use client";

import { useEffect, useState } from "react";

type ScenarioResult = { value_per_share: string; enterprise_value: string; equity_value: string; warnings: string[] };
type ValuationResult = {
  valuation_version: string;
  currency: string;
  base_year: number;
  scenarios: Record<"BEAR" | "BASE" | "BULL", ScenarioResult>;
  sensitivity: Array<{ wacc: string; values_per_share: Array<{ terminal_growth: string; value_per_share: string | null }> }>;
  analyst_review_required: boolean;
  investment_recommendation: null;
  limitations: string[];
};
type ValuationRow = { id: string; created_at: string; valuation_version: string; method: string; base_year: number; currency: string; result: ValuationResult };
const API = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");
let refreshFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  if (refreshFlight) return refreshFlight;
  refreshFlight = (async () => {
    try {
      const csrf = sessionStorage.getItem("ma_csrf_token") || "";
      const response = await fetch(`${API}/auth/refresh`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
        body: "{}",
      });
      const data = await response.json().catch(() => ({}));
      if (response.ok && data.csrf_token) { sessionStorage.setItem("ma_csrf_token", data.csrf_token); return true; }
      return false;
    } catch { return false; }
    finally { refreshFlight = null; }
  })();
  return refreshFlight;
}

async function api<T>(path: string, init?: RequestInit, retried = false): Promise<T> {
  const csrf = typeof window !== "undefined" ? sessionStorage.getItem("ma_csrf_token") : null;
  const response = await fetch(`${API}${path}`, {
    ...init, credentials: "include", cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.method && init.method !== "GET" && csrf ? { "X-CSRF-Token": csrf } : {}), ...(init?.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401 && !retried && path !== "/auth/refresh") {
    if (await refreshSession()) return api<T>(path, init, true);
    sessionStorage.removeItem("ma_csrf_token");
    window.location.href = "/login";
  }
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Pedido falhou (${response.status})`);
  return data as T;
}

const money = (value: string, currency: string) => {
  const number = Number(value);
  return Number.isFinite(number) ? new Intl.NumberFormat("pt-PT", { style: "currency", currency, maximumFractionDigits: 2 }).format(number) : value;
};

export default function ValuationWorkspace() {
  const [companyId, setCompanyId] = useState("");
  const [payload, setPayload] = useState("");
  const [history, setHistory] = useState<ValuationRow[]>([]);
  const [selected, setSelected] = useState<ValuationRow | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!sessionStorage.getItem("ma_csrf_token")) window.location.href = "/login";
  }, []);

  async function loadHistory() {
    if (!companyId.trim()) throw new Error("Indica primeiro o ID da empresa.");
    const data = await api<{ valuations: ValuationRow[] }>(`/valuation/companies/${companyId.trim()}/history`);
    setHistory(data.valuations);
  }

  async function calculate() {
    if (!companyId.trim()) throw new Error("Indica o ID da empresa.");
    let assumptions: unknown;
    try { assumptions = JSON.parse(payload); }
    catch { throw new Error("O modelo de pressupostos tem de ser JSON válido."); }
    const created = await api<ValuationRow & { result: ValuationResult }>(
      `/valuation/companies/${companyId.trim()}/dcf`,
      { method: "POST", body: JSON.stringify(assumptions) },
    );
    setSelected({ ...created, method: "FCFF_DCF", base_year: created.result.base_year, currency: created.result.currency });
    await loadHistory();
    setNotice("Avaliação calculada e guardada no histórico.");
  }

  async function run(action: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); }
    catch (err) { setError(err instanceof Error ? err.message : "Não foi possível concluir o pedido."); }
    finally { setBusy(false); }
  }

  const result = selected?.result;
  return (
    <main className="workspace-shell">
      <header className="workspace-header">
        <div><p className="eyebrow">MARKET ANALYTICS · VALUATION</p><h1>Valuation Workspace</h1><p className="muted">DCF por FCFF · cenários Bear, Base e Bull · histórico persistente</p></div>
        <a className="back-link" href="/">Início</a>
      </header>

      <section className="panel">
        <div className="panel-title"><div><h2>Nova avaliação DCF</h2><p>Introduz pressupostos explícitos. Não são inferidos nem preenchidos automaticamente.</p></div></div>
        <label className="field"><span>ID da empresa</span><input value={companyId} onChange={e => setCompanyId(e.target.value)} placeholder="UUID da empresa" /></label>
        <label className="field valuation-json"><span>Pressupostos (JSON)</span><textarea value={payload} onChange={e => setPayload(e.target.value)} rows={18} spellCheck={false} placeholder={'{\n  "base_year": 2024,\n  "currency": "USD",\n  "wacc": "0.09",\n  "terminal_growth": "0.025",\n  "net_debt": "100",\n  "diluted_shares": "50",\n  "scenarios": {\n    "BEAR": [{"year": 2025, "revenue": "900", "ebit_margin": "0.18", "tax_rate": "0.25", "da": "35", "capex": "55", "change_nwc": "10"}],\n    "BASE": [{"year": 2025, "revenue": "1000", "ebit_margin": "0.20", "tax_rate": "0.25", "da": "40", "capex": "50", "change_nwc": "10"}],\n    "BULL": [{"year": 2025, "revenue": "1100", "ebit_margin": "0.22", "tax_rate": "0.25", "da": "45", "capex": "48", "change_nwc": "10"}]\n  }\n}'} /></label>
        <p className="muted small">Os valores do exemplo são meramente ilustrativos. Todas as previsões, taxas e dados de capital devem ser validados pelo analista.</p>
        <div className="toolbar bottom-toolbar"><button disabled={busy} onClick={() => void run(calculate)}>{busy ? "A calcular…" : "Calcular e guardar"}</button><button className="secondary" disabled={busy || !companyId.trim()} onClick={() => void run(loadHistory)}>Carregar histórico</button></div>
        {error && <div className="notice error" role="alert">{error}</div>}
        {notice && <div className="notice success" role="status">{notice}</div>}
      </section>

      {result && <section className="panel">
        <div className="panel-title"><div><h2>Resultado da avaliação</h2><p>{result.valuation_version} · ano-base {result.base_year} · {result.currency}</p></div><span className="count-pill">Revisão do analista obrigatória</span></div>
        <div className="valuation-scenarios">
          {(["BEAR", "BASE", "BULL"] as const).map(name => <article className="valuation-scenario" key={name}>
            <span className="detail-label">{name}</span><strong>{money(result.scenarios[name].value_per_share, result.currency)}</strong>
            <small>Valor por ação</small><p>EV: {money(result.scenarios[name].enterprise_value, result.currency)}</p>
            {result.scenarios[name].warnings.map(warning => <small className="valuation-warning" key={warning}>{warning}</small>)}
          </article>)}
        </div>
        <h3 className="valuation-subtitle">Sensibilidade — cenário Base</h3>
        <div className="table-scroll"><table className="valuation-table"><thead><tr><th>WACC \ Crescimento terminal</th>{result.sensitivity[0]?.values_per_share.map(cell => <th key={cell.terminal_growth}>{(Number(cell.terminal_growth) * 100).toFixed(2)}%</th>)}</tr></thead>
          <tbody>{result.sensitivity.map(row => <tr key={row.wacc}><th>{(Number(row.wacc) * 100).toFixed(2)}%</th>{row.values_per_share.map(cell => <td key={cell.terminal_growth}>{cell.value_per_share === null ? "—" : money(cell.value_per_share, result.currency)}</td>)}</tr>)}</tbody></table></div>
        <p className="notice warning">A avaliação é uma ferramenta analítica, não uma recomendação de investimento. Confirma a adequação do método e revê todos os pressupostos, fontes e limitações.</p>
        <details className="context-details"><summary>Limitações do modelo</summary><ul>{result.limitations.map(item => <li key={item}>{item}</li>)}</ul></details>
      </section>}

      <section className="panel">
        <div className="panel-title"><div><h2>Histórico</h2><p>Últimas avaliações guardadas para a empresa indicada.</p></div></div>
        {history.length === 0 ? <p className="empty-state">Ainda não foram carregadas avaliações.</p> : <div className="candidate-list">{history.map(item => <button className="candidate-row" key={item.id} onClick={() => setSelected(item)}><span className="row-main"><strong>{item.method} · {item.base_year}</strong><span>{item.valuation_version} · {new Date(item.created_at).toLocaleString("pt-PT")}</span></span><span>{money(item.result.scenarios.BASE.value_per_share, item.currency)}</span></button>)}</div>}
      </section>
    </main>
  );
}
