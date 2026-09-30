# Referencias de diseño

Material exportado desde Stitch que sirve de referencia visual para la
plataforma. **No es material del archivo**: son mockups, y sí se versionan.

```
docs/diseno/
├── capturas/    PNG o JPG de cada pantalla
└── codigo/      exportación HTML/CSS de Stitch
```

## Convención de nombres

Nombrar cada archivo por la pantalla que representa, para poder relacionarlo
con la ruta del sitio:

```
capturas/inicio.png
capturas/tema-migrantes.png
capturas/detalle-testimonio.png
capturas/equipo.png
capturas/chatbot.png
capturas/admin-listado.png
```

Si una pantalla tiene variante móvil, agregar el sufijo:

```
capturas/inicio-movil.png
```

## Qué se hace con esto

Las capturas muestran la intención —composición, jerarquía, ritmo— y el código
da los valores exactos. La implementación no copia el HTML de Stitch: extrae de
él las medidas y la estructura, y las expresa con los tokens del sistema de
diseño, para que la paleta siga siendo intercambiable desde
`frontend/src/styles/tokens/`.
