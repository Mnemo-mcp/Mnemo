import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mnemo — Persistent Engineering Cognition for AI Agents",
  description:
    "Your AI coding agent forgets everything between sessions. Mnemo gives it a persistent memory layer — knowledge graphs, semantic recall, and cross-session context that never fades.",
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='4' fill='%230A0A0A'/><text x='4' y='24' font-size='20' font-family='monospace' fill='%23F59E0B'>m</text></svg>",
  },
  openGraph: {
    title: "Mnemo — Persistent Engineering Cognition for AI Agents",
    description:
      "Your AI coding agent forgets everything between sessions. Mnemo gives it a persistent memory layer.",
    type: "website",
  },
  twitter: { card: "summary_large_image" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,ital@9..144,700,0;9..144,700,1;9..144,800,0;9..144,800,1;9..144,900,0;9..144,900,1&family=IBM+Plex+Mono:wght@400;500;600;700&family=Instrument+Sans:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-bg text-neutral-200 antialiased font-body">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[9999] focus:bg-accent focus:text-black focus:px-4 focus:py-2 focus:rounded"
        >
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
