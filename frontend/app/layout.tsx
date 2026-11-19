import type { ReactNode } from "react";
import "./globals.css";
import AppFrame from "../components/app-frame";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-PT">
      <body><AppFrame>{children}</AppFrame></body>
    </html>
  );
}
