"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/Button";
import { Field } from "@/components/Field";
import type { Attribution, ContentType, Sensitivity, Theme } from "@/lib/api";
import { adminApi, CREATABLE_TYPES, type AdminContentItem } from "@/lib/adminApi";

import styles from "./ContentForm.module.css";

export interface ContentDraft {
  theme_slug: string;
  type: ContentType;
  slug: string;
  title: string;
  summary: string;
  body: string;
  attribution: Attribution;
  person_name: string;
  pseudonym: string;
  sensitivity: Sensitivity;
  alt_text: string;
  external_url: string;
  source_name: string;
  recorded_on: string;
  media_key: string;
  media_mime: string;
}

export function emptyDraft(themeSlug = ""): ContentDraft {
  return {
    theme_slug: themeSlug,
    type: "testimony",
    slug: "",
    title: "",
    summary: "",
    body: "",
    attribution: "anonymous",
    person_name: "",
    pseudonym: "",
    sensitivity: "normal",
    alt_text: "",
    external_url: "",
    source_name: "",
    recorded_on: "",
    media_key: "",
    media_mime: "",
  };
}

export function draftFromItem(item: AdminContentItem): ContentDraft {
  return {
    theme_slug: item.theme_slug,
    type: item.type,
    slug: item.slug,
    title: item.title,
    summary: item.summary ?? "",
    body: item.body ?? "",
    attribution: item.attribution,
    person_name: item.person_name ?? "",
    pseudonym: item.pseudonym ?? "",
    sensitivity: item.sensitivity,
    alt_text: item.alt_text ?? "",
    external_url: item.external_url ?? "",
    source_name: item.source_name ?? "",
    recorded_on: item.recorded_on ?? "",
    media_key: item.media_key ?? "",
    media_mime: item.media_mime ?? "",
  };
}

/** Campos vacíos se envían como null, no como cadena vacía. */
export function toPayload(draft: ContentDraft): Record<string, unknown> {
  const optional = (value: string) => (value.trim() === "" ? null : value.trim());

  return {
    theme_slug: draft.theme_slug,
    type: draft.type,
    slug: draft.slug.trim(),
    title: draft.title.trim(),
    summary: optional(draft.summary),
    body: optional(draft.body),
    attribution: draft.attribution,
    person_name: optional(draft.person_name),
    pseudonym: optional(draft.pseudonym),
    sensitivity: draft.sensitivity,
    alt_text: optional(draft.alt_text),
    external_url: optional(draft.external_url),
    source_name: optional(draft.source_name),
    recorded_on: optional(draft.recorded_on),
    media_key: optional(draft.media_key),
    media_mime: optional(draft.media_mime),
  };
}

const VISUAL_TYPES: ContentType[] = ["photo"];
const EXTERNAL_TYPES: ContentType[] = ["curated_link", "video"];

