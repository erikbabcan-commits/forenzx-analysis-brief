import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ForenZX · Release Board",
  description: "Súkromný backlog, odborné zdroje a podmienky vydania ForenZX Analysis Brief.",
  robots: { index: false, follow: false },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="sk">
      <body className="antialiased">{children}</body>
    </html>
  );
}
