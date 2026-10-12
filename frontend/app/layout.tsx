import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Document Assistant",
  description: "Pose des questions à tes documents (RAG)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
