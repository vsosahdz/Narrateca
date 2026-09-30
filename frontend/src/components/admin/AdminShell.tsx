"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { adminApi, type Account } from "@/lib/adminApi";

import styles from "./AdminShell.module.css";

/**
 * Envoltorio de la sección de administración.
 *
 * Resuelve la sesión en el cliente y redirige a la pantalla de inicio de sesión
 * si no hay ninguna. Esto es conveniencia de navegación, **no** el control de
 * acceso: quien manipule el navegador no obtiene nada, porque cada endpoint del
 * backend verifica la sesión y el rol por su cuenta.
 */
export function AdminShell({ children }: { children: React.ReactNode }) {
  const t = useTranslations("admin");
  const tPanel = useTranslations("dashboard");
  const router = useRouter();
  const pathname = usePathname();
  const isLoginPage = pathname === "/admin/login";

  const [account, setAccount] = useState<Account | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;

    adminApi
      .me()
      .then((me) => {
        if (!cancelled) setAccount(me);
      })
      .catch(() => {
        if (!cancelled && !isLoginPage) router.replace("/admin/login");
      })
      .finally(() => {
        if (!cancelled) setChecked(true);
      });

    return () => {
      cancelled = true;
    };
  }, [isLoginPage, router]);

  async function signOut() {
    await adminApi.logout();
    setAccount(null);
    router.replace("/admin/login");
  }

  if (isLoginPage) return <>{children}</>;
  if (!checked) return <p className={styles.loading}>{t("loading")}</p>;

  return (
    <div className={styles.shell}>
      <header className={styles.bar}>
        <div>
          <Link href="/admin" className={styles.brand}>
            {t("title")}
          </Link>
          <nav className={styles.nav} aria-label={t("title")}>
            <Link href="/admin" className={styles.navLink}>
              {t("content")}
            </Link>
            <Link href="/admin/panel" className={styles.navLink}>
              {tPanel("title")}
            </Link>
          </nav>
          {account && (
            <p className={styles.account}>
              {account.full_name} ·{" "}
              {account.role === "admin"
                ? "admin"
                : account.themes.map((theme) => theme.slug).join(", ") || "editor"}
            </p>
          )}
        </div>
        <Button variant="ghost" onClick={signOut}>
          {t("signOut")}
        </Button>
      </header>

      {children}
    </div>
  );
}
