# Script — Renderizado MD a PDF

> **Por qué pandoc + weasyprint y no otra herramienta, cómo
> extender el renderizado, y qué decisiones de tipografía
> están embebidas en el diseño.**

## Decisión de motor: pandoc + weasyprint

### Por qué pandoc

- Es el estándar de facto para conversión de Markdown a
  otros formatos. Si tenés un `.md`, pandoc lo entiende.
- Maneja la mayoría de las extensiones de Markdown
  (CommonMark, GFM, MultiMarkdown, Pandoc Markdown).
- Tiene un ecosistema de filtros (pandoc-crossref, pandoc-
  citeproc) que se pueden agregar sin cambiar el script.
- Es un binario independiente, lo que hace fácil diagnosticar
  problemas con `pandoc archivo.md -o archivo.pdf` directo.

### Por qué weasyprint como engine de PDF

- weasyprint es un motor de PDF basado en HTML + CSS, lo que
  significa que podés controlar la tipografía y el layout
  con CSS estándar.
- Es Python puro (con libs nativas), lo que simplifica la
  instalación con `pip install weasyprint`.
- Soporta `@page`, fuentes web, márgenes, headers/footers,
  numeración de páginas.
- Es **más liviano** que un Chromium headless (wkhtmltopdf,
  puppeteer): no necesita un browser, solo rendering engine.

### Por qué no las alternativas

| Alternativa | Por qué no |
|---|---|
| `wkhtmltopdf` | Usa un Qt WebKit viejo. Dependencias pesadas. Desarrollo estancado. |
| `puppeteer` / `playwright` | Traen un Chromium completo. Pesado, lento de instalar, overkill para un PDF de doc. |
| `mkdocs` + `mkdocs-with-pdf` | Genera un sitio web primero, después lo convierte. Más complejo, más lento, menos control. |
| `md-to-pdf` (Node) | Otra dependencia de Node. No aporta nada sobre pandoc + weasyprint. |
| Subir el MD a Drive como Doc y exportar a PDF | Pierde control sobre tipografía. Depende de la conversión de Drive, que es inconsistente. |

## Flujo de renderizado

```
   ┌──────────────┐
   │ archivo.md   │
   └──────┬───────┘
          │
          ▼
   ┌──────────────────────────────────┐
   │ pandoc archivo.md                │
   │   --pdf-engine=weasyprint        │
   │   -V papersize=A4                │
   │   -V author=...                  │
   │   -c estilos.css  (opcional)     │
   │   --template=...  (opcional)     │
   └──────┬───────────────────────────┘
          │
          ▼
   ┌──────────────┐
   │ archivo.pdf  │
   └──────────────┘
```

Pandoc hace:
1. Parsea el `.md` a AST.
2. Lo convierte a HTML usando la plantilla o el default.
3. Le pasa el HTML a weasyprint.
4. weasyprint renderiza el HTML con el CSS y genera el PDF.

## Argumentos de pandoc que usa el script

Lista completa de los flags que el script pasa a pandoc:

| Flag | Cuándo | Default | Por qué |
|---|---|---|---|
| `--pdf-engine=weasyprint` | siempre | weasyprint | Fijo por decisión de arquitectura. |
| `-V papersize={A4\|Letter\|Legal}` | siempre | A4 | Configurable. |
| `--template={path}` | si `render.htmlTemplate` está seteado | none | Plantilla Pandoc. |
| `-c {path}` | si `render.cssFile` está seteado | none | CSS extra. |
| `-V {key}={value}` | por cada `render.metadata` | title, author | Metadata del PDF. |

## Metadata del PDF

El PDF generado tiene metadata accesible desde el visor y
desde Google Drive:

| Campo | Default | Configurable | Uso |
|---|---|---|---|
| `title` | "Documents-es" | sí (`render.metadata.title`) | Título que muestra el visor de PDF y el nombre en Drive si querés. |
| `author` | "Sebastián Illa" | sí (`render.metadata.author`) | Quién generó el PDF. |
| `subject` | null | sí | Descripción corta. |
| `keywords` | null | sí | Tags separados por coma. |
| `creator` | "mirror-pdf-drive" | no | La herramienta que lo generó. Hard-coded. |

**Por qué `author` default a "Sebastián Illa":** el AGENTS.md
del proyecto define que toda la doc generada tiene como autor
a Sebastián Illa. El script respeta esa convención.

## Estilos CSS

### Default embebido

Si `render.cssFile` no está seteado, el script usa un CSS
mínimo embebido en el código:

