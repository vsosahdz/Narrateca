# Imagen del frontend de NarraTECa.
#
# Usa la salida `standalone` de Next.js, que empaqueta solo los módulos que la
# aplicación realmente importa en lugar de todo `node_modules`. Con
# `min_instances = 0` eso se nota: menos que copiar al arrancar.

# --- Etapa de dependencias ---------------------------------------------------
FROM node:22-alpine AS deps

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- Etapa de construcción ---------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# La dirección de la API se fija en el build porque
# `NEXT_PUBLIC_API_BASE_URL` viaja al navegador y debe quedar incrustada en el
# código del cliente. Cambiarla exige reconstruir la imagen, y por eso cada
# ambiente tiene la suya.
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_MEDIA_BASE_URL
ARG API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_MEDIA_BASE_URL=$NEXT_PUBLIC_MEDIA_BASE_URL \
    API_BASE_URL=$API_BASE_URL \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# --- Imagen final ------------------------------------------------------------
FROM node:22-alpine AS runtime

RUN addgroup -g 10001 narrateca && adduser -D -u 10001 -G narrateca narrateca

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=8080 \
    HOSTNAME=0.0.0.0

COPY --from=build --chown=narrateca:narrateca /app/.next/standalone ./
COPY --from=build --chown=narrateca:narrateca /app/.next/static ./.next/static
COPY --from=build --chown=narrateca:narrateca /app/public ./public

USER narrateca
EXPOSE 8080

CMD ["node", "server.js"]
