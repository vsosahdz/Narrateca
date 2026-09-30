import { setRequestLocale } from "next-intl/server";

import { AdminShell } from "@/components/admin/AdminShell";

/**
 * Sección de administración.
 *
 * No se prerenderiza ni se cachea: su contenido depende de la sesión y muestra
 * material no publicado. Servir una versión cacheada aquí podría entregar un
 * borrador a quien no debe verlo.
 */
export const dynamic = "force-dynamic";

export default async function AdminLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <AdminShell>{children}</AdminShell>;
}
