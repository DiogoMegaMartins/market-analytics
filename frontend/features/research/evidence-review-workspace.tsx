"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type DocumentRow = {
  id: string; accession_number: string; form_type: string; filed_at: string;
  published_at: string | null; source_url: string; document_hash: string;
};
type SectionRow = {
  id: string; section_key: string; heading: string; sequence_number: number;
  text_content: string; content_hash: string;
};
type ExtractedCandidate = {
  criterion_key: string; dimension: string; passage: string; source_locator: string;
  passage_type: string; matched_cues: string[]; rationale: string; status: string;
};
type PotentialConflict = { criterion_key: string; left_locator: string; right_locator: string; status: string; reason: string };
type CandidateRow = {
  id: string; criterion_key: string; status: string; passage: string; rationale: string;
  source_locator: string; evidence_hash: string; created_by: string; reviewed_by: string | null;
  review_comment: string | null; created_at: string; document_id: string; section_id: string | null;
};
type CandidateDetail = CandidateRow & {
  document: { id: string; form_type: string; accession_number: string; filed_at: string;
    published_at: string | null; source_url: string; document_hash: string } | null;
  section: { id: string; section_key: string; heading: string; text_content: string; content_hash: string } | null;
  review_events: { id: string; from_status: string | null; to_status: string; actor_id: string;
    comment: string | null; event_hash: string; created_at: string }[];
};

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");
let refreshInFlight: Promise<boolean> | null = null;

function refreshSession(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    const csrf = sessionStorage.getItem("ma_csrf_token") || "";
    try {
      const refreshed = await fetch(`${API_BASE}/auth/refresh`, { method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRF-Token": csrf } : {}) }, body: "{}" });
      const refreshBody = await refreshed.json().catch(() => ({}));
      if (refreshed.ok && refreshBody.csrf_token) {
        sessionStorage.setItem("ma_csrf_token", refreshBody.csrf_token);
        return true;
      }
      return false;
    } catch { return false; }
    finally { refreshInFlight = null; }
  })();
  return refreshInFlight;
}

async function api<T>(path: string, init?: RequestInit, retried = false): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(typeof window !== "undefined" && init?.method && init.method !== "GET" && sessionStorage.getItem("ma_csrf_token") ? { "X-CSRF-Token": sessionStorage.getItem("ma_csrf_token")! } : {}), ...(init?.headers || {}) },
    credentials: "include",
    cache: "no-store",
  });
  const body = await response.json().catch(() => ({}));
  if (response.status === 401 && typeof window !== "undefined" && !retried && path !== "/auth/refresh") {
    if (await refreshSession()) return api<T>(path, init, true);
    sessionStorage.removeItem("ma_csrf_token"); window.location.href = "/login";
  }
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : `Pedido falhou (${response.status})`;
    throw new Error(detail);
  }
  return body as T;
}

function dateLabel(value: string | null) {
  if (!value) return "Não indicada";
  return new Date(value).toLocaleString("pt-PT", { dateStyle: "medium", timeStyle: "short" });
}

