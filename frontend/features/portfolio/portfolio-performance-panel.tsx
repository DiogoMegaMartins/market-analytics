"use client";

import { useMemo, useState } from "react";

type Subperiod = { start_date: string; end_date: string; start_value: string; end_value: string; return: string };
type TWR = {
  start_date: string; end_date: string; starting_value: string; ending_value: string;
  external_cash_flow_count: number; time_weighted_return: string; time_weighted_return_percent: string;
  coverage_status: string; subperiods: Subperiod[]; limitations: string[];
};
type MWR = {
  start_date: string; end_date: string; starting_value: string; ending_value: string;
  external_cash_flow_count: number; money_weighted_return: string; money_weighted_return_percent: string;
  day_count: string; root_count: number; coverage_status: string; limitations: string[];
};
type ValuationQuality = {
  snapshot_count: number; valuation_date_count: number;
  first_valuation_date: string | null; last_valuation_date: string | null;
  rules: { canonical_selection: string; gap_basis: string; max_gap_days: number; source_reference_is_optional: boolean; findings_are_review_only: boolean };
  summary: { gap_count: number; duplicate_date_count: number; extra_snapshot_count: number; provenance_issue_count: number };
  gaps: { from_date: string; to_date: string; elapsed_calendar_days: number; missing_calendar_days: number }[];
  duplicate_dates: { valuation_date: string; snapshot_count: number; canonical_snapshot_id: string; canonical_recorded_at: string; superseded_snapshot_ids: string[] }[];
  provenance_issues: { valuation_date: string; snapshot_id: string; missing_fields: string[] }[];
  canonical_observations: { valuation_date: string; snapshot_id: string; recorded_at: string; total_value: string }[];
};

