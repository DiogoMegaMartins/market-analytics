"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type ThesisRow = { id: string; title: string; status: string; current_version_number: number; updated_at: string };
type Assumption = { assumption_id: string; description: string; metric_id: string; condition: "ABOVE" | "BELOW"; threshold: number; unit: string };
type Version = { id: string; version_number: number; summary: string; rationale: string; assumptions: Assumption[]; risks: string[]; evidence_references: string[]; created_at: string };
type ThesisDetail = { id: string; company_id: string; title: string; status: string; current_version_number: number; versions: Version[] };
type IntelligenceRow = { assumption_id: string; description: string; supports: number; contradicts: number; qualifies: number; candidate_document_evidence: number; verified_document_evidence: number; rejected_or_superseded_document_evidence: number; calculated_metrics: number; other_metric_status: number };
type EventRow = { id: string; version_id?: string; event_type: string; decision: string; payload: Record<string, unknown>; created_at: string; actor_user_id: string };
type EvidenceLink = { id: string; version_id: string; assumption_id: string; evidence_candidate_id: string | null; metric_result_id: string | null; relationship: string; rationale: string; created_at: string };
type ThesisAlert = { id: string; assumption_id: string; alert_type: string; status: string; summary: string; details: Record<string, unknown>; created_at: string };
const API = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");
let refreshFlight: Promise<boolean> | null = null;
async function refreshSession() {
  if (refreshFlight) return refreshFlight;
  refreshFlight = (async () => { try { const csrf = sessionStorage.getItem("ma_csrf_token") || ""; const r = await fetch(`${API}/auth/refresh`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRF-Token": csrf } : {}) }, body: "{}" }); const d = await r.json().catch(() => ({})); if (r.ok && d.csrf_token) { sessionStorage.setItem("ma_csrf_token", d.csrf_token); return true; } return false; } catch { return false; } finally { refreshFlight = null; } })();
  return refreshFlight;
}
async function api<T>(path: string, init?: RequestInit, retried = false): Promise<T> {
  const csrf = typeof window !== "undefined" ? sessionStorage.getItem("ma_csrf_token") : null;
  const r = await fetch(`${API}${path}`, { ...init, credentials: "include", cache: "no-store", headers: { "Content-Type": "application/json", ...(init?.method && init.method !== "GET" && csrf ? { "X-CSRF-Token": csrf } : {}), ...(init?.headers || {}) } });
  const d = await r.json().catch(() => ({}));
  if (r.status === 401 && !retried && path !== "/auth/refresh") { if (await refreshSession()) return api<T>(path, init, true); sessionStorage.removeItem("ma_csrf_token"); window.location.href = "/login"; }
  if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : `Pedido falhou (${r.status})`);
  return d as T;
}
const stamp = (s: string) => new Date(s).toLocaleString("pt-PT", { dateStyle: "medium", timeStyle: "short" });

export default function ThesisDashboard() {
  const [companyId, setCompanyId] = useState(""); const [theses, setTheses] = useState<ThesisRow[]>([]); const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<ThesisDetail | null>(null); const [intelligence, setIntelligence] = useState<IntelligenceRow[]>([]); const [links, setLinks] = useState<EvidenceLink[]>([]); const [events, setEvents] = useState<EventRow[]>([]); const [alerts, setAlerts] = useState<ThesisAlert[]>([]);
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  const [title, setTitle] = useState(""); const [summary, setSummary] = useState(""); const [rationale, setRationale] = useState(""); const [assumptionsJson, setAssumptionsJson] = useState("[]");
  const [versionSummary, setVersionSummary] = useState(""); const [versionRationale, setVersionRationale] = useState(""); const [versionAssumptions, setVersionAssumptions] = useState("[]"); const [versionRisks, setVersionRisks] = useState(""); const [versionEvidenceRefs, setVersionEvidenceRefs] = useState(""); const [compareVersionNumber, setCompareVersionNumber] = useState("");
  const [fiscalYear, setFiscalYear] = useState(String(new Date().getFullYear() - 1)); const [decision, setDecision] = useState("KEEP"); const [decisionComment, setDecisionComment] = useState("");
  const [assumptionId, setAssumptionId] = useState(""); const [targetType, setTargetType] = useState("metric"); const [targetId, setTargetId] = useState(""); const [relationship, setRelationship] = useState("SUPPORTS"); const [linkRationale, setLinkRationale] = useState("");
  const currentVersion = detail?.versions.find(v => v.version_number === detail.current_version_number) || null;
  const selectedAssumption = useMemo(() => currentVersion?.assumptions.find(a => a.assumption_id === assumptionId), [currentVersion, assumptionId]);
  const loadTheses = useCallback(async () => { if (!companyId.trim()) return; const r = await api<{ theses: ThesisRow[] }>(`/thesis/companies/${companyId.trim()}/theses`); setTheses(r.theses); }, [companyId]);
  const loadDetail = useCallback(async (id: string) => {
    const [d, i, l, e, a] = await Promise.all([
      api<ThesisDetail>(`/thesis/${id}`), api<{ assumptions: IntelligenceRow[] }>(`/thesis/${id}/intelligence`),
      api<{ evidence_links: EvidenceLink[] }>(`/thesis/${id}/evidence-links`), api<{ events: EventRow[] }>(`/thesis/${id}/events`), api<{ alerts: ThesisAlert[] }>(`/thesis/${id}/alerts`),
    ]);
    setDetail(d); setIntelligence(i.assumptions); setLinks(l.evidence_links); setEvents(e.events); setAlerts(a.alerts);
    const current = d.versions.find(v => v.version_number === d.current_version_number);
    setAssumptionId(current?.assumptions[0]?.assumption_id || "");
  }, []);
  useEffect(() => { if (!sessionStorage.getItem("ma_csrf_token")) window.location.href = "/login"; }, []);
  useEffect(() => { if (selectedId) loadDetail(selectedId).catch(e => setError(e instanceof Error ? e.message : "Falha ao carregar tese.")); }, [selectedId, loadDetail]);
  async function run(action: () => Promise<void>, success?: string) { setBusy(true); setError(""); setNotice(""); try { await action(); if (success) setNotice(success); } catch (e) { setError(e instanceof Error ? e.message : "O pedido falhou."); } finally { setBusy(false); } }
  async function createThesis() {
    let assumptions: Assumption[]; try { assumptions = JSON.parse(assumptionsJson); if (!Array.isArray(assumptions)) throw new Error(); } catch { throw new Error("Os pressupostos têm de ser um array JSON válido."); }
    const created = await api<{ id: string }>(`/thesis/companies/${companyId.trim()}/theses`, { method: "POST", body: JSON.stringify({ title, summary, rationale, assumptions, risks: [], evidence_references: [] }) });
    await loadTheses(); setSelectedId(created.id); setTitle(""); setSummary(""); setRationale(""); setAssumptionsJson("[]");
  }
  function prepareNewVersion() {
    if (!currentVersion || !detail) return;
    setVersionSummary(currentVersion.summary);
    setVersionRationale(currentVersion.rationale);
    setVersionAssumptions(JSON.stringify(currentVersion.assumptions, null, 2));
    setVersionRisks(currentVersion.risks.join("\n"));
    setVersionEvidenceRefs(currentVersion.evidence_references.join("\n"));
    setNotice("Editor preparado com o conteúdo da versão atual. As alterações só serão guardadas ao criar a nova versão.");
  }
  async function createVersion() {
    if (!selectedId || !detail) return;
    let assumptions: Assumption[];
    try { assumptions = JSON.parse(versionAssumptions); if (!Array.isArray(assumptions)) throw new Error(); }
    catch { throw new Error("Os pressupostos têm de ser um array JSON válido."); }
    const created = await api<{ version_number: number }>(`/thesis/${selectedId}/versions`, {
      method: "POST", body: JSON.stringify({
        title: detail.title, summary: versionSummary, rationale: versionRationale,
        assumptions, risks: versionRisks.split("\n").map(x => x.trim()).filter(Boolean),
        evidence_references: versionEvidenceRefs.split("\n").map(x => x.trim()).filter(Boolean),
      }),
    });
    await loadDetail(selectedId); await loadTheses();
    setNotice(`Versão ${created.version_number} criada. As versões anteriores e as respetivas ligações de evidência foram preservadas.`);
  }
  const compareVersion = detail?.versions.find(v => v.version_number === Number(compareVersionNumber)) || null;
  const versionChanges = useMemo(() => {
    if (!currentVersion || !compareVersion) return [];
    const fields: Array<[string, string, string]> = [
      ["Resumo", compareVersion.summary, currentVersion.summary],
      ["Racional", compareVersion.rationale, currentVersion.rationale],
      ["Pressupostos", JSON.stringify(compareVersion.assumptions, null, 2), JSON.stringify(currentVersion.assumptions, null, 2)],
      ["Riscos", JSON.stringify(compareVersion.risks, null, 2), JSON.stringify(currentVersion.risks, null, 2)],
      ["Referências de evidência", JSON.stringify(compareVersion.evidence_references, null, 2), JSON.stringify(currentVersion.evidence_references, null, 2)],
    ];
    return fields.filter(([, before, after]) => before !== after).map(([label, before, after]) => ({ label, before, after }));
  }, [currentVersion, compareVersion]);

  async function createLink() {
    if (!selectedId || !assumptionId || !targetId.trim()) throw new Error("Seleciona um pressuposto e indica o UUID da fonte.");
    await api(`/thesis/${selectedId}/evidence-links`, { method: "POST", body: JSON.stringify({ assumption_id: assumptionId, ...(targetType === "metric" ? { metric_result_id: targetId.trim() } : { evidence_candidate_id: targetId.trim() }), relationship, rationale: linkRationale }) });
    setTargetId(""); setLinkRationale(""); await loadDetail(selectedId);
  }
  async function evaluate() { if (!selectedId) return; await api(`/thesis/${selectedId}/evaluate?fiscal_year=${encodeURIComponent(fiscalYear)}`, { method: "POST" }); await loadDetail(selectedId); }
  async function monitor() { if (!selectedId) return; await api(`/thesis/${selectedId}/monitor?fiscal_year=${encodeURIComponent(fiscalYear)}`, { method: "POST" }); await loadDetail(selectedId); }
  async function updateAlert(id: string, status: string) { if (!selectedId) return; await api(`/thesis/${selectedId}/alerts/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }); await loadDetail(selectedId); }
  async function recordDecision() { if (!selectedId) return; await api(`/thesis/${selectedId}/decisions`, { method: "POST", body: JSON.stringify({ decision, comment: decisionComment || null }) }); setDecisionComment(""); await loadDetail(selectedId); await loadTheses(); }
  const latestEvaluation = [...events].reverse().find(e => e.event_type === "DETERMINISTIC_EVALUATION");
  const pendingRevision = [...events].reverse().find(e => e.event_type === "ANALYST_DECISION" && e.decision === "REVISE" && e.version_id === currentVersion?.id);

  return <main className="workspace-shell thesis-shell">
    <header className="workspace-header"><div><p className="eyebrow">INVESTMENT RESEARCH / THESIS</p><h1>Thesis Intelligence</h1><p className="muted">Acompanha a tese, os pressupostos, a evidência associada e as decisões do analista.</p></div><div className="toolbar"><a className="back-link" href="/">← Market Analytics</a><button className="text-button" onClick={async () => { try { await api("/auth/logout", { method: "POST" }); } finally { sessionStorage.removeItem("ma_csrf_token"); window.location.href = "/login"; } }}>Terminar sessão</button></div></header>
    <section className="panel"><div className="panel-title"><div><h2>1. Carteira de teses</h2><p>Introduz o UUID de uma empresa já registada e consulta as tuas teses.</p></div></div><div className="toolbar"><label className="field grow"><span>Company ID (UUID)</span><input value={companyId} onChange={e => setCompanyId(e.target.value)} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" /></label><button disabled={busy || !companyId.trim()} onClick={() => run(loadTheses, "Lista de teses atualizada.")}>Carregar teses</button></div>
      {theses.length > 0 && <div className="thesis-list">{theses.map(t => <button key={t.id} className={`thesis-row ${selectedId === t.id ? "active" : ""}`} onClick={() => setSelectedId(t.id)}><span><strong>{t.title}</strong><small>Versão {t.current_version_number} · Atualizada {stamp(t.updated_at)}</small></span><span className={`status ${t.status === "ACTIVE" ? "status-verified" : "status-neutral"}`}>{t.status}</span></button>)}</div>}
      {companyId.trim() && <details className="create-thesis"><summary>Criar nova tese de investimento</summary><div className="grid-two"><label className="field"><span>Título</span><input value={title} onChange={e => setTitle(e.target.value)} placeholder="Ex.: Crescimento sustentável e vantagem competitiva" /></label><label className="field"><span>Resumo</span><input value={summary} onChange={e => setSummary(e.target.value)} placeholder="Síntese da tese" /></label></div><label className="field"><span>Racional</span><textarea rows={3} value={rationale} onChange={e => setRationale(e.target.value)} /></label><label className="field"><span>Pressupostos (JSON)</span><textarea rows={5} value={assumptionsJson} onChange={e => setAssumptionsJson(e.target.value)} /><small className="muted">Campos: assumption_id, description, metric_id, condition (ABOVE/BELOW), threshold e unit.</small></label><button disabled={busy || !title.trim() || !summary.trim() || !rationale.trim()} onClick={() => run(createThesis, "Tese criada.")}>Criar tese</button></details>}
    </section>
    {error && <div className="notice error" role="alert">{error}</div>}{notice && <div className="notice success" role="status">{notice}</div>}
    {detail && currentVersion && <>
      <section className="panel"><div className="panel-title"><div><p className="eyebrow">TESE SELECIONADA · V{currentVersion.version_number}</p><h2>{detail.title}</h2><p>{currentVersion.summary}</p></div><span className={`status ${detail.status === "ACTIVE" ? "status-verified" : "status-neutral"}`}>{detail.status}</span></div><div className="thesis-copy"><h3>Racional de investimento</h3><p>{currentVersion.rationale}</p></div>{currentVersion.risks.length > 0 && <div className="thesis-copy"><h3>Riscos registados</h3><ul>{currentVersion.risks.map((risk, i) => <li key={i}>{risk}</li>)}</ul></div>}
        <div className="panel-title thesis-subtitle"><div><h3>2. Pressupostos e cobertura de evidência</h3><p>Contagens descritivas da versão atual. Não representam uma pontuação.</p></div></div>
        {currentVersion.assumptions.length === 0 ? <p className="empty-state">Esta versão ainda não tem pressupostos estruturados.</p> : <div className="assumption-grid">{currentVersion.assumptions.map(a => { const intel = intelligence.find(x => x.assumption_id === a.assumption_id); return <article className="assumption-card" key={a.assumption_id}><div className="candidate-meta"><span className="tag">{a.metric_id}</span><span className="tag subtle-tag">{a.condition} {a.threshold} {a.unit}</span></div><strong>{a.description}</strong><small className="muted">ID: {a.assumption_id}</small><div className="evidence-counts"><span>+ {intel?.supports ?? 0} suporte</span><span>− {intel?.contradicts ?? 0} contradição</span><span>≈ {intel?.qualifies ?? 0} qualificação</span></div><div className="evidence-counts muted"><span>{intel?.verified_document_evidence ?? 0} doc. verificados</span><span>{intel?.candidate_document_evidence ?? 0} por rever</span><span>{intel?.calculated_metrics ?? 0} métricas calculadas</span></div></article>; })}</div>}
        <p className="muted small">Política: evidência documental CANDIDATE ainda não foi verificada. Evidência rejeitada/substituída e métricas não calculadas não são tratadas como prova validada.</p>
      </section>
      {pendingRevision && <div className="notice warning" role="status">Foi registada uma decisão REVISE para esta versão em {stamp(pendingRevision.created_at)}. Cria uma nova versão para documentar a revisão; a decisão original continuará no histórico.</div>}
      <section className="panel">
        <div className="panel-title"><div><h2>3. Versionamento e revisão</h2><p>Uma revisão cria uma versão nova; o conteúdo anterior permanece imutável.</p></div><span className="count-pill">{detail.versions.length} versões</span></div>
        <div className="toolbar version-toolbar">
          <button className="secondary" disabled={busy} onClick={prepareNewVersion}>Preparar revisão da versão atual</button>
          <label className="field grow"><span>Comparar versão atual com</span><select value={compareVersionNumber} onChange={e => setCompareVersionNumber(e.target.value)}><option value="">Selecionar versão anterior</option>{detail.versions.filter(v => v.version_number !== currentVersion.version_number).sort((a,b) => a.version_number-b.version_number).map(v => <option key={v.id} value={v.version_number}>Versão {v.version_number} · {stamp(v.created_at)}</option>)}</select></label>
        </div>
        {compareVersion && <div className="version-comparison"><div className="candidate-meta"><span className="tag">V{compareVersion.version_number}</span><span className="tag subtle-tag">V{currentVersion.version_number}</span><strong>{versionChanges.length} campos alterados</strong></div>{versionChanges.length === 0 ? <p className="empty-state">Não foram detetadas diferenças nos campos comparados.</p> : versionChanges.map(change => <article className="version-diff" key={change.label}><strong>{change.label}</strong><div className="grid-two"><div><small>Versão {compareVersion.version_number}</small><pre>{change.before}</pre></div><div><small>Versão {currentVersion.version_number}</small><pre>{change.after}</pre></div></div></article>)}</div>}
        <details className="version-editor"><summary>Criar nova versão da tese</summary>
          <p className="muted small">O editor é preenchido com a versão atual. Altera apenas o que mudou; a criação gera um novo registo imutável.</p>
          <label className="field"><span>Resumo revisto</span><textarea rows={3} value={versionSummary} onChange={e => setVersionSummary(e.target.value)} /></label>
          <label className="field"><span>Racional revisto</span><textarea rows={5} value={versionRationale} onChange={e => setVersionRationale(e.target.value)} /></label>
          <label className="field"><span>Pressupostos (JSON)</span><textarea rows={8} value={versionAssumptions} onChange={e => setVersionAssumptions(e.target.value)} /><small className="muted">Mantém IDs estáveis quando o pressuposto continua a representar a mesma hipótese. Campos: assumption_id, description, metric_id, condition, threshold, unit.</small></label>
          <label className="field"><span>Riscos (um por linha)</span><textarea rows={3} value={versionRisks} onChange={e => setVersionRisks(e.target.value)} /></label>
          <label className="field"><span>Referências de evidência (uma por linha)</span><textarea rows={3} value={versionEvidenceRefs} onChange={e => setVersionEvidenceRefs(e.target.value)} /></label>
          <button disabled={busy || !versionSummary.trim() || !versionRationale.trim()} onClick={() => run(createVersion)}>Criar versão seguinte</button>
        </details>
        <div className="version-history"><h3>Histórico de versões</h3>{[...detail.versions].sort((a,b) => b.version_number-a.version_number).map(v => <div className="audit-row" key={v.id}><span className={`status ${v.version_number === detail.current_version_number ? "status-verified" : "status-neutral"}`}>V{v.version_number}{v.version_number === detail.current_version_number ? " · ATUAL" : ""}</span><div><strong>{v.summary}</strong><small>{stamp(v.created_at)} · {v.assumptions.length} pressupostos · {v.risks.length} riscos</small></div></div>)}</div>
      </section>
      <section className="panel"><div className="panel-title"><div><h2>4. Associar evidência</h2><p>Usa o UUID de uma métrica financeira ou de um candidato documental já existente para esta empresa.</p></div></div>{currentVersion.assumptions.length === 0 ? <p className="empty-state">Adiciona primeiro pressupostos numa nova versão da tese.</p> : <><div className="grid-two"><label className="field"><span>Pressuposto</span><select value={assumptionId} onChange={e => setAssumptionId(e.target.value)}>{currentVersion.assumptions.map(a => <option key={a.assumption_id} value={a.assumption_id}>{a.assumption_id} · {a.description}</option>)}</select></label><label className="field"><span>Tipo de fonte</span><select value={targetType} onChange={e => setTargetType(e.target.value)}><option value="metric">Resultado de métrica financeira</option><option value="document">Candidato documental BQ</option></select></label></div><div className="grid-two"><label className="field"><span>UUID da fonte</span><input value={targetId} onChange={e => setTargetId(e.target.value)} placeholder="UUID da métrica ou evidência" /></label><label className="field"><span>Relação com o pressuposto</span><select value={relationship} onChange={e => setRelationship(e.target.value)}><option value="SUPPORTS">Suporta</option><option value="CONTRADICTS">Contradiz</option><option value="QUALIFIES">Qualifica</option></select></label></div><label className="field"><span>Justificação da ligação</span><textarea rows={2} value={linkRationale} onChange={e => setLinkRationale(e.target.value)} placeholder="Explica por que razão esta fonte é relevante para o pressuposto." /></label><button disabled={busy || !selectedAssumption || !targetId.trim() || !linkRationale.trim()} onClick={() => run(createLink, "Ligação de evidência registada.")}>Registar ligação</button></>}</section>
      <section className="panel"><div className="panel-title"><div><h2>5. Avaliação e decisões</h2><p>A avaliação compara pressupostos quantitativos com o último conjunto de métricas persistido para o ano indicado.</p></div></div><div className="toolbar"><label className="field"><span>Ano fiscal</span><input type="number" min="1900" max="2200" value={fiscalYear} onChange={e => setFiscalYear(e.target.value)} /></label><button disabled={busy || !/^\d{4}$/.test(fiscalYear)} onClick={() => run(evaluate, "Avaliação determinística registada no histórico.")}>Avaliar pressupostos</button></div>{latestEvaluation && <div className="evaluation-result"><strong>Última avaliação: {latestEvaluation.decision}</strong><small>{stamp(latestEvaluation.created_at)} · FY {String(latestEvaluation.payload.fiscal_year ?? "—")}</small><pre>{JSON.stringify(latestEvaluation.payload, null, 2)}</pre></div>}<div className="decision-form"><h3>Decisão explícita do analista</h3><div className="grid-two"><label className="field"><span>Decisão</span><select value={decision} onChange={e => setDecision(e.target.value)}><option value="KEEP">Manter</option><option value="REVISE">Rever (exige nova versão)</option><option value="ON_HOLD">Colocar em espera</option><option value="INVALIDATE">Invalidar tese</option></select></label><label className="field"><span>Comentário</span><input value={decisionComment} onChange={e => setDecisionComment(e.target.value)} placeholder="Justificação da decisão (opcional)" /></label></div><button className={decision === "INVALIDATE" ? "danger-button" : "secondary"} disabled={busy} onClick={() => run(recordDecision, "Decisão do analista registada.")}>Registar decisão</button></div></section>
      <section className="panel"><div className="panel-title"><div><h2>6. Alertas de monitorização</h2><p>Deteção determinística; os alertas não alteram a tese.</p></div><button className="secondary" disabled={busy} onClick={() => run(monitor, "Monitorização concluída.")}>Monitorizar agora</button></div>{alerts.length === 0 ? <p className="empty-state">Sem alertas registados.</p> : <div className="candidate-list">{alerts.map(a => <article className="link-row" key={a.id}><div><strong>{a.summary} · {a.assumption_id}</strong><small>{a.alert_type} · {a.status} · {stamp(a.created_at)}</small><pre>{JSON.stringify(a.details, null, 2)}</pre>{a.status === "PENDING" && <button className="secondary" onClick={() => run(() => updateAlert(a.id, "REVIEWED"), "Alerta marcado como revisto.")}>Marcar revisto</button>}{a.status !== "RESOLVED" && <button className="secondary" onClick={() => run(() => updateAlert(a.id, "RESOLVED"), "Alerta resolvido.")}>Resolver</button>}</div></article>)}</div>}</section><section className="panel"><div className="panel-title"><div><h2>7. Registo de evidência e auditoria</h2><p>As ligações permanecem associadas à versão em que foram criadas.</p></div><span className="count-pill">{links.length} ligações</span></div>{links.length > 0 ? <div className="candidate-list">{links.map(l => <article className="link-row" key={l.id}><div><strong>{l.assumption_id} · {l.relationship}</strong><small>{l.evidence_candidate_id ? `Documento: ${l.evidence_candidate_id}` : `Métrica: ${l.metric_result_id}`}</small><small>{l.rationale}</small><small>Versão {detail.versions.find(v => v.id === l.version_id)?.version_number ?? "—"} · {stamp(l.created_at)}</small></div></article>)}</div> : <p className="empty-state">Ainda não existem ligações de evidência.</p>}<div className="audit-block"><h3>Histórico de eventos</h3>{events.length === 0 ? <p className="empty-state">Sem eventos registados.</p> : [...events].reverse().map(e => <div className="audit-row" key={e.id}><span className="status status-neutral">{e.event_type}</span><div><strong>{e.decision}</strong><small>{stamp(e.created_at)} · {e.actor_user_id}</small>{typeof e.payload.comment === "string" && <small>{e.payload.comment}</small>}</div></div>)}</div></section>
    </>}
    <footer className="workspace-footer">A interface não gera recomendações de compra ou venda. A associação de evidência é uma anotação do analista; as contagens não medem a força probatória. Acesso, propriedade e validação das fontes são controlados pelo backend.</footer>
  </main>;
}
