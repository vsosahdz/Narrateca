import createNextIntlPlugin from "next-intl/plugin";
import type { NextConfig } from "next";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  // Salida autónoma: reduce el tamaño de la imagen y el tiempo de arranque en
  // frío, que importa porque Cloud Run corre con `min_instances = 0`
  // (ver design.md, decisión 15).
  output: "standalone",

  // Next.js aquí es solo capa de renderizado y ruteo. El backend es un servicio
  // FastAPI independiente; este proyecto no expone API routes
  // (ver `npm run check:no-api-routes`).
  reactStrictMode: true,
};

export default withNextIntl(nextConfig);
