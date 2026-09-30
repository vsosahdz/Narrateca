"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { adminApi, type SubtitleTrack } from "@/lib/adminApi";

import styles from "@/app/[locale]/admin/contenido/form.module.css";

/**
 * Edición de las pistas de subtítulos de una pieza audiovisual.
 *
 * La transcripción automática equivoca nombres propios y términos locales. En un
 * testimonio eso no es un detalle cosmético: cambia lo que la persona dijo. Por
 * eso las pistas son editables y no solo generadas.
 */
export function SubtitleEditor({ itemId }: { itemId: string }) {
  const t = useTranslations("admin.subtitles");

  const [tracks, setTracks] = useState<SubtitleTrack[]>([]);
  const [editing, setEditing] = useState<"es" | "en" | null>(null);
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setTracks(await adminApi.subtitleStatus(itemId));
  }, [itemId]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await refresh();
      } catch {
        if (!cancelled) setTracks([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  async function open(locale: "es" | "en", exists: boolean) {
    setEditing(locale);
    setError(null);
    if (!exists) {
      setContent("WEBVTT\n\n");
      return;
    }
    try {
      setContent((await adminApi.readSubtitle(itemId, locale)).content);
    } catch {
      setContent("WEBVTT\n\n");
    }
  }

  async function save() {
    if (!editing) return;
    setBusy(true);
    setError(null);
    try {
      await adminApi.writeSubtitle(itemId, editing, content);
      await refresh();
      setEditing(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={styles.subtitles} aria-labelledby="subtitulos">
      <h2 id="subtitulos" className={styles.consentLabel}>
        {t("title")}
      </h2>
      <p className={styles.consentHelp}>{t("help")}</p>

      {tracks.map((track) => (
        <div key={track.locale} className={styles.subtitleRow}>
          <strong>{track.locale === "es" ? "Español" : "English"}</strong>
          <span>{track.exists ? t("present") : t("missing")}</span>
          <Button variant="ghost" onClick={() => open(track.locale, track.exists)}>
            {t("edit")}
          </Button>
        </div>
      ))}

      {editing && (
        <>
          <label className={styles.consentLabel} htmlFor="pista">
            {editing === "es" ? "Español" : "English"}
          </label>
          <textarea
            id="pista"
            className={styles.subtitleTextarea}
            rows={12}
            spellCheck
            value={content}
            onChange={(event) => setContent(event.target.value)}
          />
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
          <div className={styles.subtitleRow}>
            <Button variant="primary" loading={busy} onClick={save}>
              Guardar pista
            </Button>
            <Button variant="ghost" onClick={() => setEditing(null)}>
              Cancelar
            </Button>
          </div>
        </>
      )}
    </section>
  );
}
