"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navigation = [
  { href: "/", label: "Visão geral", short: "OV", section: "WORKSPACE" },
  { href: "/research/evidence", label: "Research & Evidence", short: "RE", section: "RESEARCH" },
  { href: "/valuation", label: "Valuation", short: "VA", section: "RESEARCH" },
  { href: "/thesis", label: "Investment Thesis", short: "TH", section: "RESEARCH" },
  { href: "/portfolio", label: "Portfolio", short: "PF", section: "PORTFOLIO" },
];

export default function AppFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/login") return <>{children}</>;
  return (
    <div className="app-frame">
      <aside className="app-sidebar">
        <Link href="/" className="brand-lockup" aria-label="Market Analytics — início">
          <span className="brand-mark">M<span>A</span></span>
          <span className="brand-copy"><strong>MARKET ANALYTICS</strong><small>FUNDAMENTAL RESEARCH</small></span>
        </Link>
        <div className="sidebar-rule" />
        <nav className="primary-nav" aria-label="Navegação principal">
          {["WORKSPACE", "RESEARCH", "PORTFOLIO"].map((section) => (
            <div className="nav-section" key={section}>
              <p>{section}</p>
              {navigation.filter((item) => item.section === section).map((item) => {
                const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                return <Link key={item.href} href={item.href} className={active ? "nav-link active" : "nav-link"} aria-current={active ? "page" : undefined}>
                  <span className="nav-monogram">{item.short}</span><span>{item.label}</span>{active && <i />}
                </Link>;
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="environment-dot" />
          <span><strong>Research environment</strong><small>Private workspace</small></span>
        </div>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <div className="topbar-context"><span>MARKET INTELLIGENCE</span><span className="topbar-divider">/</span><strong>{navigation.find((item) => item.href === "/" ? pathname === "/" : pathname.startsWith(item.href))?.label || "Workspace"}</strong></div>
          <div className="topbar-right"><span className="secure-label"><span /> Ambiente privado</span><Link href="/login" className="topbar-account">Conta <span>↗</span></Link></div>
        </header>
        <main className="app-content">{children}</main>
        <footer className="app-footer"><span>MARKET ANALYTICS</span><span>Fundamental research · Evidence-led decisions</span></footer>
      </div>
    </div>
  );
}
