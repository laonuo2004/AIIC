import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AIIC Stack Chat",
  description: "Full-stack AI chat baseline for the AIIC project challenge.",
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
