import Link from "next/link";

const workspaces = [
  { href: "/research/evidence", number: "01", name: "Research & Evidence", description: "Rever fontes, validar evidência e manter rastreabilidade da investigação.", category: "RESEARCH", action: "Abrir evidence review" },
  { href: "/valuation", number: "02", name: "Valuation", description: "Explorar pressupostos, cenários e avaliações fundamentais.", category: "ANALYSIS", action: "Abrir valuation" },
  { href: "/thesis", number: "03", name: "Investment Thesis", description: "Estruturar teses, acompanhar pressupostos e documentar decisões.", category: "DECISION MAKING", action: "Abrir thesis workspace" },
  { href: "/portfolio", number: "04", name: "Portfolio", description: "Consultar carteiras, movimentos, posições e métricas de performance.", category: "PORTFOLIO", action: "Abrir portfolio" },
];

export default function HomePage() {
  return (
    <div className="workspace-shell overview-page">
      <section className="overview-hero">
        <div className="hero-copy">
          <p className="eyebrow">INVESTMENT RESEARCH PLATFORM <span>·</span> PRIVATE WORKSPACE</p>
          <h1>Clarity for<br /><em>long-term decisions.</em></h1>
          <p className="hero-description">Um espaço integrado para investigação fundamentalista, avaliação empresarial e acompanhamento disciplinado de carteiras.</p>
          <div className="hero-rule"><span /> <small>RESEARCH WITH RIGOUR. DECISIONS WITH CONVICTION.</small></div>
        </div>
        <div className="hero-seal" aria-hidden="true"><div className="seal-orbit" /><div className="seal-inner"><span>MA</span><small>EST. FOR<br />DISCIPLINED<br />RESEARCH</small></div></div>
      </section>

      <section className="overview-section">
        <div className="section-heading"><div><p className="eyebrow">YOUR WORKSPACE</p><h2>Áreas de trabalho</h2></div><span className="section-index">01 — 04</span></div>
        <div className="workspace-grid">
          {workspaces.map((item) => <Link href={item.href} key={item.href} className="workspace-card">
            <div className="workspace-card-top"><span>{item.number}</span><small>{item.category}</small></div>
            <div><h3>{item.name}</h3><p>{item.description}</p></div>
            <div className="workspace-card-action"><span>{item.action}</span><b>↗</b></div>
          </Link>)}
        </div>
      </section>
      <section className="principles-strip"><div><span className="principle-mark">01</span><strong>Evidence-led</strong><small>Fontes e pressupostos rastreáveis</small></div><div><span className="principle-mark">02</span><strong>Fundamental-first</strong><small>Foco no valor e nos fundamentos</small></div><div><span className="principle-mark">03</span><strong>Long-term oriented</strong><small>Disciplina na análise e decisão</small></div></section>
    </div>
  );
}
