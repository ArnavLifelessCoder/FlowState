import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FlowState — Adaptive Intelligence Dashboard",
  description: "Real-time emotionally adaptive AI platform that monitors cognitive load, attention, and stress to adapt digital experiences.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
