// The live API and its recorded stand in. The first call on a page probes /v1/health with a six
// second limit, twice, because the API's machine stops when idle and the first request wakes it; if
// it is asleep or unreachable, every API feature on the page answers from recorded_session.json for
// the rest of the visit and says so beside the control it affects.
import { API, dataUrl } from "./site";

export type Source = "live" | "recorded";

export interface Envelope {
  statement: string;
  rate_attribution: string;
  served_at: string;
}
export interface HealthResponse extends Envelope {
  status: string;
  environment: string;
  database: string;
  model_version: string;
  metros: number;
  latest_period: string;
  rate_default: number | null;
  income_year: number | null;
  writes: string;
}
export interface MetroEntry {
  cbsa_code: string;
  cbsa_title: string;
  households: number;
  median_income: number;
  median_rent: number;
  latest_period: string;
  value_latest: number;
  rate_latest: number;
  income_year: number;
}
export interface MetrosResponse extends Envelope {
  metros: MetroEntry[];
  rate_default: number;
  model_version: string;
}
export interface Inputs {
  cbsa_code: string;
  income: number;
  down_share: number;
  rate: number | null;
  horizon_years: number;
}
export interface AnswerBody {
  cbsa_code: string;
  cbsa_title?: string;
  quarter: string;
  income: number;
  down_share: number;
  rate: number;
  horizon_years: number;
  median_home: number;
  payment: number;
  payment_share: number;
  affordable_price: number;
  affordable_share: number | null;
  households_can_afford?: number | null;
  breakeven_years: number | null;
  breakeven_low: number | null;
  breakeven_high: number | null;
  never_share?: number | null;
  median_income?: number;
  income_year?: number;
  expected_next_payment_share: number;
}
export interface CurvePoint {
  year: number;
  difference: number;
  owner_equity: number;
  renter_wealth: number;
  home_value: number;
}
export interface CurveResponse extends Envelope, AnswerBody {
  points: CurvePoint[];
  model_version: string;
}
export interface CheckOut extends Envelope, AnswerBody {
  check_id: string;
  model_version: string;
  note: string;
  created_at: string;
  score?: {
    scored_quarter: string;
    realized_payment_share: number;
    absolute_error: number;
    price_moved: number;
    rate_moved: number;
    scored_at: string;
  } | null;
}

interface RecordedResponse {
  method: string;
  path: string;
  status: number;
  body: unknown;
}
export interface RecordedSession {
  recorded: boolean;
  recorded_at: string;
  base_url: string;
  inputs: Inputs[];
  responses: Record<string, RecordedResponse>;
}

export interface Answer<T> {
  source: Source;
  status: number;
  body: T;
  /** Why the answer is the recorded one when the API itself is awake. */
  reason?: string;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

const PROBE_TIMEOUT_MS = 6000;
const PROBE_ATTEMPTS = 2;
const PROBE_PAUSE_MS = 4000;

let probe: Promise<Source> | null = null;
let session: Promise<RecordedSession> | null = null;

async function probeOnce(): Promise<Source> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const response = await fetch(`${API}/v1/health`, { signal: controller.signal, cache: "no-store" });
    if (!response.ok) return "recorded";
    const body = (await response.json()) as Partial<HealthResponse>;
    return body.status === "ok" ? "live" : "recorded";
  } catch {
    return "recorded";
  } finally {
    window.clearTimeout(timer);
  }
}

/** Whether this page visit talks to the live API or to the recording. Probed twice, then fixed. */
export function apiSource(): Promise<Source> {
  probe ??= (async (): Promise<Source> => {
    if (!API) return "recorded";
    for (let attempt = 1; attempt <= PROBE_ATTEMPTS; attempt += 1) {
      if (attempt > 1) await new Promise((resolve) => window.setTimeout(resolve, PROBE_PAUSE_MS));
      if ((await probeOnce()) === "live") return "live";
    }
    return "recorded";
  })();
  return probe;
}

export function recordedSession(): Promise<RecordedSession> {
  session ??= fetch(dataUrl("recorded_session.json")).then((r) => {
    if (!r.ok) throw new Error(`the recorded session did not load (${r.status})`);
    return r.json() as Promise<RecordedSession>;
  });
  return session;
}

async function fromRecording<T>(name: string, reason?: string): Promise<Answer<T>> {
  const s = await recordedSession();
  const hit = s.responses[name];
  if (!hit) throw new Error("the recorded session has no answer for these inputs; pick one of the recorded metros at its recorded inputs");
  return { source: "recorded", status: hit.status, body: hit.body as T, reason };
}

async function send<T>(path: string, init: RequestInit = {}): Promise<{ status: number; body: T }> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  const body = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new ApiError(response.status, typeof body.error === "string" ? body.error : `status ${response.status}`);
  return { status: response.status, body };
}

/** A read: the live answer when the API is awake, else the recorded one under the given name. */
export async function read<T>(path: string, recordedName: string): Promise<Answer<T>> {
  if ((await apiSource()) === "live") {
    try {
      const { status, body } = await send<T>(path);
      return { source: "live", status, body };
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) throw err;
      return fromRecording<T>(recordedName, "the live API did not answer this request");
    }
  }
  return fromRecording<T>(recordedName);
}

/** The recorded name of a curve: the inputs, with the rate as given or "default". */
export function curveName(i: Inputs): string {
  return `curve_${i.cbsa_code}_${i.income}_${i.down_share}_${i.rate ?? "default"}_${i.horizon_years}`;
}

export function curvePath(i: Inputs): string {
  const q = new URLSearchParams({
    cbsa_code: i.cbsa_code,
    income: String(i.income),
    down_share: String(i.down_share),
    horizon_years: String(i.horizon_years),
  });
  if (i.rate !== null) q.set("rate", String(i.rate));
  return `/v1/curve?${q.toString()}`;
}

export function getCurve(i: Inputs): Promise<Answer<CurveResponse>> {
  return read<CurveResponse>(curvePath(i), curveName(i));
}

/** Save a check. Writes need the token and a live API; without either, the answer is the check the
 * recording made for that metro, labelled as recorded. */
export async function saveCheck(i: Inputs, token: string): Promise<Answer<CheckOut>> {
  const name = `check_${i.cbsa_code}`;
  if ((await apiSource()) !== "live") return fromRecording<CheckOut>(name);
  if (!token.trim()) return fromRecording<CheckOut>(name, "no write token was given");
  const payload: Record<string, unknown> = { cbsa_code: i.cbsa_code, income: i.income, down_share: i.down_share, horizon_years: i.horizon_years, note: "saved from the planner" };
  if (i.rate !== null) payload.rate = i.rate;
  const { status, body } = await send<CheckOut>("/v1/checks", {
    method: "POST",
    body: JSON.stringify(payload),
    headers: { Authorization: `Bearer ${token.trim()}` },
  });
  return { source: "live", status, body };
}
