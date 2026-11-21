import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "MNEMO",
  description: "MNEMO Teacher Mode. From answer intelligence to learning intelligence.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-stone-100 text-stone-900 antialiased">{children}</body>
    </html>
  );
}
