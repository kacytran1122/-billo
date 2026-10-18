export type Money = {
  amount: number;
  currency?: string;
};

export type VisitItem = {
  label: string;
  code?: string;
  amount?: number | null;
  currency?: string;
  qualifier?: string;
};

export type DocumentLine = VisitItem & {
  line_no?: number;
  description?: string;
  units?: number;
  service_date?: string;
  needs_review?: boolean;
  review_reasons?: string[];
};

export type CaseView = {
  stage: "saved" | "booked" | "during" | "after";
  data_mode: "demo" | "synthetic" | "live" | "patient_provided" | "mixed" | string;
  updated_at?: string;
  provider?: null | {
    name: string;
    address?: string;
    hours?: string;
    directions_url?: string;
  };
  estimate?: null | {
    amount: number;
    currency?: string;
    source_label?: string;
    as_of?: string;
  };
  calendar?: {
    ics_url?: string;
    google_url?: string;
  };
  visit?: {
    items?: VisitItem[];
    running_total?: number;
    currency?: string;
  };
  document?: null | {
    type?: string;
    payment_status?: "paid" | "unpaid" | "unknown" | string;
    total: number;
    currency?: string;
    estimate_difference?: number | null;
    provider_match?: boolean;
    reader?: string;
    review_status?: "review_needed" | "organized" | string;
    needs_review?: number[];
    unreviewed_lines?: number[];
    fallback_reason?: string;
    lines?: DocumentLine[];
    next_steps?: string[];
  };
  wallet_url?: string;
};

export type HandoffView = {
  status: "waiting" | "linked" | "expired" | "unknown" | "used" | string;
  channel?: string;
  code?: string;
  display_code?: string;
  expires_at?: string | number;
  deep_link?: string;
};

export type WalletView = {
  mode: string;
  status: string;
  merchant_name: string;
  amount: number;
  currency?: string;
  invoice?: string;
  reference?: string;
  checks?: Array<{ id?: string; label: string; passed: boolean }> | Record<string, boolean>;
  action_url?: string;
};

export function documentReviewTitle(type?: string) {
  if (type === "receipt") return "Your receipt review";
  if (type === "bill") return "Your bill review";
  return "Your bill or receipt review";
}

export function documentNeedsReview(document?: CaseView["document"]) {
  return Boolean(
    document && (
      document.review_status === "review_needed"
      || (document.needs_review?.length ?? 0) > 0
      || (document.unreviewed_lines?.length ?? 0) > 0
    )
  );
}

export function caseDataLabel(mode: string) {
  if (mode === "mixed") return "Mixed demo + case data";
  return isDemoMode(mode) ? "Demo data" : "Case data";
}

export function formatMoney(amount: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(Number.isFinite(amount) ? amount : 0);
}

export function isDemoMode(mode: string) {
  return !["live", "patient_provided"].includes(mode);
}

export function safeWebUrl(value: string | undefined, allowedHosts?: readonly string[]) {
  if (!value) return "";
  try {
    const url = new URL(value);
    const localDevelopment = url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname);
    if (url.protocol !== "https:" && !localDevelopment) return "";
    if (url.username || url.password) return "";
    if (allowedHosts && !allowedHosts.includes(url.hostname)) return "";
    return url.toString();
  } catch {
    return "";
  }
}