type Props = { companyId: string; portfolioId: string; currency: string; request: (path: string) => Promise<unknown> };
const isoDate = (date: Date) => date.toISOString().slice(0, 10);
const defaultStart = () => { const d = new Date(); d.setUTCFullYear(d.getUTCFullYear() - 1); return isoDate(d); };
const percent = (value: string) => {
  const n = Number(value);
  return Number.isFinite(n) ? new Intl.NumberFormat("pt-PT", { style: "percent", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n) : "—";
};
const money = (value: string, currency: string) => {
  const n = Number(value);
  return Number.isFinite(n) ? new Intl.NumberFormat("pt-PT", { style: "currency", currency, maximumFractionDigits: 2 }).format(n) : "—";
};

export default function PortfolioPerformancePanel({ companyId, portfolioId, currency, request }: Props) {
  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(() => isoDate(new Date()));
  const [twr, setTwr] = useState<TWR | null>(null);
  const [mwr, setMwr] = useState<MWR | null>(null);
  const [twrError, setTwrError] = useState("");
  const [mwrError, setMwrError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadedRange, setLoadedRange] = useState("");
  const [quality, setQuality] = useState<ValuationQuality | null>(null);
  const [qualityError, setQualityError] = useState("");
  const [qualityBusy, setQualityBusy] = useState(false);

  async function inspectValuationQuality() {
    setQualityBusy(true); setQualityError(""); setQuality(null);
    const base = `/portfolio/companies/${companyId.trim()}/portfolios/${portfolioId}/valuations/quality`;
    const query = new URLSearchParams({ start_date: startDate, end_date: endDate });
    try { setQuality(await request(`${base}?${query}`) as ValuationQuality); }
    catch (reason) { setQualityError(reason instanceof Error ? reason.message : "Não foi possível analisar as avaliações."); }
    finally { setQualityBusy(false); }
  }


  async function load() {
    setBusy(true); setTwr(null); setMwr(null); setTwrError(""); setMwrError(""); setLoadedRange("");
    const base = `/portfolio/companies/${companyId.trim()}/portfolios/${portfolioId}/performance`;
    const query = `?start_date=${startDate}&end_date=${endDate}`;
    const [twrResult, mwrResult] = await Promise.allSettled([
      request(`${base}/twr${query}`).then(value => value as TWR),
      request(`${base}/mwr${query}`).then(value => value as MWR),
    ]);
    if (twrResult.status === "fulfilled") setTwr(twrResult.value);
    else setTwrError(twrResult.reason instanceof Error ? twrResult.reason.message : "Não foi possível calcular TWR.");
    if (mwrResult.status === "fulfilled") setMwr(mwrResult.value);
    else setMwrError(mwrResult.reason instanceof Error ? mwrResult.reason.message : "Não foi possível calcular XIRR.");
    setLoadedRange(`${startDate} — ${endDate}`);
    setBusy(false);
  }

  const chart = useMemo(() => {
    if (!twr) return null;
    const values = [Number(twr.starting_value), ...twr.subperiods.map(item => Number(item.end_value))].filter(Number.isFinite);
    if (values.length < 2) return null;
    const min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
    const points = values.map((value, index) => ({
      x: 12 + index * (376 / (values.length - 1)),
      y: 112 - ((value - min) / span) * 92,
      value,
    }));
    return { points, polyline: points.map(point => `${point.x},${point.y}`).join(" "), min, max };
  }, [twr]);

  return <section className="panel">
    <div className="panel-title"><div><h2>Performance da carteira</h2><p>TWR e XIRR calculados pela API a partir de valuations e fluxos externos registados.</p></div><span className="count-pill">Read-only</span></div>
    <div className="toolbar portfolio-performance-filters">
      <label className="field"><span>Data inicial</span><input type="date" value={startDate} max={endDate} onChange={event => setStartDate(event.target.value)} /></label>
      <label className="field"><span>Data final</span><input type="date" value={endDate} min={startDate} onChange={event => setEndDate(event.target.value)} /></label>
      <button disabled={busy || !companyId.trim() || !portfolioId || !startDate || !endDate || endDate <= startDate} onClick={() => void load()}>{busy ? "A calcular…" : "Calcular performance"}</button>
    </div>
    {loadedRange && <p className="muted small">Período consultado: {loadedRange} · moeda: {currency}</p>}
    <div className="panel-title"><div><h3>Qualidade das avaliações</h3><p>Auditoria read-only de cobertura, duplicados, seleção canónica e proveniência no período selecionado.</p></div></div>
    <button disabled={qualityBusy || !companyId.trim() || !portfolioId || endDate < startDate} onClick={() => void inspectValuationQuality()}>{qualityBusy ? "A analisar…" : "Analisar qualidade das avaliações"}</button>
    {qualityError && <div className="notice warning" role="alert">{qualityError}</div>}
    {quality && <>
      <div className="portfolio-kpis portfolio-performance-kpis">
        <article><span>Datas com avaliações</span><strong>{quality.valuation_date_count}</strong><small>{quality.snapshot_count} snapshots no total</small></article>
        <article><span>Datas duplicadas</span><strong>{quality.summary.duplicate_date_count}</strong><small>{quality.summary.extra_snapshot_count} snapshots adicionais</small></article>
        <article><span>Intervalos longos</span><strong>{quality.summary.gap_count}</strong><small>Mais de {quality.rules.max_gap_days} dias de calendário</small></article>
        <article><span>Problemas de proveniência</span><strong>{quality.summary.provenance_issue_count}</strong><small>Origem ou metodologia em falta</small></article>
      </div>
      {quality.duplicate_dates.length > 0 && <div className="table-scroll"><table className="valuation-table"><thead><tr><th>Data</th><th>Snapshots</th><th>Snapshot canónico</th><th>Registado em</th></tr></thead><tbody>{quality.duplicate_dates.map(item => <tr key={item.valuation_date}><td>{item.valuation_date}</td><td>{item.snapshot_count}</td><td><code>{item.canonical_snapshot_id}</code></td><td>{item.canonical_recorded_at}</td></tr>)}</tbody></table></div>}
      {quality.gaps.length > 0 && <div className="table-scroll"><table className="valuation-table"><thead><tr><th>Intervalo</th><th>Dias sem observação</th></tr></thead><tbody>{quality.gaps.map(item => <tr key={item.from_date + item.to_date}><td>{item.from_date} → {item.to_date}</td><td>{item.missing_calendar_days}</td></tr>)}</tbody></table></div>}
      {quality.provenance_issues.length > 0 && <div className="table-scroll"><table className="valuation-table"><thead><tr><th>Data</th><th>Snapshot</th><th>Campos em falta</th></tr></thead><tbody>{quality.provenance_issues.map(item => <tr key={item.snapshot_id}><td>{item.valuation_date}</td><td><code>{item.snapshot_id}</code></td><td>{item.missing_fields.join(", ")}</td></tr>)}</tbody></table></div>}
      {quality.summary.gap_count + quality.summary.duplicate_date_count + quality.summary.provenance_issue_count === 0 && <p className="notice success" role="status">Não foram detetados problemas segundo as regras aplicadas.</p>}
      <p className="muted small">Política canónica: {quality.rules.canonical_selection}. Lacunas em dias de calendário; referência da fonte opcional. Alertas apenas para revisão — sem alterações aos snapshots.</p>
    </>}

    {!loadedRange && <p className="empty-state">Seleciona o período e calcula para consultar métricas. Não são estimados valores quando faltam snapshots.</p>}
    {(twr || mwr) && <div className="portfolio-kpis portfolio-performance-kpis">
      <article><span>Time-Weighted Return (TWR)</span><strong>{twr ? percent(twr.time_weighted_return) : "Indisponível"}</strong><small>{twr ? `${twr.external_cash_flow_count} fluxos externos · ${twr.coverage_status}` : "Cobertura insuficiente ou cálculo indisponível"}</small></article>
      <article><span>Money-Weighted Return (XIRR anualizado)</span><strong>{mwr ? percent(mwr.money_weighted_return) : "Indisponível"}</strong><small>{mwr ? `${mwr.external_cash_flow_count} fluxos externos · ACTUAL/365` : "Cobertura insuficiente ou cálculo indisponível"}</small></article>
      <article><span>Valor inicial / final</span><strong>{twr ? money(twr.starting_value, currency) : mwr ? money(mwr.starting_value, currency) : "—"}</strong><small>{twr ? money(twr.ending_value, currency) : mwr ? money(mwr.ending_value, currency) : "Sem NAV confirmado"}</small></article>
      <article><span>Estado da cobertura</span><strong>{twr?.coverage_status === "COMPLETE" && mwr?.coverage_status === "COMPLETE" ? "Completa" : "Parcial"}</strong><small>Os resultados dependem dos snapshots fornecidos</small></article>
    </div>}
    {twrError && <div className="notice warning" role="status"><strong>TWR indisponível:</strong> {twrError}</div>}
    {mwrError && <div className="notice warning" role="status"><strong>XIRR indisponível:</strong> {mwrError}</div>}
    {chart && <div className="portfolio-performance-chart">
      <div className="panel-title"><div><h3>Evolução do NAV observado</h3><p>Valores inicial e finais dos subperíodos usados no cálculo TWR; não é uma interpolação diária.</p></div></div>
      <div className="portfolio-chart-wrap">
        <svg viewBox="0 0 400 132" role="img" aria-label="Gráfico dos valores NAV observados nos limites dos subperíodos TWR">
          <line x1="12" y1="112" x2="388" y2="112" stroke="currentColor" opacity=".18" />
          <polyline points={chart.polyline} fill="none" stroke="#24658a" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
          {chart.points.map((point, index) => <circle key={index} cx={point.x} cy={point.y} r="3.5" fill="#24658a"><title>{money(String(point.value), currency)}</title></circle>)}
        </svg>
        <div className="portfolio-chart-labels"><span>{money(String(chart.min), currency)}</span><span>{money(String(chart.max), currency)}</span></div>
      </div>
    </div>}
    {(twr || mwr) && <details className="context-details portfolio-performance-limitations"><summary>Metodologia e limitações</summary>
      <ul>{[...(twr?.limitations || []), ...(mwr?.limitations || [])].filter((item, index, all) => all.indexOf(item) === index).map(item => <li key={item}>{item}</li>)}</ul>
      {twr && <p className="muted small">TWR: fluxos externos assumidos no início da data de negociação; exige valuation na data de cada fluxo externo não nulo.</p>}
      {mwr && <p className="muted small">XIRR: retorno anualizado do ponto de vista do investidor; múltiplas raízes ou ausência de raiz são rejeitadas.</p>}
    </details>}
  </section>;
}
