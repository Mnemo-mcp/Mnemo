import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Mnemo - Persistent Engineering Cognition for AI Agents',
  description: 'One command gives AI coding agents accumulated engineering understanding across chat sessions.',
  icons: {
    icon: '/Mnemo/favicon.ico',
    apple: '/Mnemo/apple-touch-icon.png',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
