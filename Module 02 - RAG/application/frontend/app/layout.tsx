import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Assistant documentaire Fictiva",
  description: "Questions sur la documentation de Fictiva SA (entreprise fictive, données synthétiques), avec citations.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