export default function EvidenceReviewWorkspace() {
  const [companyId, setCompanyId] = useState("");
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [documentId, setDocumentId] = useState("");
  const [sections, setSections] = useState<SectionRow[]>([]);
  const [sectionId, setSectionId] = useState("");
  const [extracted, setExtracted] = useState<ExtractedCandidate[]>([]);
  const [conflicts, setConflicts] = useState<PotentialConflict[]>([]);
  const [candidates, setCandidates] = useState<CandidateRow[]>([]);
  const [selected, setSelected] = useState<CandidateDetail | null>(null);
  const [comment, setComment] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selectedSection = useMemo(() => sections.find((item) => item.id === sectionId), [sections, sectionId]);

  const loadCandidates = useCallback(async () => {
    if (!companyId.trim()) return;
    const query = filter === "ALL" ? "" : `?status=${filter}`;
    const result = await api<{ candidates: CandidateRow[] }>(
      `/business-quality/companies/${companyId.trim()}/evidence-candidates${query}`,
    );
    setCandidates(result.candidates);
  }, [companyId, filter]);

  async function loadDocuments() {
    setBusy(true); setError(""); setNotice(""); setSelected(null); setExtracted([]); setConflicts([]);
    try {
      const result = await api<{ documents: DocumentRow[] }>(
        `/business-quality/companies/${companyId.trim()}/source-documents`,
      );
      setDocuments(result.documents); setDocumentId(""); setSections([]); setSectionId("");
      await loadCandidates();
      setNotice(`${result.documents.length} documentos encontrados.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível carregar os documentos."); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    if (!sessionStorage.getItem("ma_csrf_token")) { window.location.href = "/login"; }
  }, []);

  useEffect(() => {
    if (!documentId) { setSections([]); setSectionId(""); return; }
    let active = true;
    api<{ sections: SectionRow[] }>(`/business-quality/source-documents/${documentId}/sections`)
      .then((result) => { if (active) { setSections(result.sections); setSectionId(""); setExtracted([]); } })
      .catch((e: unknown) => { if (active) setError(e instanceof Error ? e.message : "Erro ao carregar secções."); });
    return () => { active = false; };
  }, [documentId]);

  async function runExtraction() {
    if (!sectionId) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await api<{ candidates: ExtractedCandidate[]; candidate_count: number; potential_conflicts: PotentialConflict[] }>(
        `/business-quality/document-sections/${sectionId}/extract-candidates`, { method: "POST" },
      );
      setExtracted(result.candidates); setConflicts(result.potential_conflicts || []); setNotice(`${result.candidate_count} passagens candidatas encontradas. Ainda não foram verificadas.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Falha na extração."); }
    finally { setBusy(false); }
  }

  async function saveCandidate(item: ExtractedCandidate) {
    if (!companyId.trim() || !sectionId) { setError("Indica a empresa e a secção."); return; }
    setBusy(true); setError("");
    try {
      await api(`/business-quality/companies/${companyId.trim()}/evidence-candidates`, {
        method: "POST", body: JSON.stringify({ section_id: sectionId, criterion_key: item.criterion_key,
          passage: item.passage, rationale: item.rationale, source_locator: item.source_locator }),
      });
      setNotice("Candidato guardado com estado CANDIDATE. É necessária revisão independente.");
      await loadCandidates();
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível guardar o candidato."); }
    finally { setBusy(false); }
  }

  async function openCandidate(id: string) {
    setBusy(true); setError("");
    try { setSelected(await api<CandidateDetail>(`/business-quality/evidence-candidates/${id}`)); }
    catch (e) { setError(e instanceof Error ? e.message : "Não foi possível abrir a evidência."); }
    finally { setBusy(false); }
  }

  async function reviewCandidate(status: "VERIFIED" | "REJECTED" | "SUPERSEDED") {
    if (!selected || !comment.trim()) { setError("A revisão exige um comentário."); return; }
    setBusy(true); setError(""); setNotice("");
    try {
      await api(`/business-quality/evidence-candidates/${selected.id}/review`, {
        method: "POST", body: JSON.stringify({ status, review_comment: comment.trim() }),
      });
      setComment(""); setNotice(`Evidência atualizada para ${status}.`);
      await openCandidate(selected.id); await loadCandidates();
    } catch (e) { setError(e instanceof Error ? e.message : "A revisão falhou."); }
    finally { setBusy(false); }
  }

  return (
    <main className="workspace-shell">
      <header className="workspace-header">
        <div><p className="eyebrow">RESEARCH / EVIDENCE</p><h1>Evidence Review Workspace</h1>
          <p className="muted">Rever passagens documentais, confirmar o contexto e manter a proveniência.</p></div>
        <div className="toolbar"><button className="text-button" onClick={async () => { try { await api("/auth/logout", { method: "POST" }); } finally { sessionStorage.removeItem("ma_csrf_token"); window.location.href = "/login"; } }}>Terminar sessão</button><a className="back-link" href="/">← Market Analytics</a></div>
      </header>

      <section className="panel setup-panel">
        <div className="panel-title"><div><h2>1. Selecionar empresa e documentos</h2><p>Usa o UUID da empresa já registada no Market Analytics.</p></div></div>
        <div className="toolbar">
          <label className="field grow"><span>Company ID (UUID)</span><input value={companyId} onChange={(e) => setCompanyId(e.target.value)} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" /></label>
          <button disabled={busy || !companyId.trim()} onClick={loadDocuments}>{busy ? "A carregar…" : "Carregar documentos"}</button>
        </div>
        {documents.length > 0 && <div className="grid-two">
          <label className="field"><span>Documento SEC</span><select value={documentId} onChange={(e) => setDocumentId(e.target.value)}><option value="">Selecionar documento…</option>{documents.map((doc) => <option key={doc.id} value={doc.id}>{doc.form_type} · {doc.accession_number} · {dateLabel(doc.filed_at)}</option>)}</select></label>
          <label className="field"><span>Secção extraída</span><select value={sectionId} onChange={(e) => setSectionId(e.target.value)} disabled={!sections.length}><option value="">Selecionar secção…</option>{sections.map((section) => <option key={section.id} value={section.id}>{section.heading} ({section.section_key})</option>)}</select></label>
        </div>}
        {selectedSection && <div className="source-context"><div className="source-heading"><strong>{selectedSection.heading}</strong><span>{selectedSection.text_content.length.toLocaleString("pt-PT")} caracteres</span></div><p>{selectedSection.text_content.slice(0, 900)}{selectedSection.text_content.length > 900 ? "…" : ""}</p></div>}
        <div className="toolbar bottom-toolbar"><button className="secondary" disabled={busy || !sectionId} onClick={runExtraction}>Extrair passagens candidatas</button><span className="muted small">A extração não verifica afirmações nem atribui pontuações.</span></div>
      </section>

      {error && <div className="notice error" role="alert">{error}</div>}
      {notice && <div className="notice success" role="status">{notice}</div>}

      {conflicts.length > 0 && <div className="notice warning"><strong>Possíveis contradições para revisão:</strong>{conflicts.map((item, index) => <p key={`${item.criterion_key}-${index}`}>{item.criterion_key}: {item.reason}<br /><span className="small">{item.left_locator} ↔ {item.right_locator}</span></p>)}</div>}

      {extracted.length > 0 && <section className="panel">
        <div className="panel-title"><div><h2>2. Passagens encontradas</h2><p>Pré-visualização da extração. Guarda apenas as passagens que merecem revisão.</p></div><span className="count-pill">{extracted.length}</span></div>
        <div className="candidate-stack">{extracted.map((item, index) => <article className="candidate-card" key={`${item.criterion_key}-${index}`}>
          <div className="candidate-meta"><span className="tag">{item.dimension}</span><span className="tag subtle-tag">{item.passage_type}</span><strong>{item.criterion_key}</strong></div>
          <blockquote>{item.passage}</blockquote>
          <p className="muted small">Correspondência: {item.matched_cues.join(" · ") || "—"}</p>
          <p className="muted small">{item.source_locator}</p>
          <div className="card-actions"><button className="secondary" disabled={busy} onClick={() => saveCandidate(item)}>Guardar para revisão</button></div>
        </article>)}</div>
      </section>}

      <section className="panel">
        <div className="panel-title list-title"><div><h2>3. Fila de revisão</h2><p>Abre um candidato para consultar documento, contexto e histórico.</p></div>
          <select className="compact-select" value={filter} onChange={async (e) => { const value = e.target.value; setFilter(value); if (companyId.trim()) { try { const query = value === "ALL" ? "" : `?status=${value}`; const result = await api<{ candidates: CandidateRow[] }>(`/business-quality/companies/${companyId.trim()}/evidence-candidates${query}`); setCandidates(result.candidates); } catch (err) { setError(err instanceof Error ? err.message : "Falha ao filtrar candidatos."); } } }}><option value="ALL">Todos os estados</option><option value="CANDIDATE">Por rever</option><option value="VERIFIED">Verificados</option><option value="REJECTED">Rejeitados</option><option value="SUPERSEDED">Substituídos</option></select>
        </div>
        <div className="toolbar list-refresh"><button className="text-button" disabled={!companyId.trim() || busy} onClick={() => loadCandidates()}>Atualizar fila ↻</button></div>
        {candidates.length === 0 ? <p className="empty-state">Sem candidatos para mostrar. Carrega uma empresa e os respetivos documentos.</p> : <div className="candidate-list">
          {candidates.map((item) => <button className={`candidate-row ${selected?.id === item.id ? "active" : ""}`} key={item.id} onClick={() => openCandidate(item.id)}>
            <div className="row-main"><strong>{item.criterion_key}</strong><span>{item.passage.slice(0, 170)}{item.passage.length > 170 ? "…" : ""}</span><small>{dateLabel(item.created_at)} · {item.created_by}</small></div>
            <span className={`status status-${item.status.toLowerCase()}`}>{item.status}</span>
          </button>)}
        </div>}
      </section>

      {selected && <section className="panel detail-panel">
        <div className="panel-title"><div><h2>4. Revisão da evidência</h2><p>{selected.criterion_key} · <span className={`status status-${selected.status.toLowerCase()}`}>{selected.status}</span></p></div><button className="text-button" onClick={() => setSelected(null)}>Fechar</button></div>
        <blockquote className="detail-passage">{selected.passage}</blockquote>
        <div className="detail-grid"><div><span className="detail-label">Documento</span><strong>{selected.document?.form_type} · {selected.document?.accession_number}</strong><small>Filing: {selected.document ? dateLabel(selected.document.filed_at) : "—"}</small><small>Disponibilidade: {selected.document ? dateLabel(selected.document.published_at) : "Não indicada"}</small>{selected.document && <a href={selected.document.source_url} target="_blank" rel="noreferrer">Abrir fonte SEC ↗</a>}</div>
          <div><span className="detail-label">Secção e localização</span><strong>{selected.section?.heading || "Secção indisponível"}</strong><small>{selected.source_locator}</small><small>Hash da passagem: {selected.evidence_hash}</small><small>Criado por: {selected.created_by}</small></div></div>
        {selected.section && <details className="context-details"><summary>Ver contexto integral da secção</summary><pre>{selected.section.text_content}</pre></details>}
        {selected.status === "CANDIDATE" && <div className="review-form"><h3>Decisão do revisor</h3><label className="field"><span>Comentário obrigatório</span><input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Justificação da decisão" /></label><div className="toolbar review-actions"><button disabled={busy} onClick={() => reviewCandidate("VERIFIED")}>Verificar</button><button className="danger-button" disabled={busy} onClick={() => reviewCandidate("REJECTED")}>Rejeitar</button><button className="secondary" disabled={busy} onClick={() => reviewCandidate("SUPERSEDED")}>Marcar substituída</button></div><p className="muted small">O criador não pode rever o próprio candidato. A revisão é registada no histórico.</p></div>}
        <div className="audit-block"><h3>Histórico de revisão</h3>{selected.review_events.map((event) => <div className="audit-row" key={event.id}><span className="status status-neutral">{event.from_status || "—"} → {event.to_status}</span><div><strong>{event.actor_id}</strong><small>{event.comment || "Sem comentário"} · {dateLabel(event.created_at)}</small><small className="hash">Hash: {event.event_hash}</small></div></div>)}</div>
      </section>}

      <footer className="workspace-footer">A identidade é obtida a partir da sessão autenticada e as permissões são verificadas no backend. Uma evidência VERIFIED é uma decisão de revisão, não uma garantia de verdade nem uma pontuação de investimento.</footer>
    </main>
  );
}
