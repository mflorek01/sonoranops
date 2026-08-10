import type { ReactNode } from "react";

export const pretty = (value: string) =>
  value
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

const metricLabels: Record<string, string> = {
  belt_speed_mps: "Belt speed",
  feed_rate_tph: "Feed rate",
  motor_current_amps: "Motor current",
  screen_load_percent: "Screen load",
  vibration_mm_s: "Vibration",
};

export const metricLabel = (metric: string) => metricLabels[metric] ?? pretty(metric);

const assetLabels: Record<string, string> = {
  "primary-crusher-01": "Primary crusher",
  "conveyor-17": "Conveyor",
  "secondary-crusher-01": "Secondary crusher",
  "screen-01": "Screen",
  "stacker-01": "Stacker",
  "stockpile-01": "Stockpile",
  "feeder-01": "Feeder",
  "wash-plant-02": "Wash plant",
};

export const assetLabel = (assetId: string) => assetLabels[assetId] ?? pretty(assetId);

export const time = (value?: string) =>
  value
    ? `${new Intl.DateTimeFormat("en-US", {
        hour: "numeric",
        minute: "2-digit",
        month: "short",
        day: "numeric",
        timeZone: "America/Phoenix",
      }).format(new Date(value))} MST`
    : "Not returned";

export const number = (value?: number | null, digits = 0) =>
  value === null || value === undefined
    ? "Not returned"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(
        value,
      );

export function Pill({ value }: { value: string }) {
  return <span className={`pill ${value}`}>{pretty(value)}</span>;
}

export function Panel({
  title,
  detail,
  children,
  action,
}: {
  title: string;
  detail?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="panel">
      <header className="panel-heading">
        <div>
          <h2>{title}</h2>
          {detail && <p>{detail}</p>}
        </div>
        {action}
      </header>
      {children}
    </section>
  );
}

export function Empty({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  );
}

export function Loading({
  label = "Loading the operating record",
}: {
  label?: string;
}) {
  return (
    <div className="loading" role="status">
      {label}
    </div>
  );
}
