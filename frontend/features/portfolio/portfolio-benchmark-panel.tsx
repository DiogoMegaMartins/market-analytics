"use client";

import { useEffect, useState } from "react";

type Benchmark = {
  id: string; code: string; name: string; currency: string; benchmark_type: string;
  provider: string; methodology: string; source_reference: string | null; is_active: boolean;
};
type Observation = {
  id: string; observation_date: string; index_level: string; currency: string;
  source: string; source_reference: string | null; methodology: string; recorded_at: string;
};
type RelativePerformance = {
  portfolio_twr_percent: string; benchmark_total_return_percent: string;
  relative_return_percentage_points: string; benchmark_start_level: string;
  benchmark_end_level: string; portfolio_coverage_status: string; limitations: string[];
};
type BenchmarkQuality = {
  observation_count: number;
  first_observation_date: string | null;
  last_observation_date: string | null;
  rules: { gap_basis: string; max_gap_days: number; anomaly_threshold_percent: string; anomalies_are_review_only: boolean; source_reference_is_optional: boolean };
  summary: { gap_count: number; anomaly_count: number; provenance_issue_count: number };
  gaps: { from_date: string; to_date: string; elapsed_calendar_days: number; missing_calendar_days: number }[];
  anomalies: { from_date: string; to_date: string; change_percent: string; reason: string }[];
  provenance_issues: { observation_date: string; missing_fields: string[] }[];
};

