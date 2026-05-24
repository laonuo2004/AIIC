import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AIIC Chat Studio",
  description: "AIIC Chat Studio with OpenRouter model routing and file-aware chat.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
