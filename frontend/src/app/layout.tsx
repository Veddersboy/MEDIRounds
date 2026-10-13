import type { Metadata } from "next";

import "./globals.css";

import { AppProvider } from "@/components/app-provider";
import { Shell } from "@/components/shell";

export const metadata: Metadata = {
  title: "MediRounds | Diabetes research assistant",
  description: "Research-focused diabetes clinical decision support",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AppProvider>
          <Shell>{children}</Shell>
        </AppProvider>
      </body>
    </html>
  );
}