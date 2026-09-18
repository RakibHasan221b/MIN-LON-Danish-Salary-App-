import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Min Løn — Danish salary calculator",
  description: "Estimate your Danish net salary under 2026 tax rules.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
