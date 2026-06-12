---
title: mirror-pdf-drive
author: Sebastián Illa
version: 0.5.0
status: stable
---

# `mirror-pdf-drive`

> Convierte documentación Markdown a PDFs y los sube a Google
> Drive. Runtime-agnostic. Configurable por proyecto.

[![CI](https://github.com/Sebailla/mirror-pdf-drive/actions/workflows/test.yml/badge.svg)](https://github.com/Sebailla/mirror-pdf-drive/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/Sebailla/mirror-pdf-drive/branch/main/graph/badge.svg)](https://codecov.io/gh/Sebailla/mirror-pdf-drive)
[![PyPI version](https://badge.fury.io/py/mirror-pdf-drive.svg)](https://test.pypi.org/project/mirror-pdf-drive/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ¿Qué es?

Una herramienta CLI que:

1. Lee un árbol de archivos `.md` (por default, el espejo
   español `Documents-es/` de un proyecto).
2. Convierte cada archivo a PDF usando `pandoc` + `weasyprint`,
   con tipografía y color configurables (Inter/Roboto por default,
   colores validados WCAG AA en blanco).
3. Sube cada PDF a una **carpeta raíz fija en Google Drive**
   (configurable), creando automáticamente una subcarpeta con el
   nombre del proyecto y replicando la estructura de carpetas
   source.
4. Mantiene idempotencia: si el MD no cambió, no re-renderiza.
5. Escapa comillas simples y backslashes en queries de la API de
   Drive (sin fallos con nombres que tienen `'`, `\`, etc.).

## Quick start

```bash
# 1. Instalar (una vez, en un venv)
python -m venv ~/.venvs/mirror-pdf-drive
source ~/.venvs/mirror-pdf-drive/bin/activate
pip install mirror-pdf-drive

# 2. Configurar Google Drive OAuth (una vez por máquina)
#    a. Crear proyecto en https://console.cloud.google.com/
#    b. Habilitar Google Drive API
#    c. Crear OAuth 2.0 Client ID tipo "Desktop app"
#    d. Bajar client_secret.json a ~/.config/mirror-pdf-drive/
#    e. Agregar tu email como Test user en el OAuth consent screen
#    f. Crear carpeta raíz en Drive (ej. "proyectos-archivo"),
#       copiar el Folder ID de la URL

# 3. Crear config del proyecto
cp mirror-pdf-drive.config.example.yaml mirror-pdf-drive.config.yaml
# Editar: source.root, output.root, drive.root_folder_id

# 4. Bootstrap OAuth (primera vez)
mirror-pdf-drive --init

# 5. Corrida normal
mirror-pdf-drive
```

Para más detalles (incluyendo deps de sistema y troubleshooting),
ver [`docs/operacion/instalar-en-nuevo-repo.md`](./docs/operacion/instalar-en-nuevo-repo.md).

## Dependencias del sistema

| Paquete | Cómo instalar | Para qué |
|---|---|---|
| Python 3.11+ | `brew install python@3.12` | Runtime |
| `pandoc` | `brew install pandoc` | Conversor MD → HTML |
| `pango` | `brew install pango` | Layout de texto (weasyprint) |
| `cairo` | `brew install cairo` | Rendering (weasyprint) |
| `glib` | `brew install glib` | Bindings de bajo nivel |
| `gobject-introspection` | `brew install gobject-introspection` | Bindings |
| `pkg-config` | `brew install pkg-config` | Build de bindings |
| `harfbuzz` | `brew install harfbuzz` | Shaping de texto |
| `fribidi` | `brew install fribidi` | Texto bidireccional |
| `libffi` | `brew install libffi` | FFI |

En Debian/Ubuntu: `apt-get install pandoc libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libpangocairo-1.0-0`.

**Importante**: instalar `mirror-pdf-drive` en un **venv aislado** evita problemas con `DYLD_LIBRARY_PATH` en macOS. WeasyPrint no carga las libs nativas de brew desde el Python del framework, solo desde un venv.

```bash
python -m venv ~/.venvs/mirror-pdf-drive
source ~/.venvs/mirror-pdf-drive/bin/activate
pip install mirror-pdf-drive[dev]
```

## Configuración

Ejemplo completo en [`mirror-pdf-drive.config.example.yaml`](./mirror-pdf-drive.config.example.yaml). Schema detallado en [`docs/configuracion/schema.md`](./docs/configuracion/schema.md).

```yaml
version: 1
source:
  root: ./docs
  include: ["**/*.md"]
output:
  root: ./dist
render: {}                    # defaults son profesionales, ver abajo
drive:
  root_folder_id: "..."       # carpeta raíz fija en Drive (ej. "proyectos-archivo")
  # folder_id: "..."          # legacy, root_folder_id gana
  # project_folder_name: "..." # override del nombre del subfolder
  conflict_strategy: skip      # skip | replace | version
auth:
  dir: ~/.config/mirror-pdf-drive
```

## Tipografía y color (v0.5.0+)

`RenderConfig` genera un CSS por default con tipografía y color
profesionales. Todos los defaults están validados para **WCAG AA
en fondo blanco** (contraste ≥ 4.5:1 para texto normal, ≥ 3:1
para texto grande).

| Campo | Default | Notas |
|---|---|---|
| `font_family` | `Inter, Roboto, Helvetica, Arial, sans-serif` | Inter/Roboto como preferred (Google Fonts populares), fallback a fonts del sistema. |
| `font_file` | `null` | Path opcional a un `.ttf`/`.otf` para embeber via `@font-face`. |
| `body_color` | `#1a1a1a` | Near-black. Contraste 16.5:1 (AAA). |
| `heading_color` | `#000000` | Pure black. Contraste 21:1 (AAA). |
| `link_color` | `#0563c1` | Office blue. Contraste 7.4:1 (AAA). |
| `code_color` | `#1a1a1a` | Match body. |
| `code_bg_color` | `#f6f8fa` | GitHub-style very light gray. Background, no text. |

**Importante**: el CSS generado **no sobrescribe los colores inline**
que pandoc pone desde el MD. Si el MD tiene `<span style="color: #abc">`,
ese color se preserva. Los defaults solo aplican a elementos sin
color explícito.

**Customización**:

```yaml
render:
  font_family: "'SF Pro Display', Helvetica, sans-serif"  # custom font stack
  font_file: ~/fonts/Inter-Regular.ttf                  # embeber font custom
  body_color: "#222222"                                # un poco más claro
  link_color: "#cc0066"                                # links rojos
```

Para control total del CSS, pasá un archivo completo:

```yaml
render:
  css_file: ~/my-custom-styles.css  # override total, los defaults se ignoran
```

El CSS se cachea en `output.root/.mirror-pdf-drive-cache/`
con un hash de la config, así no se regenera en cada corrida.

## Project folder isolation (v0.4.0+)

Cuando corrés `mirror-pdf-drive`, el CLI crea automáticamente una
subcarpeta con el **nombre del proyecto** dentro de
`drive.root_folder_id`. La estructura de carpetas source se
replica adentro.

**Ejemplo**:

Source:
```
docs/operacion/troubleshooting.md
```

En Drive:
```
<root_folder>/<proyecto>/docs/operacion/troubleshooting.pdf
```

- Default: el nombre del proyecto es `Path.cwd().name` (la
  carpeta desde donde corrés el CLI).
- Override: `drive.project_folder_name: "mi-proyecto"` en el
  config, o `--project-folder-name "mi-proyecto"` en la CLI.

## Variables de entorno

| Variable | Default | Para qué |
|---|---|---|
| `MIRROR_PDF_DRIVE_AUTH_DIR` | `~/.config/mirror-pdf-drive` | Override del directorio de auth (donde están `client_secret.json` y `token.json`). |
| `MIRROR_PDF_DRIVE_SANDBOX_FOLDER_ID` | (ninguno) | Folder ID del sandbox en Drive. Requerido solo para correr los integration tests. |

## Comandos

| Comando | Para qué |
|---|---|
| `mirror-pdf-drive --version` | Imprime versión y sale. |
| `mirror-pdf-drive --init` | **Primera vez.** Hace el OAuth flow y guarda el token. |
| `mirror-pdf-drive` | Corrida normal. Idempotente. |
| `mirror-pdf-drive --dry-run` | Muestra qué haría sin gastar quota. |
| `mirror-pdf-drive --no-upload` | Solo genera PDFs locales. |
| `mirror-pdf-drive --force` | Regenera todo, ignorando mtime. |
| `mirror-pdf-drive --verbose` | Logs en DEBUG. |
| `mirror-pdf-drive --config <path>` | Override del path al YAML. |
| `mirror-pdf-drive --source-dir <p>` | Override del `source.root`. |
| `mirror-pdf-drive --output-dir <p>` | Override del `output.root`. |
| `mirror-pdf-drive --folder-id <id>` | Override del `folder_id` legacy. |
| `mirror-pdf-drive --project-folder-name <name>` | Override del nombre del subfolder del proyecto. |

Exit codes: 0 (OK), 1 (config), 2 (auth), 3 (render), 4 (upload), 5 (unexpected). "Worst-wins" priority.

## Tests

```bash
# Suite completa (unit + integration con Drive real, requiere env var)
MIRROR_PDF_DRIVE_SANDBOX_FOLDER_ID=tu-folder-id pytest -v

# Solo unit (sin credenciales, default en CI)
pytest -q

# Solo integration
pytest -m integration
```

100 tests unitarios, 6 integration, 97% cobertura.

## Documentación

| Sección | Para qué |
|---|---|
| [`docs/operacion/instalar-en-nuevo-repo.md`](./docs/operacion/instalar-en-nuevo-repo.md) | Setup paso a paso en un proyecto nuevo (recomendado leer primero). |
| [`docs/operacion/validar-skill-pi.md`](./docs/operacion/validar-skill-pi.md) | Validar que la skill de Pi funciona. |
| [`docs/operacion/troubleshooting.md`](./docs/operacion/troubleshooting.md) | Diagnóstico de problemas comunes. |
| [`docs/operacion/codigos-de-error.md`](./docs/operacion/codigos-de-error.md) | Exit codes y errores. |
| [`docs/arquitectura/`](./docs/arquitectura/) | Cómo están conectadas las piezas, qué hace cada módulo. |
| [`docs/script/`](./docs/script/) | Diseño del script Python. |
| [`docs/configuracion/`](./docs/configuracion/) | Schema del `mirror-pdf-drive.config.yaml`. |
| [`docs/skill/`](./docs/skill/skill.md) | Diseño de la `SKILL.md` de Pi. |
| [`docs/referencias/`](./docs/referencias/) | Decisiones de diseño y dependencias. |

## Skill de Pi

`mirror-pdf-drive` se activa automáticamente cuando decís algo como "convertir MD a PDF", "subir docs a Drive", o "regenerar los PDFs". La skill vive en `~/.pi/agent/skills/mirror-pdf-drive/`. Ver [`docs/skill/skill.md`](./docs/skill/skill.md) para el diseño y [`docs/operacion/validar-skill-pi.md`](./docs/operacion/validar-skill-pi.md) para validar que funciona.

## Stack

- **Lenguaje:** Python 3.11+
- **Renderizado:** `pandoc` + `weasyprint`
- **API de Google:** `google-api-python-client` + OAuth scope `drive.file`
- **Validación de config:** `pydantic` v2
- **Tests:** `pytest` + `pytest-cov`
- **CI:** GitHub Actions (matrix ubuntu + macos, Python 3.11 + 3.12)
- **Coverage:** Codecov (96% con branch coverage)
- **Estrategia de merge:** rebase-merge exclusivo
- **Distribución:** TestPyPI (v0.3.0), pendiente PyPI real

## Releases

- **v0.5.0** — Tipografía y color configurables (Inter/Roboto, WCAG AA)
- **v0.4.1** — Fix: escapar comillas simples en queries de Drive
- **v0.4.0** — Project folder isolation: cada proyecto tiene su subcarpeta en Drive
- **v0.3.1** — Skill de Pi reescrita con workflow imperativo
- **v0.3.0** — Integration tests contra Google Drive real + bugfix
- **v0.2.0** — CI workflow + skill de Pi + runtime
- **v0.1.0** — Primera versión estable

## Licencia

MIT — ver [`LICENSE`](./LICENSE).

## Autor

Sebastián Illa.
