---
title: Schema completo de mirror-pdf-drive.config.yaml
author: Sebastián Illa
version: 0.5.0
status: stable
---

# Schema completo de `mirror-pdf-drive.config.yaml`

Referencia exhaustiva de todos los campos del config. Para
ejemplos reales, ver [`mirror-pdf-drive.config.example.yaml`](../../mirror-pdf-drive.config.example.yaml) en la raíz del repo.

## Estructura de alto nivel

```yaml
version: 1            # Schema version (obligatorio)
source: {...}        # Qué procesar
output: {...}        # Dónde guardar PDFs locales
render: {...}        # Cómo renderizar (tipografía, color, CSS)
drive: {...}         # Dónde y cómo subir a Drive
auth: {...}          # Dónde está el OAuth client y el token
```

## `source`

Define **qué archivos Markdown** se procesan.

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `source.root` | `Path` | (obligatorio) | Debe existir. Relativo al config o absoluto. |
| `source.include` | `list[str]` | `["**/*.md"]` | Globs válidos. |
| `source.exclude` | `list[str]` | `[]` | Globs válidos. Se aplican después de `include`. |
| `source.max_depth` | `int` | `10` | Entero positivo. |

**Ejemplo**:
```yaml
source:
  root: ./docs
  include: ["**/*.md"]
  exclude: ["**/drafts/**"]
  max_depth: 5
```

## `output`

Define **dónde guardar los PDFs locales** antes de subir.

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `output.root` | `Path` | (obligatorio) | Se crea si no existe. |
| `output.clean` | `bool` | `false` | Si es `true`, borra el contenido de `output.root` antes de cada corrida. |

**Ejemplo**:
```yaml
output:
  root: ./dist/mirror-pdf-drive
  clean: false
```

## `render`

Define **cómo renderizar los PDFs**: tipografía, color, márgenes, metadata.

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `render.html_template` | `Path \| None` | `null` | Path a un template HTML de pandoc. Si está set, pandoc usa este template. |
| `render.css_file` | `Path \| None` | `null` | Path a un archivo CSS completo. Si está set, **override total** sobre los defaults de tipografía/color. |
| `render.page_size` | `str` | `"A4"` | `"A4"`, `"Letter"`, `"Legal"`, etc. |
| `render.margins` | `dict[str, float]` | `{top: 2.0, bottom: 2.0, left: 2.0, right: 2.0}` | Cada key en cm. |
| `render.metadata` | `dict[str, str]` | `{title: "Documents-es", author: "Sebastián Illa"}` | Strings. Keys vacíos se ignoran. |

### Tipografía (v0.5.0+)

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `render.font_family` | `str` | `"Inter, Roboto, Helvetica, Arial, sans-serif"` | CSS font-family válido. |
| `render.font_file` | `Path \| None` | `null` | Path a un archivo `.ttf`/`.ttc`/`.otf`. Se embebe via `@font-face`. |

### Colores (v0.5.0+)

Todos validados para **WCAG AA en fondo blanco**.

| Campo | Default | Contraste | Uso |
|---|---|---|---|
| `render.body_color` | `#1a1a1a` | 16.5:1 (AAA) | Texto normal |
| `render.heading_color` | `#000000` | 21:1 (AAA) | Títulos (h1-h6) |
| `render.link_color` | `#0563c1` | 7.4:1 (AAA) | Links |
| `render.code_color` | `#1a1a1a` | 16.5:1 (AAA) | Código inline |
| `render.code_bg_color` | `#f6f8fa` | 1.06:1 (bg) | Background de código |

### Ejemplo completo de `render`

```yaml
render:
  # Custom font
  font_family: "'SF Pro Display', Helvetica, sans-serif"
  font_file: /Users/sebailla/fonts/Inter-Regular.ttf

  # Custom colors
  body_color: "#222222"
  heading_color: "#000000"
  link_color: "#cc0066"

  # Page layout
  page_size: Letter
  margins: {top: 1.0, bottom: 1.0, left: 1.5, right: 1.5}
  metadata:
    title: "Mi Proyecto"
    author: "Sebastián Illa"
    subject: "Documentación del proyecto"
```

### Comportamiento del CSS

- Si `css_file` está set, se usa tal cual. Los defaults de
  tipografía/color **se ignoran**.
- Si `css_file` NO está set, el CLI genera un CSS ad-hoc
  con los defaults arriba y lo cachea en
  `output.root/.mirror-pdf-drive-cache/style-<hash>.css`.
- Runs subsecuentes con la misma config no regeneran el CSS
  (cache hit).
- El CSS generado **no sobrescribe los colores inline** que
  pandoc pone desde el MD. Si el MD tiene
  `<span style="color: #abc">`, ese color gana.

### Targets CSS del default

El CSS generado targetea:

| Target | Propiedades |
|---|---|
| `@page` | size, margin |
| `body` | font-family, color, font-size, line-height |
| `h1`-`h6` | color, font-weight, line-height, margin, font-size |
| `a` | color, text-decoration |
| `a:hover` | text-decoration |
| `code`, `pre`, `kbd`, `samp` | font-family (monospace), color, background-color, padding, border-radius, font-size |
| `pre` | padding, overflow-x, line-height, border-radius |
| `pre code` | background (transparent), padding (0) |
| `blockquote` | border-left, padding-left, color, opacity |
| `table` | border-collapse, margin |
| `th`, `td` | border, padding, text-align |
| `th` | background-color, font-weight |
| `img` | max-width (100%), height (auto) |
| `hr` | border-top |

## `drive`

Define **dónde y cómo subir a Google Drive**.

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `drive.root_folder_id` | `str \| None` | `null` | Folder ID de Google Drive. Obligatorio (junto con `folder_id`). |
| `drive.folder_id` | `str \| None` | `null` | Legacy. Si ambos están, `root_folder_id` gana. |
| `drive.folder_name` | `str` | `"Documents-es PDFs"` | Metadata. NO afecta el upload. |
| `drive.project_folder_name` | `str \| None` | `null` | Override del nombre del subfolder. Si `null`, usa `Path.cwd().name`. |
| `drive.conflict_strategy` | `str` | `"skip"` | `"skip"`, `"replace"`, o `"version"`. |

### Project folder isolation (v0.4.0+)

Cuando corrés `mirror-pdf-drive`, el CLI crea una subcarpeta
con el **nombre del proyecto** dentro de `drive.root_folder_id`.
La estructura de carpetas source se replica adentro.

**Resolución del nombre del subfolder** (en orden):
1. Flag CLI `--project-folder-name <name>` (si está)
2. `drive.project_folder_name` en el config (si está)
3. `Path.cwd().name` (default)

**Ejemplo**:

```yaml
drive:
  root_folder_id: "1AbCdEfGhIjKlMnOpQrStUvWxYz"
  conflict_strategy: skip
```

Corriendo `mirror-pdf-drive` desde `/path/to/gastos-personales/`,
los PDFs van a:
```
<root_folder_id>/gastos-personales/docs/operacion/troubleshooting.pdf
```

### Conflicto strategies

| Strategy | Comportamiento |
|---|---|
| `skip` | Si ya existe un PDF con el mismo nombre, no re-sube. **Default**. |
| `replace` | Sobrescribe el PDF existente. |
| `version` | Crea un nuevo archivo con sufijo `-1`, `-2`, etc. |

## `auth`

Define **dónde está el OAuth client y el token**.

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `auth.dir` | `Path \| None` | `null` | Si `null`, usa `~/.config/mirror-pdf-drive/`. |
| `auth.client_secret_file` | `str` | `"client_secret.json"` | Nombre del archivo dentro de `auth.dir`. |
| `auth.token_file` | `str` | `"token.json"` | Nombre del archivo dentro de `auth.dir`. |

**Override por env var**: `MIRROR_PDF_DRIVE_AUTH_DIR` override de `auth.dir`.

**Ejemplo**:
```yaml
auth:
  dir: ~/.config/mirror-pdf-drive
  # Si querés usar paths custom:
  # dir: ~/my-secure-configs/mirror-pdf-drive
  # client_secret_file: my-client.json
  # token_file: my-token.json
```

## Ejemplo completo

```yaml
version: 1

source:
  root: ./docs
  include: ["**/*.md"]
  exclude: []
  max_depth: 10

output:
  root: ./dist/mirror-pdf-drive
  clean: false

render:
  # Defaults son profesionales, solo customizá lo que necesites
  page_size: A4
  margins: {top: 2.0, bottom: 2.0, left: 2.0, right: 2.0}
  metadata:
    title: "Mi Proyecto"
    author: "Sebastián Illa"
  # Tipografía custom
  font_family: "Inter, Roboto, Helvetica, sans-serif"
  font_file: null
  # Colores custom (validados para WCAG AA)
  body_color: "#1a1a1a"
  heading_color: "#000000"
  link_color: "#0563c1"
  code_color: "#1a1a1a"
  code_bg_color: "#f6f8fa"

drive:
  # Carpeta raíz fija en Drive (ej. "proyectos-archivo")
  root_folder_id: "TU_FOLDER_ID_AQUI"
  # Override del nombre del subfolder (opcional)
  # project_folder_name: "mi-proyecto"
  conflict_strategy: skip

auth:
  dir: ~/.config/mirror-pdf-drive
  client_secret_file: client_secret.json
  token_file: token.json
```

## Versionado

El campo `version: int` es el **schema version**. Si en el
futuro se agregan campos obligatorios o se cambian tipos, se
bumpea. El script rechaza configs con versiones mayores a las
que conoce.

- `version: 1` — schema actual (v0.5.0+)

## Validación

El config se valida con Pydantic v2. Errores comunes:

| Error | Causa | Fix |
|---|---|---|
| `drive config requires either root_folder_id or folder_id` | Ninguno de los dos está set. | Set al menos uno. |
| `invalid conflict_strategy: X` | Strategy no es `skip`/`replace`/`version`. | Usar uno de los 3. |
| `source.root 'X' does not exist` | El directorio no existe. | Verificar la ruta. |
| `pydantic.ValidationError` | Otro campo con tipo incorrecto. | Ver el traceback para el campo exacto. |
