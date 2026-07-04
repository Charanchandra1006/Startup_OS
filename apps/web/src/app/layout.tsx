import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Chief OS — AI CEO Assistant & Founder Executive Dashboard",
  description: "Modern, premium, minimal AI CEO Assistant Dashboard for founders inspired by Linear, Notion, Stripe, and Apple.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased bg-white text-black`}
    >
      <body className="min-h-full flex flex-col bg-white text-black selection:bg-neutral-200 font-sans">{children}</body>
    </html>
  );
}
