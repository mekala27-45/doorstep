import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { Shell } from "@/components/Shell";
import { THEME_SCRIPT } from "@/components/ThemeToggle";
import palette from "@/theme/palette.json";

import { alegreya, epilogue, fragment } from "./fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "doorstep: can anyone still afford a home", template: "%s | doorstep" },
  description:
    "A data story in eight chapters on every US metropolitan area the public record covers since 2000: what affordable means, the rate shock and the lock in, the rent burden the median hides, supply, the fair metro ranking, who still buys, the migration shock, and the rent or buy decision.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: palette.light.surface },
    { media: "(prefers-color-scheme: dark)", color: palette.dark.surface },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // The theme script sets data-theme before first paint, so the server markup cannot match it.
    <html lang="en" suppressHydrationWarning className={`${epilogue.variable} ${alegreya.variable} ${fragment.variable}`}>
      <body>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
