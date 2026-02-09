import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LitFinder — Поиск научных статей с ИИ",
  description: "Умный поиск научной литературы и автоматическое оформление списка литературы по ГОСТ",
  keywords: "поиск статей, научные статьи, ГОСТ, библиография, список литературы",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className="antialiased font-inter bg-slate-950 text-white min-h-screen">
        {children}
      </body>
    </html>
  );
}
