"use client";

import { FormEvent, useState } from "react";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/auth/token`, { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify({ email, password }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Não foi possível iniciar sessão.");
      sessionStorage.setItem("ma_csrf_token", data.csrf_token);
      window.location.href = "/thesis";
    } catch (e) { setError(e instanceof Error ? e.message : "Erro de autenticação."); }
    finally { setBusy(false); }
  }

  return <main className="login-page">
    <section className="login-brand-panel">
      <div className="login-brand"><span className="brand-mark">M<span>A</span></span><span className="brand-copy"><strong>MARKET ANALYTICS</strong><small>FUNDAMENTAL RESEARCH</small></span></div>
      <div className="login-brand-message"><p className="eyebrow">INDEPENDENT THINKING. RIGOROUS ANALYSIS.</p><h1>Invest with<br /><em>understanding.</em></h1><p>Investigação fundamentalista construída sobre evidência, método e perspetiva de longo prazo.</p></div>
      <div className="login-brand-foot"><span>PRIVATE RESEARCH ENVIRONMENT</span><span>01 / 01</span></div>
      <div className="login-decoration" aria-hidden="true"><span /><span /><span /></div>
    </section>
    <section className="login-form-panel">
      <div className="login-form-wrap">
        <div className="login-mobile-brand"><span className="brand-mark">M<span>A</span></span><strong>MARKET ANALYTICS</strong></div>
        <p className="eyebrow">WELCOME BACK</p>
        <h2>Iniciar sessão</h2>
        <p className="login-intro">Acede ao teu espaço privado de investigação.</p>
        <form onSubmit={submit} className="login-form">
          <label className="field"><span>Endereço de email</span><input type="email" autoComplete="username" placeholder="nome@empresa.com" required value={email} onChange={e => setEmail(e.target.value)} /></label>
          <label className="field"><span>Password</span><input type="password" autoComplete="current-password" placeholder="Introduz a tua password" required value={password} onChange={e => setPassword(e.target.value)} /></label>
          {error && <div className="notice error" role="alert">{error}</div>}
          <button disabled={busy} className="login-submit">{busy ? "A validar…" : "Entrar no workspace"} <span>→</span></button>
        </form>
        <div className="login-security"><span>⌑</span><p><strong>Acesso protegido</strong><small>As contas são provisionadas por um administrador. Não existe registo público.</small></p></div>
        <p className="login-copyright">© MARKET ANALYTICS · PRIVATE ACCESS</p>
      </div>
    </section>
  </main>;
}