type Props = {
  companyId: string; portfolioId: string; currency: string;
  request: (path: string, init?: RequestInit) => Promise<unknown>;
};
const dateToday = () => new Date().toISOString().slice(0, 10);
const percent = (value: string) => {
  const number = Number(value);
  return Number.isFinite(number) ? new Intl.NumberFormat("pt-PT", { style: "percent", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(number / 100) : "—";
};

export default function PortfolioBenchmarkPanel({ companyId, portfolioId, currency, request }: Props) {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [benchmarkId, setBenchmarkId] = useState("");
  const [observations, setObservations] = useState<Observation[]>([]);
  const [startDate, setStartDate] = useState(() => { const date = new Date(); date.setUTCFullYear(date.getUTCFullYear() - 1); return date.toISOString().slice(0, 10); });
  const [endDate, setEndDate] = useState(dateToday);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("");
  const [methodology, setMethodology] = useState("Total return index; dividends reinvested");
  const [sourceReference, setSourceReference] = useState("");
  const [observationDate, setObservationDate] = useState(dateToday);
  const [indexLevel, setIndexLevel] = useState("");
  const [source, setSource] = useState("");
  const [observationMethodology, setObservationMethodology] = useState("Official total-return closing level");
  const [observationReference, setObservationReference] = useState("");
  const [result, setResult] = useState<RelativePerformance | null>(null);
  const [quality, setQuality] = useState<BenchmarkQuality | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const base = `/portfolio/companies/${companyId.trim()}`;
  const selected = benchmarks.find(item => item.id === benchmarkId) || null;

  async function loadBenchmarks() {
    const data = await request(`${base}/benchmarks`) as { benchmarks: Benchmark[] };
    setBenchmarks(data.benchmarks);
    if (!data.benchmarks.some(item => item.id === benchmarkId)) setBenchmarkId(data.benchmarks.find(item => item.is_active && item.currency === currency)?.id || "");
  }
  async function loadObservations() {
    if (!benchmarkId) { setObservations([]); return; }
    const data = await request(`${base}/benchmarks/${benchmarkId}/observations?start_date=${startDate}&end_date=${endDate}`) as { observations: Observation[] };
    setObservations(data.observations);
  }
  useEffect(() => {
    if (!companyId.trim()) return;
    let active = true;
    request(`${base}/benchmarks`).then(value => {
      if (!active) return;
      const data = value as { benchmarks: Benchmark[] };
      setBenchmarks(data.benchmarks);
      setBenchmarkId(current => current || data.benchmarks.find(item => item.is_active && item.currency === currency)?.id || "");
    }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : "Não foi possível carregar benchmarks."); });
    return () => { active = false; };
  }, [companyId, currency]);

  useEffect(() => {
    if (!benchmarkId) { setObservations([]); return; }
    let active = true;
    request(`${base}/benchmarks/${benchmarkId}/observations?start_date=${startDate}&end_date=${endDate}`).then(value => {
      if (active) setObservations((value as { observations: Observation[] }).observations);
    }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : "Não foi possível carregar observações."); });
    return () => { active = false; };
  }, [companyId, benchmarkId, startDate, endDate]);

  async function run(action: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível concluir a operação."); }
    finally { setBusy(false); }
  }
  async function createBenchmark() {
    const data = await request(`${base}/benchmarks`, { method: "POST", body: JSON.stringify({
      code: code.trim().toUpperCase(), name: name.trim(), currency, benchmark_type: "TOTAL_RETURN_INDEX",
      provider: provider.trim(), methodology: methodology.trim(), source_reference: sourceReference.trim() || null,
    }) }) as Benchmark;
    setCode(""); setName(""); setProvider(""); setSourceReference("");
    await loadBenchmarks(); setBenchmarkId(data.id); setNotice("Benchmark criado.");
  }
  async function addObservation() {
    if (!benchmarkId) throw new Error("Seleciona um benchmark.");
    await request(`${base}/benchmarks/${benchmarkId}/observations`, { method: "POST", body: JSON.stringify({
      observation_date: observationDate, index_level: indexLevel, currency,
      source: source.trim(), source_reference: observationReference.trim() || null,
      methodology: observationMethodology.trim(),
    }) });
    setIndexLevel(""); setObservationReference("");
    await loadObservations(); setNotice("Observação registada; o histórico é append-only.");
  }
  async function calculate() {
    if (!benchmarkId) throw new Error("Seleciona um benchmark.");
    const query = new URLSearchParams({ benchmark_id: benchmarkId, start_date: startDate, end_date: endDate });
    const data = await request(`${base}/portfolios/${portfolioId}/performance/benchmark?${query}`) as RelativePerformance;
    setResult(data);
  }

  async function inspectQuality() {
    if (!benchmarkId) throw new Error("Seleciona um benchmark.");
    const query = new URLSearchParams({ start_date: startDate, end_date: endDate });
    const data = await request(`${base}/benchmarks/${benchmarkId}/quality?${query}`) as BenchmarkQuality;
    setQuality(data);
  }

  return <section className="panel">
    <div className="panel-title"><div><h2>Benchmarks e performance relativa</h2><p>Comparação TWR vs. índice total return na mesma moeda e nas mesmas datas de fronteira.</p></div><span className="count-pill">Total return</span></div>
    {error && <div className="notice warning" role="alert">{error}</div>}
    {notice && <div className="notice success" role="status">{notice}</div>}
    <label className="field portfolio-select"><span>Benchmark ({currency})</span><select value={benchmarkId} onChange={event => { setBenchmarkId(event.target.value); setResult(null); setQuality(null); }}><option value="">Selecionar benchmark</option>{benchmarks.map(item => <option key={item.id} value={item.id}>{item.code} · {item.name} · {item.currency}{!item.is_active ? " · inativo" : ""}</option>)}</select></label>
    {selected && <div className="portfolio-meta"><strong>{selected.name}</strong><span>{selected.provider}</span><span>{selected.methodology}</span><span>{selected.currency}</span></div>}
    <details className="portfolio-create">
      <summary>Registar novo benchmark</summary>
      <div className="grid-two">
        <label className="field"><span>Código</span><input value={code} onChange={event => setCode(event.target.value.toUpperCase())} placeholder="Ex.: SP500TR" /></label>
        <label className="field"><span>Nome</span><input value={name} onChange={event => setName(event.target.value)} placeholder="S&P 500 Total Return" /></label>
        <label className="field"><span>Fornecedor / origem</span><input value={provider} onChange={event => setProvider(event.target.value)} /></label>
        <label className="field"><span>Referência da fonte (opcional)</span><input value={sourceReference} onChange={event => setSourceReference(event.target.value)} /></label>
      </div>
      <label className="field portfolio-notes"><span>Metodologia</span><input value={methodology} onChange={event => setMethodology(event.target.value)} /></label>
      <p className="muted small">Só são aceites índices de retorno total com dividendos reinvestidos. A moeda é herdada da carteira ({currency}); não existe conversão FX.</p>
      <button disabled={busy || !code.trim() || !name.trim() || !provider.trim() || !methodology.trim()} onClick={() => void run(createBenchmark)}>Criar benchmark</button>
    </details>
    {selected && <>
      <div className="panel-title"><div><h3>Observações do índice</h3><p>Introduz níveis publicados pela fonte. Datas duplicadas são rejeitadas e os registos não podem ser editados.</p></div><span className="count-pill">{observations.length} observações</span></div>
      <div className="panel-title"><div><h3>Qualidade dos dados</h3><p>Deteção de intervalos longos, variações invulgares e metadados de proveniência em falta. Os alertas não alteram os dados históricos.</p></div></div>
      <button disabled={busy || !benchmarkId} onClick={() => void run(inspectQuality)}>{busy ? "A analisar…" : "Analisar qualidade"}</button>
      {quality && <>
        <div className="portfolio-kpis portfolio-performance-kpis">
          <article><span>Intervalos longos</span><strong>{quality.summary.gap_count}</strong><small>Base: dias de calendário · limite {quality.rules.max_gap_days} dias</small></article>
          <article><span>Variações para revisão</span><strong>{quality.summary.anomaly_count}</strong><small>Limite absoluto {quality.rules.anomaly_threshold_percent}%</small></article>
          <article><span>Problemas de proveniência</span><strong>{quality.summary.provenance_issue_count}</strong><small>Fonte ou metodologia em falta</small></article>
        </div>
        {quality.gaps.length > 0 && <div className="table-scroll"><table className="valuation-table"><thead><tr><th>Intervalo</th><th>Dias decorridos</th><th>Dias sem observação</th></tr></thead><tbody>{quality.gaps.map(item => <tr key={`${item.from_date}-${item.to_date}`}><td>{item.from_date} → {item.to_date}</td><td>{item.elapsed_calendar_days}</td><td>{item.missing_calendar_days}</td></tr>)}</tbody></table></div>}
        {quality.anomalies.length > 0 && <div className="table-scroll"><table className="valuation-table"><thead><tr><th>Período</th><th>Variação</th><th>Estado</th></tr></thead><tbody>{quality.anomalies.map(item => <tr key={`${item.from_date}-${item.to_date}`}><td>{item.from_date} → {item.to_date}</td><td>{Number(item.change_percent).toFixed(2)}%</td><td>Requer revisão</td></tr>)}</tbody></table></div>}
        {quality.provenance_issues.length > 0 && <div className="table-scroll"><table className="valuation-table"><thead><tr><th>Data</th><th>Metadados em falta</th></tr></thead><tbody>{quality.provenance_issues.map(item => <tr key={item.observation_date}><td>{item.observation_date}</td><td>{item.missing_fields.join(", ")}</td></tr>)}</tbody></table></div>}
        {quality.summary.gap_count + quality.summary.anomaly_count + quality.summary.provenance_issue_count === 0 && <p className="notice success" role="status">Não foram detetados problemas segundo as regras aplicadas.</p>}
        <p className="muted small">Análise de {quality.observation_count} observações entre {quality.first_observation_date || "—"} e {quality.last_observation_date || "—"}. As lacunas usam dias de calendário, não um calendário de sessões bolsistas. As anomalias são apenas sinalizações para revisão.</p>
      </>}

      <div className="grid-two">
        <label className="field"><span>Data da observação</span><input type="date" value={observationDate} onChange={event => setObservationDate(event.target.value)} /></label>
        <label className="field"><span>Nível do índice</span><input type="number" min="0.0000000001" step="any" value={indexLevel} onChange={event => setIndexLevel(event.target.value)} placeholder="Ex.: 125.438" /></label>
        <label className="field"><span>Fonte</span><input value={source} onChange={event => setSource(event.target.value)} placeholder="Fornecedor / documento" /></label>
        <label className="field"><span>Referência (opcional)</span><input value={observationReference} onChange={event => setObservationReference(event.target.value)} /></label>
      </div>
      <label className="field portfolio-notes"><span>Metodologia / convenção</span><input value={observationMethodology} onChange={event => setObservationMethodology(event.target.value)} /></label>
      <button disabled={busy || !indexLevel || Number(indexLevel) <= 0 || !source.trim() || !observationMethodology.trim()} onClick={() => void run(addObservation)}>Adicionar observação</button>
      <div className="table-scroll"><table className="valuation-table"><thead><tr><th>Data</th><th>Nível</th><th>Moeda</th><th>Fonte</th><th>Metodologia</th></tr></thead><tbody>{observations.length ? observations.map(item => <tr key={item.id}><td>{item.observation_date}</td><td>{item.index_level}</td><td>{item.currency}</td><td>{item.source}{item.source_reference && <small className="portfolio-id">{item.source_reference}</small>}</td><td>{item.methodology}</td></tr>) : <tr><td colSpan={5}>Sem observações neste intervalo.</td></tr>}</tbody></table></div>
    </>}
    <div className="panel-title"><div><h3>Comparação de performance</h3><p>Exige observações exatas do benchmark no início e no fim do período, além de cobertura TWR completa.</p></div></div>
    <div className="toolbar portfolio-performance-filters">
      <label className="field"><span>Data inicial</span><input type="date" value={startDate} max={endDate} onChange={event => { setStartDate(event.target.value); setResult(null); }} /></label>
      <label className="field"><span>Data final</span><input type="date" value={endDate} min={startDate} onChange={event => { setEndDate(event.target.value); setResult(null); }} /></label>
      <button disabled={busy || !benchmarkId || !portfolioId || endDate <= startDate} onClick={() => void run(calculate)}>{busy ? "A processar…" : "Calcular performance relativa"}</button>
    </div>
    {result && <div className="portfolio-kpis portfolio-performance-kpis">
      <article><span>Retorno TWR da carteira</span><strong>{percent(result.portfolio_twr_percent)}</strong><small>{result.portfolio_coverage_status}</small></article>
      <article><span>Retorno total do benchmark</span><strong>{percent(result.benchmark_total_return_percent)}</strong><small>Nível inicial {result.benchmark_start_level} · final {result.benchmark_end_level}</small></article>
      <article><span>Excesso de retorno</span><strong>{percent(result.relative_return_percentage_points)}</strong><small>Diferença em pontos percentuais</small></article>
    </div>}
    {result && <details className="context-details"><summary>Metodologia e limitações</summary><ul>{result.limitations.map(item => <li key={item}>{item}</li>)}</ul></details>}
    <p className="muted small">Os dados são introduzidos manualmente e não são verificados de forma independente. Não há interpolação, estimativa de observações em falta ou conversão cambial.</p>
  </section>;
}
