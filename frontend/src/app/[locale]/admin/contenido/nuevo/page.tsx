"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button } from "@/components/Button";
import {
  ContentForm,
  emptyDraft,
  toPayload,
  type ContentDraft,
} from "@/components/admin/ContentForm";
import { Link, useRouter } from "@/i18n/navigation";
import type { Theme } from "@/lib/api";
import { adminApi } from "@/lib/adminApi";

import styles from "../form.module.css";

export default function NewContentPage() {
  const t = useTranslations("admin");
  const router = useRouter();

  const [themes, setThemes] = useState<Theme[]>([]);
  const [draft, setDraft] = useState<ContentDraft>(emptyDraft());
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    adminApi.themes().then(setThemes).catch(() => setThemes([]));
  }, []);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);

    try {
      // La pieza nace como borrador, siempre. Publicar es una acción aparte, y
      // el consentimiento arranca en «sin uso con IA» por decisión del backend.
      const created = await adminApi.createContent(toPayload(draft));
      router.replace(`/admin/contenido/${created.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Error");
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} noValidate>
      <div className={styles.header}>
        <div>
          <Link href="/admin" className={styles.back}>
            ← {t("backToList")}
          </Link>
          <h1 className={styles.title}>{t("newContent")}</h1>
        </div>
        <Button type="submit" variant="primary" loading={saving}>
          {saving ? t("saving") : t("save")}
        </Button>
      </div>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      <ContentForm draft={draft} themes={themes} onChange={setDraft} />
    </form>
  );
}
