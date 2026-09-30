"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/Button";
import { Field } from "@/components/Field";
import { useRouter } from "@/i18n/navigation";
import { adminApi, AdminApiError } from "@/lib/adminApi";

import styles from "./page.module.css";

export default function LoginPage() {
  const t = useTranslations("admin");
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);

    try {
      await adminApi.login(email, password);
      router.replace("/admin");
    } catch (caught) {
      // El backend devuelve el mismo mensaje exista o no el correo, para no
      // revelar qué direcciones tienen cuenta. Se muestra tal cual.
      setError(caught instanceof AdminApiError ? caught.message : t("signInError"));
      setPending(false);
    }
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>{t("title")}</h1>

      <form className={styles.form} onSubmit={onSubmit} noValidate>
        <Field
          label={t("email")}
          type="email"
          name="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <Field
          label={t("password")}
          type="password"
          name="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

        {/* El error se anuncia a lectores de pantalla cuando aparece, en vez de
            quedar como texto que solo se ve. */}
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}

        <Button type="submit" variant="primary" loading={pending}>
          {pending ? t("signingIn") : t("signIn")}
        </Button>
      </form>
    </div>
  );
}
