"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { ConsentBadge, IndexBadge, StatusBadge } from "@/components/admin/Badges";
import { Link } from "@/i18n/navigation";
import type { ContentType, Theme } from "@/lib/api";
import { adminApi, CREATABLE_TYPES, type AdminContentItem } from "@/lib/adminApi";

import styles from "./page.module.css";

export default function AdminContentListPage() {
  const t = useTranslations("admin");
  const tSections = useTranslations("sections");

  const [items, setItems] = useState<AdminContentItem[]>([]);
  const [themes, setThemes] = useState<Theme[]>([]);
  const [theme, setTheme] = useState("");
  const [type, setType] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const result = await adminApi.listContent({
      theme: theme || undefined,
      type: (type as ContentType) || undefined,
    });
    setItems(result);
    setLoading(false);
  }, [theme, type]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const result = await adminApi.themes();
        if (!cancelled) setThemes(result);
      } catch {
        if (!cancelled) setThemes([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    // El guardia evita actualizar el estado de un componente ya desmontado
    // cuando el filtro cambia antes de que termine la petición anterior.
    let cancelled = false;
    void (async () => {
      try {
        await load();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  return (
    <div>
      <div className={styles.header}>
        <h1 className={styles.title}>{t("content")}</h1>
        <Link href="/admin/contenido/nuevo" className={styles.newButton}>
          {t("newContent")}
        </Link>
      </div>

      <div className={styles.filters}>
        <label className={styles.filter}>
          <span className={styles.filterLabel}>{t("filterTheme")}</span>
          <select value={theme} onChange={(event) => setTheme(event.target.value)}>
            <option value="">{t("all")}</option>
            {themes.map((option) => (
              <option key={option.slug} value={option.slug}>
                {option.name_es}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.filter}>
          <span className={styles.filterLabel}>{t("filterType")}</span>
          <select value={type} onChange={(event) => setType(event.target.value)}>
            <option value="">{t("all")}</option>
            {CREATABLE_TYPES.map((option) => (
              <option key={option} value={option}>
                {tSections(option)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading ? (
        <p className={styles.muted}>{t("loading")}</p>
      ) : items.length === 0 ? (
        <p className={styles.muted}>{t("empty")}</p>
      ) : (
        <div className={styles.tableWrapper}>
          {/* Una tabla real, no una rejilla de divs: el contenido es tabular y
              un lector de pantalla necesita los encabezados para anunciar cada
              celda con su columna. */}
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">{t("columnTitle")}</th>
                <th scope="col">{t("columnTheme")}</th>
                <th scope="col">{t("columnType")}</th>
                <th scope="col">{t("columnStatus")}</th>
                <th scope="col">{t("columnConsent")}</th>
                <th scope="col">{t("columnIndex")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <th scope="row" className={styles.titleCell}>
                    <Link href={`/admin/contenido/${item.id}`}>{item.title}</Link>
                    <span className={styles.slug}>{item.slug}</span>
                  </th>
                  <td>{item.theme_slug}</td>
                  <td>{tSections(item.type)}</td>
                  <td>
                    <StatusBadge status={item.status} />
                  </td>
                  {/* El alcance de consentimiento se ve aquí, sin abrir el
                      detalle: es requisito de la spec `admin-cms`. */}
                  <td>
                    <ConsentBadge scope={item.consent_scope} />
                  </td>
                  <td>
                    <IndexBadge indexed={item.is_indexable} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
