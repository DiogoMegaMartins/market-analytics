"use client";

import { useEffect, useMemo, useState } from "react";

type Portfolio = { id: string; company_id: string; name: string; base_currency: string; status: string; created_at: string };
type Transaction = { id: string; transaction_type: string; trade_date: string; settlement_date: string | null; asset_id: string | null; quantity: string | null; unit_price: string | null; gross_amount: string; currency: string; fees: string; taxes: string; external_reference: string | null; notes: string | null; idempotent_replay: boolean };
type Position = { asset_id: string; asset_name: string | null; quantity: string; bought_quantity: string; sold_quantity: string; buy_gross: string; sell_gross: string; negative_position: boolean };
type Snapshot = { portfolio_id: string; company_id: string; base_currency: string; as_of: string; transaction_count: number; positions: Position[]; cash_reconciliation: { trade_date_balance: string; settled_balance: string; unsettled_net_amount: string; inflows: string; outflows: string; net_movements_by_type: Record<string,string> }; reconciliation: { negative_position_asset_ids: string[]; negative_position_count: number; status: string; limitations: string[] } };
const API = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");
let refreshFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  if (refreshFlight) return refreshFlight;
  refreshFlight = (async () => {
    try {
      const csrf = sessionStorage.getItem("ma_csrf_token") || "";
      const response = await fetch(`${API}/auth/refresh`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRF-Token": csrf } : {}) }, body: "{}" });
      const data = await response.json().catch(() => ({}));
      if (response.ok && data.csrf_token) { sessionStorage.setItem("ma_csrf_token", data.csrf_token); return true; }
      return false;
    } catch { return false; } finally { refreshFlight = null; }
  })();
  return refreshFlight;
}
async function api<T>(path: string, init?: RequestInit, retried = false): Promise<T> {
  const csrf = typeof window !== "undefined" ? sessionStorage.getItem("ma_csrf_token") : null;
  const response = await fetch(`${API}${path}`, { ...init, credentials: "include", cache: "no-store", headers: { "Content-Type": "application/json", ...(init?.method && init.method !== "GET" && csrf ? { "X-CSRF-Token": csrf } : {}), ...(init?.headers || {}) } });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401 && !retried && path !== "/auth/refresh") {
    if (await refreshSession()) return api<T>(path, init, true);
    sessionStorage.removeItem("ma_csrf_token"); window.location.href = "/login";
  }
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Pedido falhou (${response.status})`);
  return data as T;
}
const money = (value: string, currency: string) => {
  const number = Number(value);
  return Number.isFinite(number) ? new Intl.NumberFormat("pt-PT", { style: "currency", currency, maximumFractionDigits: 2 }).format(number) : value;
};
const stamp = (value: string) => new Date(value).toLocaleString("pt-PT");
const today = () => new Date().toISOString().slice(0, 10);

export default function PortfolioWorkspace() {
  const [companyId, setCompanyId] = useState("");
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [portfolioId, setPortfolioId] = useState("");
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [asOf, setAsOf] = useState(today());
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [type, setType] = useState("BUY");
  const [tradeDate, setTradeDate] = useState(today());
  const [settlementDate, setSettlementDate] = useState("");
  const [assetId, setAssetId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [gross, setGross] = useState("");
  const [fees, setFees] = useState("0");
  const [taxes, setTaxes] = useState("0");
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => { if (!sessionStorage.getItem("ma_csrf_token")) window.location.href = "/login"; }, []);
  const selected = useMemo(() => portfolios.find(item => item.id === portfolioId) || null, [portfolios, portfolioId]);
  const needsAsset = ["BUY", "SELL", "DIVIDEND"].includes(type);
  const needsTradeDetails = ["BUY", "SELL"].includes(type);

  async function loadPortfolios() {
    if (!companyId.trim()) throw new Error("Indica primeiro o UUID da empresa.");
    const data = await api<{ portfolios: Portfolio[] }>(`/portfolio/companies/${companyId.trim()}/portfolios`);
    setPortfolios(data.portfolios);
    if (!data.portfolios.some(item => item.id === portfolioId)) setPortfolioId(data.portfolios[0]?.id || "");
    setNotice(`${data.portfolios.length} carteira(s) carregada(s).`);
  }
  async function loadPortfolioData() {
    if (!companyId.trim() || !portfolioId) throw new Error("Seleciona uma empresa e uma carteira.");
    const [tx, positions] = await Promise.all([
      api<{ transactions: Transaction[] }>(`/portfolio/companies/${companyId.trim()}/portfolios/${portfolioId}/transactions?limit=100`),
      api<Snapshot>(`/portfolio/companies/${companyId.trim()}/portfolios/${portfolioId}/positions?as_of=${asOf}`),
    ]);
    setTransactions(tx.transactions); setSnapshot(positions);
  }
  async function createPortfolio() {
    if (!companyId.trim()) throw new Error("Indica primeiro o UUID da empresa.");
    await api(`/portfolio/companies/${companyId.trim()}/portfolios`, { method: "POST", body: JSON.stringify({ name, base_currency: currency }) });
    setName(""); await loadPortfolios(); setNotice("Carteira criada.");
  }
  async function createTransaction() {
    if (!selected) throw new Error("Seleciona uma carteira.");
    if (!idempotencyKey.trim()) throw new Error("A chave de idempotência é obrigatória.");
    const amount = needsTradeDetails ? Number(quantity) * Number(unitPrice) : Number(gross);
    if (!Number.isFinite(amount) || amount <= 0) throw new Error("Indica uma quantidade e um preço/valor bruto válidos.");
    const body = {
      transaction_type: type, trade_date: tradeDate, settlement_date: settlementDate || null,
      asset_id: needsAsset ? assetId.trim() : null,
      quantity: needsTradeDetails ? quantity : null, unit_price: needsTradeDetails ? unitPrice : null,
      gross_amount: String(amount), currency: selected.base_currency,
      fees, taxes, idempotency_key: idempotencyKey.trim(),
      external_reference: reference.trim() || null, notes: notes.trim() || null,
    };
    const result = await api<Transaction>(`/portfolio/companies/${companyId.trim()}/portfolios/${portfolioId}/transactions`, { method: "POST", body: JSON.stringify(body) });
    setIdempotencyKey(""); setReference(""); setNotes(""); setQuantity(""); setUnitPrice(""); setGross(""); setAssetId("");
    await loadPortfolioData();
    setNotice(result.idempotent_replay ? "Movimento já existia: foi devolvido o registo original (idempotência)." : "Movimento registado no ledger imutável.");
  }
  async function run(action: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); } catch (err) { setError(err instanceof Error ? err.message : "Não foi possível concluir o pedido."); } finally { setBusy(false); }
  }

  return <main className="workspace-shell">
    <header className="workspace-header"><div><p className="eyebrow">MARKET ANALYTICS · PORTFOLIO</p><h1>Portfolio Workspace</h1><p className="muted">Ledger append-only · posições por data de negociação · reconciliação de caixa</p></div><a className="back-link" href="/">Início</a></header>
    <section className="panel">
      <div className="panel-title"><div><h2>1. Selecionar empresa e carteiras</h2><p>O acesso é limitado às empresas autorizadas para a sessão autenticada.</p></div></div>
      <div className="toolbar portfolio-company"><label className="field grow"><span>ID da empresa (UUID)</span><input value={companyId} onChange={e => setCompanyId(e.target.value)} placeholder="UUID da empresa" /></label><button disabled={busy || !companyId.trim()} onClick={() => void run(loadPortfolios)}>Carregar carteiras</button></div>
      {portfolios.length > 0 && <label className="field portfolio-select"><span>Carteira</span><select value={portfolioId} onChange={e => { setPortfolioId(e.target.value); setSnapshot(null); setTransactions([]); }}><option value="">Selecionar carteira</option>{portfolios.map(item => <option key={item.id} value={item.id}>{item.name} · {item.base_currency} · {item.status}</option>)}</select></label>}
      {selected && <div className="portfolio-meta"><strong>{selected.name}</strong><span>{selected.id}</span><span>Moeda base: {selected.base_currency}</span><span>Criada: {stamp(selected.created_at)}</span></div>}
      <details className="portfolio-create"><summary>Criar carteira</summary><div className="grid-two"><label className="field"><span>Nome</span><input value={name} onChange={e => setName(e.target.value)} placeholder="Ex.: Long-term holdings" /></label><label className="field"><span>Moeda base</span><select value={currency} onChange={e => setCurrency(e.target.value)}>{["USD","EUR","GBP","CHF","CAD","AUD","JPY"].map(value => <option key={value}>{value}</option>)}</select></label></div><button disabled={busy || !name.trim()} onClick={() => void run(createPortfolio)}>Criar carteira</button></details>
    </section>
    {error && <div className="notice error" role="alert">{error}</div>}{notice && <div className="notice success" role="status">{notice}</div>}
    {selected && <>
      <section className="panel">
        <div className="panel-title"><div><h2>2. Registar movimento</h2><p>O movimento é imutável após registo. A chave de idempotência evita duplicações em reenvios.</p></div><span className="count-pill">Append-only</span></div>
        <div className="grid-two">
          <label className="field"><span>Tipo de movimento</span><select value={type} onChange={e => setType(e.target.value)}>{["BUY","SELL","DIVIDEND","DEPOSIT","WITHDRAWAL","FEE","TAX","INTEREST"].map(value => <option key={value}>{value}</option>)}</select></label>
          <label className="field"><span>Data de negociação</span><input type="date" value={tradeDate} onChange={e => setTradeDate(e.target.value)} /></label>
          <label className="field"><span>Data de liquidação (opcional)</span><input type="date" value={settlementDate} onChange={e => setSettlementDate(e.target.value)} /></label>
          {needsAsset && <label className="field"><span>Asset ID (UUID da empresa)</span><input value={assetId} onChange={e => setAssetId(e.target.value)} placeholder="UUID do ativo" /></label>}
          {needsTradeDetails ? <><label className="field"><span>Quantidade</span><input type="number" min="0" step="any" value={quantity} onChange={e => setQuantity(e.target.value)} /></label><label className="field"><span>Preço unitário ({selected.base_currency})</span><input type="number" min="0" step="any" value={unitPrice} onChange={e => setUnitPrice(e.target.value)} /></label></> : <label className="field"><span>Valor bruto ({selected.base_currency})</span><input type="number" min="0" step="any" value={gross} onChange={e => setGross(e.target.value)} /></label>}
          <label className="field"><span>Comissões</span><input type="number" min="0" step="any" value={fees} onChange={e => setFees(e.target.value)} /></label>
          <label className="field"><span>Impostos</span><input type="number" min="0" step="any" value={taxes} onChange={e => setTaxes(e.target.value)} /></label>
          <label className="field"><span>Chave de idempotência</span><input value={idempotencyKey} onChange={e => setIdempotencyKey(e.target.value)} placeholder="Ex.: broker-transaction-123" /></label>
          <label className="field"><span>Referência externa (opcional)</span><input value={reference} onChange={e => setReference(e.target.value)} /></label>
        </div>
        <label className="field portfolio-notes"><span>Notas (opcional)</span><textarea rows={2} value={notes} onChange={e => setNotes(e.target.value)} /></label>
        {needsTradeDetails && quantity && unitPrice && <p className="muted small">Valor bruto calculado: {money(String(Number(quantity) * Number(unitPrice)), selected.base_currency)}.</p>}
        <p className="notice warning">A moeda tem de coincidir com a moeda base da carteira. FX, lot accounting e cost basis ainda não estão disponíveis. Confirma os dados antes de submeter.</p>
        <button disabled={busy || !idempotencyKey.trim() || (needsAsset && !assetId.trim()) || (needsTradeDetails && (!quantity || !unitPrice)) || (!needsTradeDetails && !gross)} onClick={() => void run(createTransaction)}>Registar movimento</button>
      </section>
      <section className="panel">
        <div className="panel-title"><div><h2>3. Posições e reconciliação de caixa</h2><p>Snapshot determinístico read-only, derivado dos movimentos persistidos.</p></div><span className="count-pill">{snapshot?.reconciliation.status || "Por carregar"}</span></div>
        <div className="toolbar portfolio-refresh"><label className="field"><span>Data de referência</span><input type="date" value={asOf} onChange={e => setAsOf(e.target.value)} /></label><button disabled={busy} onClick={() => void run(loadPortfolioData)}>Atualizar snapshot e histórico</button></div>
        {snapshot && <>
          <p className="muted small">Data: {snapshot.as_of} · {snapshot.transaction_count} movimentos incluídos · {snapshot.base_currency}</p>
          <div className="portfolio-kpis"><article><span>Caixa por trade date</span><strong>{money(snapshot.cash_reconciliation.trade_date_balance, selected.base_currency)}</strong></article><article><span>Caixa liquidado</span><strong>{money(snapshot.cash_reconciliation.settled_balance, selected.base_currency)}</strong></article><article><span>Valor por liquidar</span><strong>{money(snapshot.cash_reconciliation.unsettled_net_amount, selected.base_currency)}</strong></article><article><span>Entradas / saídas</span><strong>{money(snapshot.cash_reconciliation.inflows, selected.base_currency)} / {money(snapshot.cash_reconciliation.outflows, selected.base_currency)}</strong></article></div>
          {snapshot.reconciliation.negative_position_count > 0 && <p className="notice warning">Existem {snapshot.reconciliation.negative_position_count} posições negativas. Estado REVIEW_REQUIRED: requer análise, não é corrigido automaticamente.</p>}
          <div className="table-scroll"><table className="valuation-table"><thead><tr><th>Ativo</th><th>Quantidade líquida</th><th>Comprada</th><th>Vendida</th><th>Compras brutas</th><th>Vendas brutas</th><th>Estado</th></tr></thead><tbody>{snapshot.positions.length ? snapshot.positions.map(item => <tr key={item.asset_id}><th>{item.asset_name || "Ativo sem nome"}<small className="portfolio-id">{item.asset_id}</small></th><td>{item.quantity}</td><td>{item.bought_quantity}</td><td>{item.sold_quantity}</td><td>{money(item.buy_gross, selected.base_currency)}</td><td>{money(item.sell_gross, selected.base_currency)}</td><td>{item.negative_position ? "REVIEW_REQUIRED" : "OK"}</td></tr>) : <tr><td colSpan={7}>Sem posições abertas nesta data.</td></tr>}</tbody></table></div>
          <h3 className="valuation-subtitle">Movimentos líquidos por tipo</h3><div className="portfolio-movements">{Object.entries(snapshot.cash_reconciliation.net_movements_by_type).map(([key,value]) => <div key={key}><span>{key}</span><strong>{money(value, selected.base_currency)}</strong></div>)}</div>
          <details className="context-details"><summary>Limitações da reconciliação</summary><ul>{snapshot.reconciliation.limitations.map(item => <li key={item}>{item}</li>)}</ul></details>
        </>}
      </section>
      <section className="panel">
        <div className="panel-title"><div><h2>4. Histórico do ledger</h2><p>Até 100 movimentos mais recentes; os registos originais não são editáveis nem elimináveis.</p></div><span className="count-pill">{transactions.length} movimentos</span></div>
        {!transactions.length ? <p className="empty-state">Atualiza o snapshot para carregar o histórico.</p> : <div className="table-scroll"><table className="valuation-table"><thead><tr><th>Data</th><th>Tipo</th><th>Ativo / quantidade</th><th>Valor bruto</th><th>Custos</th><th>Referência</th></tr></thead><tbody>{transactions.map(item => <tr key={item.id}><td>{item.trade_date}</td><th>{item.transaction_type}</th><td><span>{item.asset_id || "—"}</span>{item.quantity && <small className="portfolio-id">Qtd. {item.quantity} × {item.unit_price}</small>}</td><td>{money(item.gross_amount, item.currency)}</td><td>{money(String(Number(item.fees) + Number(item.taxes)), item.currency)}</td><td>{item.external_reference || "—"}{item.idempotent_replay && <small>Replay idempotente</small>}</td></tr>)}</tbody></table></div>}
      </section>
    </>}
    <p className="workspace-footer">As posições são quantidades líquidas por data de negociação. A caixa é calculada a partir do ledger e não é uma reconciliação com extrato bancário ou corretora. Não são calculados P&amp;L, cost basis, performance, FX ou backtesting.</p>
  </main>;
}
