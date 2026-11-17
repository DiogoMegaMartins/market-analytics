export default function HomePage() {
  return (
    <main style={{ maxWidth: 960, margin: "64px auto", padding: "0 24px", fontFamily: "system-ui" }}>
      <p style={{ color: "#587084", fontSize: 11, fontWeight: 800, letterSpacing: ".15em" }}>MARKET ANALYTICS</p>
      <h1>Fundamental Research Workspace</h1>
      <p>Plataforma de investigação fundamentalista e análise de qualidade empresarial.</p>
      <nav style={{ display: "flex", flexWrap: "wrap", gap: 20, marginTop: 22 }}>
        <a href="/thesis" style={{ color: "#185b86", fontWeight: 700 }}>Abrir Thesis Intelligence →</a>
        <a href="/research/evidence" style={{ color: "#185b86", fontWeight: 700 }}>Abrir Evidence Review Workspace →</a>
      </nav>
    </main>
  );
}
