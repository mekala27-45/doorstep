// The type, self hosted at build time through next/font from the Fontsource packages: Epilogue for
// headlines, the interface and chart annotations; Alegreya for the long read and the memo; Fragment Mono
// for figures in dense tables, hashes, the SQL and code.
import localFont from "next/font/local";

export const epilogue = localFont({
  src: [
    { path: "../../node_modules/@fontsource-variable/epilogue/files/epilogue-latin-wght-normal.woff2", style: "normal" },
    { path: "../../node_modules/@fontsource-variable/epilogue/files/epilogue-latin-wght-italic.woff2", style: "italic" },
  ],
  weight: "100 900",
  variable: "--font-epilogue",
  display: "swap",
});

export const alegreya = localFont({
  src: [
    { path: "../../node_modules/@fontsource-variable/alegreya/files/alegreya-latin-wght-normal.woff2", style: "normal" },
    { path: "../../node_modules/@fontsource-variable/alegreya/files/alegreya-latin-wght-italic.woff2", style: "italic" },
  ],
  weight: "400 900",
  variable: "--font-alegreya",
  display: "swap",
});

export const fragment = localFont({
  src: [
    { path: "../../node_modules/@fontsource/fragment-mono/files/fragment-mono-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../node_modules/@fontsource/fragment-mono/files/fragment-mono-latin-400-italic.woff2", weight: "400", style: "italic" },
  ],
  variable: "--font-fragment",
  display: "swap",
});