export function ContentForm({
  draft,
  themes,
  onChange,
  disableIdentity = false,
}: {
  draft: ContentDraft;
  themes: Theme[];
  onChange: (draft: ContentDraft) => void;
  /** En edición, el tema y el identificador no cambian: la dirección pública
   *  debe permanecer estable porque el chatbot la usa al citar. */
  disableIdentity?: boolean;
}) {
  const t = useTranslations("admin");
  const tSections = useTranslations("sections");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const set = <K extends keyof ContentDraft>(key: K, value: ContentDraft[K]) =>
    onChange({ ...draft, [key]: value });

  async function upload(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      const result = await adminApi.uploadMedia(file, draft.theme_slug, draft.sensitivity);
      onChange({ ...draft, media_key: result.media_key, media_mime: result.media_mime });
    } catch (caught) {
      setUploadError(caught instanceof Error ? caught.message : t("upload.error"));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className={styles.form}>
      <fieldset className={styles.group}>
        <legend className={styles.legend}>{t("fields.theme")}</legend>

        <label className={styles.select}>
          <span className={styles.selectLabel}>{t("fields.theme")}</span>
          <select
            value={draft.theme_slug}
            onChange={(event) => set("theme_slug", event.target.value)}
            disabled={disableIdentity}
            required
          >
            <option value="">—</option>
            {themes.map((theme) => (
              <option key={theme.slug} value={theme.slug}>
                {theme.name_es}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.select}>
          <span className={styles.selectLabel}>{t("fields.type")}</span>
          <select
            value={draft.type}
            onChange={(event) => set("type", event.target.value as ContentType)}
            disabled={disableIdentity}
          >
            {CREATABLE_TYPES.map((type) => (
              <option key={type} value={type}>
                {tSections(type)}
              </option>
            ))}
          </select>
        </label>

        <Field
          label={t("fields.slug")}
          hint={t("fields.slugHelp")}
          value={draft.slug}
          onChange={(event) => set("slug", event.target.value)}
          disabled={disableIdentity}
          required
        />
      </fieldset>

      <fieldset className={styles.group}>
        <legend className={styles.legend}>{t("fields.title")}</legend>

        <Field
          label={t("fields.title")}
          value={draft.title}
          onChange={(event) => set("title", event.target.value)}
          required
        />

        <label className={styles.textareaLabel}>
          <span className={styles.selectLabel}>{t("fields.summary")}</span>
          <textarea
            className={styles.textarea}
            rows={2}
            value={draft.summary}
            onChange={(event) => set("summary", event.target.value)}
          />
        </label>

        <label className={styles.textareaLabel}>
          <span className={styles.selectLabel}>{t("fields.body")}</span>
          <textarea
            className={styles.textarea}
            rows={10}
            value={draft.body}
            onChange={(event) => set("body", event.target.value)}
          />
        </label>
      </fieldset>

      <fieldset className={styles.group}>
        <legend className={styles.legend}>{t("fields.attribution")}</legend>

        <label className={styles.select}>
          <span className={styles.selectLabel}>{t("fields.attribution")}</span>
          <select
            value={draft.attribution}
            onChange={(event) => set("attribution", event.target.value as Attribution)}
          >
            {(["anonymous", "pseudonym", "named"] as Attribution[]).map((value) => (
              <option key={value} value={value}>
                {t(`attribution.${value}`)}
              </option>
            ))}
          </select>
        </label>

        {draft.attribution === "pseudonym" && (
          <Field
            label={t("fields.pseudonym")}
            value={draft.pseudonym}
            onChange={(event) => set("pseudonym", event.target.value)}
            required
          />
        )}

        <Field
          label={t("fields.personName")}
          hint={t("fields.personNameHelp")}
          value={draft.person_name}
          onChange={(event) => set("person_name", event.target.value)}
          required={draft.attribution === "named"}
        />

        <label className={styles.select}>
          <span className={styles.selectLabel}>{t("fields.sensitivity")}</span>
          <select
            value={draft.sensitivity}
            onChange={(event) => set("sensitivity", event.target.value as Sensitivity)}
          >
            {(["normal", "high"] as Sensitivity[]).map((value) => (
              <option key={value} value={value}>
                {t(`sensitivity.${value}`)}
              </option>
            ))}
          </select>
          <span className={styles.help}>{t("fields.sensitivityHelp")}</span>
        </label>
      </fieldset>

      <fieldset className={styles.group}>
        <legend className={styles.legend}>{t("fields.media")}</legend>

        {draft.media_key && (
          <p className={styles.currentFile}>
            {t("upload.current")}: <code>{draft.media_key}</code>
          </p>
        )}

        <label className={styles.select}>
          <span className={styles.selectLabel}>
            {draft.media_key ? t("upload.replace") : t("upload.choose")}
          </span>
          <input
            type="file"
            disabled={uploading || !draft.theme_slug}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file);
            }}
          />
        </label>

        {uploading && <p className={styles.help}>{t("upload.uploading")}</p>}
        {uploadError && (
          <p className={styles.error} role="alert">
            {uploadError}
          </p>
        )}

        {(VISUAL_TYPES.includes(draft.type) || draft.media_mime.startsWith("image/")) && (
          <Field
            label={t("fields.altText")}
            hint={t("fields.altTextHelp")}
            value={draft.alt_text}
            onChange={(event) => set("alt_text", event.target.value)}
            required
          />
        )}

        {EXTERNAL_TYPES.includes(draft.type) && (
          <>
            <Field
              label={t("fields.externalUrl")}
              type="url"
              value={draft.external_url}
              onChange={(event) => set("external_url", event.target.value)}
            />
            <Field
              label={t("fields.sourceName")}
              value={draft.source_name}
              onChange={(event) => set("source_name", event.target.value)}
            />
          </>
        )}

        <Field
          label={t("fields.recordedOn")}
          type="date"
          value={draft.recorded_on}
          onChange={(event) => set("recorded_on", event.target.value)}
        />
      </fieldset>
    </div>
  );
}

export { Button };
