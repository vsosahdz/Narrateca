"use client";

import { useTranslations } from "next-intl";
import { use, useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { ConsentBadge, IndexBadge, StatusBadge } from "@/components/admin/Badges";
import {
  ContentForm,
  draftFromItem,
  toPayload,
  type ContentDraft,
} from "@/components/admin/ContentForm";
import { SubtitleEditor } from "@/components/admin/SubtitleEditor";
import { Link, useRouter } from "@/i18n/navigation";
import type { Theme } from "@/lib/api";
import {
  adminApi,
  CONSENT_SCOPES,
  type AdminContentItem,
  type ConsentScope,
} from "@/lib/adminApi";

import styles from "../form.module.css";

export default function EditContentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useTranslations("admin");
  const router = useRouter();

  const [item, setItem] = useState<AdminContentItem | null>(null);
  const [themes, setThemes] = useState<Theme[]>([]);
  const [draft, setDraft] = useState<ContentDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const fetched = await adminApi.getContent(id);
    setItem(fetched);
    setDraft(draftFromItem(fetched));
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const list = await adminApi.themes();
        if (!cancelled) setThemes(list);
      } catch {
        if (!cancelled) setThemes([]);
      }
      try {
        await refresh();
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "Error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  /** Ejecuta una acción mostrando su error en vez de dejarla fallar en silencio. */
  async function run(action: () => Promise<unknown>, successMessage?: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      await refresh();
      if (successMessage) setNotice(successMessage);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(t("deleteConfirm"))) return;
    await run(() => adminApi.deleteContent(id));
    router.replace("/admin");
  }

  if (!item || !draft) {
    return <p>{error ?? t("loading")}</p>;
  }

  const hasMedia = Boolean(item.media_key);

  return (
    <div>
      <div className={styles.header}>
        <div>
          <Link href="/admin" className={styles.back}>
            ← {t("backToList")}
          </Link>
          <h1 className={styles.title}>{t("editContent")}</h1>
        </div>

        <div className={styles.actions}>
          {item.status !== "published" ? (
            <Button variant="primary" disabled={busy} onClick={() => run(() => adminApi.publish(id))}>
              {t("publish")}
            </Button>
          ) : (
            <Button variant="secondary" disabled={busy} onClick={() => run(() => adminApi.withdraw(id))}>
              {t("withdraw")}
            </Button>
          )}
          <Button variant="danger" disabled={busy} onClick={remove}>
            {t("delete")}
          </Button>
        </div>
      </div>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      )}

      <div className={styles.statusRow}>
        <StatusBadge status={item.status} />
        <ConsentBadge scope={item.consent_scope} />
        <IndexBadge indexed={item.is_indexable} />
      </div>

      {/* El consentimiento es la decisión más delicada del catálogo, así que
          tiene su propio control y su propio endpoint: cambiarlo no se mezcla
          con guardar el resto del formulario. */}
      <div className={styles.consentControl}>
        <label className={styles.consentLabel} htmlFor="consent">
          {t("consent.label")}
        </label>
        <p className={styles.consentHelp}>{t("consent.help")}</p>
        <select
          id="consent"
          value={item.consent_scope}
          disabled={busy}
          onChange={(event) =>
            run(() => adminApi.setConsent(id, event.target.value as ConsentScope))
          }
        >
          {CONSENT_SCOPES.map((scope) => (
            <option key={scope} value={scope}>
              {t(`consent.${scope}`)}
            </option>
          ))}
        </select>
      </div>

      {hasMedia && <SubtitleEditor itemId={id} />}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void run(() => adminApi.updateContent(id, toPayload(draft)), t("saved"));
        }}
        noValidate
      >
        <ContentForm draft={draft} themes={themes} onChange={setDraft} disableIdentity />

        <div className={styles.actions}>
          <Button type="submit" variant="primary" loading={busy}>
            {busy ? t("saving") : t("save")}
          </Button>
        </div>
      </form>
    </div>
  );
}