```css
@page {
  size: A4;
  margin: 2cm;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
               Roboto, "Helvetica Neue", sans-serif;
  font-size: 11pt;
  line-height: 1.5;
  color: #333;
  max-width: 100%;
}

h1, h2, h3, h4, h5, h6 {
  font-weight: 600;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}

h1 { font-size: 24pt; border-bottom: 1px solid #ccc; padding-bottom: 0.3em; }
h2 { font-size: 18pt; }
h3 { font-size: 14pt; }
h4 { font-size: 12pt; }

code, pre {
  font-family: "SF Mono", Menlo, Consolas, monospace;
  font-size: 10pt;
  background: #f4f4f4;
  border-radius: 3px;
}

pre {
  padding: 0.8em;
  overflow-x: auto;
  border-left: 3px solid #ccc;
}

code {
  padding: 0.1em 0.3em;
}

pre code {
  background: transparent;
  padding: 0;
  border: none;
}

blockquote {
  border-left: 4px solid #ccc;
  margin-left: 0;
  padding-left: 1em;
  color: #666;
  font-style: italic;
}

table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}

th, td {
  border: 1px solid #ddd;
  padding: 0.5em;
  text-align: left;
}

th {
  background: #f4f4f4;
  font-weight: 600;
}

a {
  color: #0066cc;
  text-decoration: none;
}

img {
  max-width: 100%;
  height: auto;
}
```

### Custom

Si querés tu propio CSS (por ejemplo, con la paleta de tu
proyecto), apuntá `render.cssFile` a un archivo `.css`
dentro del repo. El path es relativo a la raíz del proyecto
(donde está el config) o absoluto.

## Plantillas Pandoc

Pandoc soporta plantillas para controlar el HTML intermedio.
Si querés cambiar la estructura (por ejemplo, agregar un
header/footer con fecha de generación), podés:

1. Crear un archivo `template.html` en tu repo.
2. Apuntar `render.htmlTemplate` a ese archivo.

**Cuándo se necesita una plantilla vs. solo CSS:** las
plantillas controlan la **estructura** (qué bloques HTML
existen, dónde van). El CSS controla la **apariencia** (cómo
se ven esos bloques). Cambios de color, fuente, márgenes →
CSS. Cambios de layout, agregar página de portada, numeración
custom → plantilla.

## Manejo de errores de renderizado

Pandoc puede fallar por:

- **MD malformado** (sintaxis inválida).
- **Imagen referenciada que no existe** (`![alt](ruta/rota.png)`).
- **Link a un archivo local que no se puede embeber**.
- **Plantilla HTML inválida**.

El script captura `RuntimeError` de `pypandoc` y lo envuelve
en `RenderFailedError` con el path del MD y el mensaje de
pandoc. El usuario ve:

```
Error: No se pudo renderizar Documents-es/posts/2024-01-15.md
  Contexto: pandoc failed with exit code 1
  Sugerencia: abrí el MD localmente y verificá que pandoc pueda convertirlo
```

## Diagnóstico manual

Si querés verificar por qué un MD específico no se renderiza:

```bash
# Render manual con pandoc
pandoc Documents-es/posts/2024-01-15.md \
  --pdf-engine=weasyprint \
  -V papersize=A4 \
  -o /tmp/test.pdf

# Si pandoc directo funciona pero el script falla, el problema
# está en los argumentos extra que pasa el script. Compará con:
pandoc $(mirror-pdf-drive --verbose 2>&1 | grep "extra_args" | head -1)
```

## Performance

Tiempos aproximados en una MacBook Pro M2:

| Operación | Tiempo por archivo |
|---|---|
| `pandoc` + weasyprint (MD pequeño, <5KB) | 200-500ms |
| `pandoc` + weasyprint (MD mediano, 5-50KB) | 500ms-2s |
| `pandoc` + weasyprint (MD grande, >50KB) | 2-10s |
| Subida a Drive (PDF de 1MB) | 500ms-1s |
| Subida a Drive (PDF de 10MB) | 2-5s |

**Implicación:** para el caso de uso típico (doc de un
proyecto, decenas de MDs, total < 5MB), una corrida
completa tarda **menos de 1 minuto**. No necesita
optimización de performance.

**Si en el futuro se vuelve lento** (cientos de archivos o
archivos muy grandes), las optimizaciones son:

1. **Paralelizar el renderizado** con `concurrent.futures`.
   Renderizar es CPU-bound, así que `ProcessPoolExecutor`
   es lo indicado.
2. **Cachear PDFs** por hash del MD en vez de por `mtime`.
   Más robusto contra cambios de timestamp.
3. **Batch upload** con la API multipart de Drive.
