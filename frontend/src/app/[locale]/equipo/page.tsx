import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { api } from "@/lib/api";
import { mediaUrl } from "@/lib/media";

import styles from "./page.module.css";

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "team" });
  return { title: t("title"), description: t("intro") };
}

/**
 * Página del equipo de investigación.
 *
 * Cada integrante lleva fotografía, nombre y biografía. Quien no tenga
 * fotografía cargada muestra un marcador neutro en lugar de una imagen rota:
 * el estado incompleto es normal mientras el equipo se documenta, y no debe
 * verse como un error.
 */
export default async function TeamPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  const [t, members] = await Promise.all([getTranslations("team"), api.team()]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{t("title")}</h1>
        <p className={styles.intro}>{t("intro")}</p>
      </header>

      {members.length === 0 ? (
        <p className={styles.empty}>{t("empty")}</p>
      ) : (
        <ul className={styles.grid}>
          {members.map((member) => (
            <li key={member.id} className={styles.member}>
              {member.photo_key ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  className={styles.photo}
                  src={mediaUrl(member.photo_key)}
                  alt={member.photo_alt ?? ""}
                  loading="lazy"
                />
              ) : (
                <div className={styles.photoPlaceholder} role="presentation">
                  <span className="visually-hidden">{t("noPhoto")}</span>
                </div>
              )}

              <div className={styles.info}>
                <h2 className={styles.name}>{member.full_name}</h2>
                {member.role_title && <p className={styles.role}>{member.role_title}</p>}
                <p className={styles.bio} lang="es">
                  {member.bio}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
