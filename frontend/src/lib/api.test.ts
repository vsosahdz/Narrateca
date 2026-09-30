import { describe, expect, it } from "vitest";

import { groupByType, SECTION_ORDER, type ContentItem, type ContentType } from "./api";

function item(type: ContentType, slug: string): ContentItem {
  return {
    id: slug,
    theme_slug: "migrantes",
    type,
    slug,
    title: slug,
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
  };
}

describe("groupByType", () => {
  it("agrupa las piezas por tipo", () => {
    const groups = groupByType([
      item("testimony", "a"),
      item("interview", "b"),
      item("testimony", "c"),
    ]);

    const testimonies = groups.find(([type]) => type === "testimony")?.[1];
    expect(testimonies?.map((i) => i.slug)).toEqual(["a", "c"]);
  });

  it("omite los tipos sin piezas", () => {
    // Escenario de `public-site`: una sección vacía no debe mostrarse en vez de
    // aparecer con un encabezado y nada debajo.
    const groups = groupByType([item("testimony", "a")]);

    expect(groups.map(([type]) => type)).toEqual(["testimony"]);
    expect(groups).toHaveLength(1);
  });

  it("respeta el orden declarado de secciones", () => {
    const groups = groupByType([item("photo", "f"), item("testimony", "t")]);

    const order = groups.map(([type]) => type);
    const expected = SECTION_ORDER.filter((type) => order.includes(type));
    expect(order).toEqual(expected);
    // El testimonio va antes que la fotografía sin importar el orden de llegada.
    expect(order.indexOf("testimony")).toBeLessThan(order.indexOf("photo"));
  });

  it("deja las noticias fuera: tienen su propia sección", () => {
    // Agruparlas aquí las partiría en dos listas —notas propias por un lado,
    // enlaces curados por otro— que la persona tendría que reconciliar. La
    // sección de noticias las reúne ordenadas por fecha.
    const groups = groupByType([
      item("news_post", "n"),
      item("curated_link", "e"),
      item("testimony", "t"),
    ]);

    expect(groups.map(([type]) => type)).toEqual(["testimony"]);
  });

  it("devuelve una lista vacía cuando no hay contenido", () => {
    expect(groupByType([])).toEqual([]);
  });
});
