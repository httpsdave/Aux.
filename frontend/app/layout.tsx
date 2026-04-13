import type { Metadata } from "next";
import { Space_Grotesk, Bebas_Neue } from "next/font/google";

import "./globals.css";

const bodyFont = Space_Grotesk({ subsets: ["latin"], variable: "--font-body" });
const titleFont = Bebas_Neue({ subsets: ["latin"], weight: "400", variable: "--font-title" });

export const metadata: Metadata = {
  title: "Aux.",
  description: "Chart rankings with song previews"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${bodyFont.variable} ${titleFont.variable}`}>{children}</body>
    </html>
  );
}
