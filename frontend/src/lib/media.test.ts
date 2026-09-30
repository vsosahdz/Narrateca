import { describe, expect, it } from "vitest";

import type { ContentItem } from "./api";
import { requiresOwnPlayer, subtitleUrl, youTubeId } from "./media";

function item(overrides: Partial<ContentItem>): ContentItem {
  return {
    id: "x",
    theme_slug: "migrantes",
    type: "video",
    slug: "x",
    title: "x",
    summary: null,
    body: null,
    display_name: null,
    attribution: "anonymous",
    sensitivity: "normal",
    media_key: null,
    media_mime: null,
    external_url: null,
    source_name: null,
    alt_text: null,
    recorded_on: null,
    published_at: null,
    ...overrides,
  };
}

describe("requiresOwnPlayer", () => {
  it("exige reproductor propio para material sensible", () => {
    // Un testimonio de una sobreviviente no se incrusta desde un servicio de
    // terceros, aunque exista una dirección externa disponible.
    const sensible = item({
      sensitivity: "high",
      external_url: "https://youtube.com/watch?v=abcdefghijk",
    });

    expect(requiresOwnPlayer(sensible)).toBe(true);
  });

  it("permite servicio externo para material de difusión general", () => {
    const general = item({ sensitivity: "normal" });
    expect(requiresOwnPlayer(general)).toBe(false);
  });
});

describe("subtitleUrl", () => {
  it("deriva ambas pistas del archivo de media", () => {
    expect(subtitleUrl("entrevistas/ent-014.mp4", "es")).toContain("ent-014.es.vtt");
    expect(subtitleUrl("entrevistas/ent-014.mp4", "en")).toContain("ent-014.en.vtt");
  });

  it("sustituye la extensión y no la concatena", () => {
    expect(subtitleUrl("a/b.mp4", "es")).not.toContain(".mp4");
  });
});

describe("youTubeId", () => {
  it.each([
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://www.youtube.com/embed/dQw4w9WgXcQ",
  ])("reconoce %s", (url) => {
    expect(youTubeId(url)).toBe("dQw4w9WgXcQ");
  });

  it("devuelve null para direcciones que no son de YouTube", () => {
    expect(youTubeId("https://ejemplo.mx/nota")).toBeNull();
  });
});
