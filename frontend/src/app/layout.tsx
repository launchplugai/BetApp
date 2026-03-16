import type { Metadata } from "next";
import { ReactNode } from "react";

import { Providers } from "@/components/providers";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: "BetApp Frontend Split",
  description: "Evaluate-first frontend scaffold for the FastAPI separation plan.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
