import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Field } from "./Field";

/**
 * Estas pruebas verifican la accesibilidad del campo, no su apariencia.
 *
 * La asociación entre etiqueta, ayuda y error no se ve: un campo puede verse
 * perfecto y ser inutilizable con lector de pantalla. Por eso las consultas usan
 * el nombre accesible y no clases de CSS.
 */
describe("Field", () => {
  it("asocia la etiqueta con el campo", () => {
    render(<Field label="Texto alternativo" />);

    // getByLabelText falla si la etiqueta no está asociada con htmlFor/id.
    expect(screen.getByLabelText("Texto alternativo")).toBeInTheDocument();
  });

  it("anuncia el texto de ayuda mediante aria-describedby", () => {
    render(<Field label="Título" hint="Máximo 160 caracteres" />);

    expect(screen.getByLabelText("Título")).toHaveAccessibleDescription(
      "Máximo 160 caracteres",
    );
  });

  it("marca el campo como inválido y anuncia el error", () => {
    render(<Field label="Título" error="El título es obligatorio" />);

    const input = screen.getByLabelText("Título");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("El título es obligatorio");
  });

  it("comunica el error con texto y no solo con color", () => {
    render(<Field label="Título" error="El título es obligatorio" />);

    // WCAG 2.2 SC 1.4.1: el color no puede ser el único medio de transmitir
    // información. El error debe existir como texto anunciable.
    expect(screen.getByRole("alert")).toHaveTextContent("El título es obligatorio");
  });

  it("anuncia que un campo es obligatorio sin depender del asterisco", () => {
    render(<Field label="Título" required />);

    const input = screen.getByLabelText(/Título/);
    expect(input).toBeRequired();
    expect(screen.getByText("(obligatorio)")).toBeInTheDocument();
  });

  it("genera identificadores distintos para varios campos", () => {
    render(
      <>
        <Field label="Primero" />
        <Field label="Segundo" />
      </>,
    );

    const first = screen.getByLabelText("Primero");
    const second = screen.getByLabelText("Segundo");
    expect(first.id).not.toBe(second.id);
  });
});
