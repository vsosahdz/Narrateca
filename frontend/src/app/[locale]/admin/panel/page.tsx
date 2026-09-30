"use client";

import { useFormatter, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { adminApi, type Dashboard, type ScanReport } from "@/lib/adminApi";

import styles from "./page.module.css";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tSections = useTranslations("sections");
  const format = useFormatter();

  const [data, setData] = useState<Dashboard | null>(null);
  const [scan, setScan] = useState<ScanReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setData(await adminApi.dashboard());
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await load();
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "Error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  async function runScan() {
    setBusy(true);
    setError(null);
    try {
      setScan(await adminApi.scanArchive());
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className={styles.error} role="alert">{error}</p>;
  if (!data) return <p className={styles.muted}>…</p>;

  const dateTime = (value: string) =>
    format.dateTime(new Date(value), { dateStyle: "medium", timeStyle: "short" });

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>{t("title")}</h1>
          <p className={styles.muted}>
            {t("generatedAt", { time: dateTime(data.generated_at) })}
          </p>
        </div>
        <div className={styles.actions}>
          <Button variant="secondary" onClick={load}>
            {t("actions.refresh")}
          </Button>
          <Button variant="primary" loading={busy} onClick={runScan}>
            {busy ? t("actions.scanning") : t("actions.scan")}
          </Button>
        </div>
      </div>

      {/* --- Totales ------------------------------------------------------- */}
      <ul className={styles.totals}>
        <li className={styles.stat}>
          <span className={styles.statValue}>{data.total_items}</span>
          <span className={styles.statLabel}>{t("totals.items")}</span>
        </li>
        <li className={styles.stat}>
          <span className={styles.statValue}>{data.total_published}</span>
          <span className={styles.statLabel}>{t("totals.published")}</span>
        </li>
        <li className={styles.stat} data-emphasis="corpus">
          <span className={styles.statValue}>{data.total_indexable}</span>
          <span className={styles.statLabel}>{t("totals.indexable")}</span>
        </li>
      </ul>

      {/* --- Avisos -------------------------------------------------------- */}
      <section className={styles.card} aria-labelledby="avisos">
        <h2 id="avisos" className={styles.cardTitle}>
          {t("alerts.title")}
        </h2>
        {data.alerts.length === 0 ? (
          <p className={styles.muted}>{t("alerts.none")}</p>
        ) : (
          <ul className={styles.alerts}>
            {data.alerts.map((alert, index) => (
              <li key={index} className={styles.alert} data-level={alert.level}>
                <strong className={styles.alertCount}>{alert.count}</strong>
                <span>{alert.message}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* --- Cobertura ----------------------------------------------------- */}
      <section className={styles.card} aria-labelledby="cobertura">
        <h2 id="cobertura" className={styles.cardTitle}>
          {t("coverage.title")}
        </h2>
        <p className={styles.help}>{t("coverage.help")}</p>

        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">{t("coverage.community")}</th>
                <th scope="col">{t("coverage.total")}</th>
                <th scope="col">{t("coverage.draft")}</th>
                <th scope="col">{t("coverage.published")}</th>
                <th scope="col">{t("coverage.withdrawn")}</th>
                <th scope="col">{t("coverage.indexable")}</th>
                <th scope="col">{t("coverage.noAi")}</th>
                <th scope="col">{t("coverage.siteOnly")}</th>
                <th scope="col">{t("coverage.blockedAlt")}</th>
              </tr>
            </thead>
            <tbody>
              {data.themes.map((theme) => (
                <tr key={theme.theme_slug}>
                  <th scope="row">{theme.theme_name}</th>
                  <td>{theme.total}</td>
                  <td>{theme.draft}</td>
                  <td>{theme.published}</td>
                  <td>{theme.withdrawn}</td>
                  <td data-emphasis="corpus">{theme.indexable}</td>
                  <td>{theme.excluded_no_ai}</td>
                  <td>{theme.excluded_site_only}</td>
                  <td data-warn={theme.blocked_missing_alt_text > 0 ? "yes" : undefined}>
                    {theme.blocked_missing_alt_text}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className={styles.columns}>
        {/* --- Ingesta ----------------------------------------------------- */}
        <section className={styles.card} aria-labelledby="ingesta">
          <h2 id="ingesta" className={styles.cardTitle}>
            {t("archiveHealth.title")}
          </h2>
          <p className={styles.help}>
            {data.archive.last_scan_at
              ? t("archiveHealth.lastScan", { time: dateTime(data.archive.last_scan_at) })
              : t("archiveHealth.neverScanned")}
          </p>

          <ul className={styles.statusList}>
            {Object.entries(data.archive.by_status).map(([status, count]) => (
              <li key={status}>
                <span>{t(`archiveHealth.status.${status}`)}</span>
                <strong>{count}</strong>
              </li>
            ))}
            <li data-total="yes">
              <span>{t("archiveHealth.needsAttention")}</span>
              <strong>{data.archive.needs_attention}</strong>
            </li>
          </ul>

          {scan && (
            <p className={styles.scanResult} role="status">
              {scan.scanned} · +{scan.new.length} · ~{scan.modified.length} · −
              {scan.missing.length}
            </p>
          )}
        </section>

        {/* --- Tipos ------------------------------------------------------- */}
        <section className={styles.card} aria-labelledby="tipos">
          <h2 id="tipos" className={styles.cardTitle}>
            {t("types.title")}
          </h2>
          <ul className={styles.statusList}>
            {data.types.map((entry) => (
              <li key={entry.type}>
                <span>{tSections(entry.type)}</span>
                <strong>{entry.count}</strong>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {/* --- Actividad ----------------------------------------------------- */}
      <section className={styles.card} aria-labelledby="actividad">
        <h2 id="actividad" className={styles.cardTitle}>
          {t("activity.title")}
        </h2>
        {data.recent_activity.length === 0 ? (
          <p className={styles.muted}>{t("activity.none")}</p>
        ) : (
          <ul className={styles.activity}>
            {data.recent_activity.map((entry, index) => (
              <li key={index}>
                <code>{entry.action}</code> {entry.entity_type} · {t("activity.by")}{" "}
                {entry.account_email}
                <time dateTime={entry.created_at}>{dateTime(entry.created_at)}</time>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* --- Pendiente de datos --------------------------------------------
          Se muestran declaradas y vacías a propósito. Reportar cero haría creer
          que no hay uso, cuando lo que falta es la funcionalidad. */}
      <section className={styles.card} data-pending="yes" aria-labelledby="pendiente">
        <h2 id="pendiente" className={styles.cardTitle}>
          {t("pending.title")}
        </h2>
        <p className={styles.help}>{t("pending.help")}</p>
        <ul className={styles.pending}>
          {data.pending_sections.map((section) => (
            <li key={section.key}>
              <strong>{section.label}</strong>
              <span>{section.reason}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
