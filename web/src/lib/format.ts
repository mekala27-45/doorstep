// Number formats, mirroring packages/core/src/doorstep_core/formats.py so that a value reads the
// same on the site as in the memo and the README. Anything that rounds to zero prints unsigned.
export type Scalar = number | string | boolean | null;

export const FORMATS = [
  "int",
  "float1",
  "float2",
  "float3",
  "float4",
  "sfloat1",
  "sfloat2",
  "sfloat3",
  "sfloat4",
  "pct0",
  "spct0",
  "pct1",
  "pct2",
  "spct1",
  "spct2",
  "pts1",
  "pts2",
  "apts1",
  "min0",
  "min1",
  "min2",
  "smin1",
  "smin2",
  "millions1",
  "thousands0",
  "hours0",
  "hours1",
  "days1",
  "ms",
  "usd0",
  "susd0",
  "usdk",
  "usdm1",
  "usdb1",
  "years1",
  "years0",
  "beyond1",
  "beyond0",
  "ratio1",
  "ratio2",
  "rate2",
  "srate2",
  "quarter",
  "year",
  "month",
  "date",
  "text",
] as const;
export type Fmt = (typeof FORMATS)[number];

/** The breakeven engine's horizon; one past it is its sentinel for owning never catching up (policy.breakeven_horizon_years). */
export const BREAKEVEN_HORIZON_YEARS = 30;

/**
 * Fixed decimals with thousands separators, rounded the way Python's format() rounds: on the
 * exact binary value of the number, ties to even. toFixed(100) is the exact expansion for every
 * magnitude this site prints, so the decision is made on real digits rather than on the shortest
 * decimal that happens to print for the number.
 */
function grouped(n: number, decimals: number): string {
  const negative = n < 0 || Object.is(n, -0);
  const [whole = "0", frac = ""] = Math.abs(n).toFixed(100).split(".");
  const digits = (whole + frac.slice(0, decimals)).split("").map(Number);
  const rest = frac.slice(decimals);
  const first = Number(rest[0] ?? "0");
  const tied = first === 5 && !/[1-9]/.test(rest.slice(1));
  const last = digits[digits.length - 1] ?? 0;
  if (first > 5 || (first === 5 && !tied) || (tied && last % 2 === 1)) {
    let i = digits.length - 1;
    while (i >= 0) {
      const d = (digits[i] ?? 0) + 1;
      digits[i] = d % 10;
      if (d < 10) break;
      i -= 1;
    }
    if (i < 0) digits.unshift(1);
  }
  const intDigits = digits.slice(0, digits.length - decimals).join("") || "0";
  const intText = intDigits.replace(/^0+(?=\d)/, "").replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const fracText = decimals > 0 ? `.${digits.slice(digits.length - decimals).join("")}` : "";
  return `${negative ? "-" : ""}${intText}${fracText}`;
}

const isZero = (text: string): boolean => Number(text.replace(/[,-]/g, "")) === 0;

const plain = (n: number, decimals: number): string => {
  const text = grouped(n, decimals);
  return text.startsWith("-") && isZero(text) ? text.slice(1) : text;
};


const signed = (n: number, decimals: number): string => {
  const text = plain(n, decimals);
  return n > 0 && !isZero(text) ? `+${text}` : text;
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** One formatter for every figure on the site. The format names are the manifest's `fmt`; the last
 * three (year, month, date) are for chart axes, whose x values arrive as numbers. */
export function formatValue(value: Scalar | undefined, fmt: string): string {
  if (fmt === "text") return value === null || value === undefined ? "not available" : String(value);
  if (fmt === "quarter") {
    if (value === null || value === undefined) return "not available";
    if (typeof value === "number") {
      // A quarter on an axis is the year plus the quarter's fraction; a tick between quarters prints the year.
      const year = Math.floor(value + 1e-9);
      const q = Math.round((value - year) * 4) + 1;
      return Math.abs((value - year) * 4 - Math.round((value - year) * 4)) < 1e-6 ? `${year}Q${q}` : String(year);
    }
    return String(value);
  }
  if (value === null || value === undefined) return "not applicable";
  if (fmt === "date" || fmt === "month") {
    const d = typeof value === "number" ? new Date(value) : new Date(String(value));
    if (Number.isNaN(d.getTime())) return String(value);
    return fmt === "date" ? d.toISOString().slice(0, 10) : `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  }
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "not available";
  switch (fmt) {
    case "int":
      return plain(n, 0);
    case "year":
      return String(Math.round(n));
    case "float1":
      return plain(n, 1);
    case "float2":
      return plain(n, 2);
    case "float3":
      return plain(n, 3);
    case "float4":
      return plain(n, 4);
    case "sfloat1":
      return signed(n, 1);
    case "sfloat2":
      return signed(n, 2);
    case "sfloat3":
      return signed(n, 3);
    case "sfloat4":
      return signed(n, 4);
    case "pct0":
      return `${plain(n * 100, 0)}%`;
    case "pct1":
      return `${plain(n * 100, 1)}%`;
    case "pct2":
      return `${plain(n * 100, 2)}%`;
    case "spct0":
      return `${signed(n * 100, 0)}%`;
    case "spct1":
      return `${signed(n * 100, 1)}%`;
    case "spct2":
      return `${signed(n * 100, 2)}%`;
    case "pts1":
      return `${signed(n * 100, 1)} pts`;
    case "pts2":
      return `${signed(n * 100, 2)} pts`;
    case "apts1":
      return `${plain(n * 100, 1)} pts`;
    case "min0":
      return `${plain(n, 0)} min`;
    case "min1":
      return `${plain(n, 1)} min`;
    case "min2":
      return `${plain(n, 2)} min`;
    case "smin1":
      return `${signed(n, 1)} min`;
    case "smin2":
      return `${signed(n, 2)} min`;
    case "millions1":
      return `${plain(n / 1_000_000, 1)} million`;
    case "thousands0":
      return `${plain(Math.round(n / 1000), 0)} thousand`;
    case "hours0":
      return `${plain(Math.round(n), 0)} h`;
    case "hours1":
      return `${plain(n, 1)} h`;
    case "days1":
      return `${plain(n, 1)} days`;
    case "ms":
      return `${plain(Math.round(n), 0)} ms`;
    case "usd0":
      return `${n < 0 && Math.round(n) !== 0 ? "-" : ""}$${plain(Math.abs(n), 0)}`;
    case "susd0":
      return Math.round(n) === 0 ? "$0" : `${n > 0 ? "+" : "-"}$${plain(Math.abs(n), 0)}`;
    case "usdk":
      return `$${plain(n / 1000, 1)}k`;
    case "usdm1":
      return `$${plain(n / 1_000_000, 1)} million`;
    case "usdb1":
      return `$${plain(n / 1_000_000_000, 1)} billion`;
    case "years1":
      return `${plain(n, 1)} years`;
    case "years0":
      return Math.round(n) === 1 ? "1 year" : `${plain(Math.round(n), 0)} years`;
    case "beyond1":
      return n > BREAKEVEN_HORIZON_YEARS ? `beyond ${BREAKEVEN_HORIZON_YEARS} years` : `${plain(n, 1)} years`;
    case "beyond0":
      return n > BREAKEVEN_HORIZON_YEARS ? `beyond ${BREAKEVEN_HORIZON_YEARS} years` : Math.round(n) === 1 ? "1 year" : `${plain(Math.round(n), 0)} years`;
    case "ratio1":
      return `${plain(n, 1)}x`;
    case "ratio2":
      return `${plain(n, 2)}x`;
    case "rate2":
      return `${plain(n, 2)}%`;
    case "srate2":
      return `${signed(n, 2)} pts`;
    default:
      throw new Error(`unknown format ${fmt}`);
  }
}

/** Shorthand for chart code, which formats query results rather than manifest entries. */
export const fmt = (value: Scalar | undefined, format: Fmt): string => formatValue(value, format);

/** A timestamp from a mart or the API as "YYYY-MM-DD HH:MM" in UTC. DuckDB hands a timestamp
 * column to the page as epoch milliseconds or a Date, the API as an ISO string; all three land
 * here, so no page prints a raw number of milliseconds. */
export function whenUtc(value: unknown, suffix = " UTC"): string {
  if (value === null || value === undefined || value === "") return "";
  let iso: string;
  if (value instanceof Date) iso = value.toISOString();
  else if (typeof value === "number" || (typeof value === "bigint")) iso = new Date(Number(value)).toISOString();
  else if (typeof value === "string" && /^\d{11,}$/.test(value)) iso = new Date(Number(value)).toISOString();
  else iso = String(value);
  return iso.replace("T", " ").slice(0, 16) + suffix;
}

