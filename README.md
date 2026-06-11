---
title: mirror-pdf-drive
author: Sebastián Illa
version: 0.3.0
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
2. Convierte cada archivo a PDF usando `pandoc` + `weasyprint`.
3. Sube cada PDF a una carpeta de Google Drive (OAuth scope
   `drive.file`).
4. Mantiene idempotencia: si el MD no cambió, no re-renderiza.

## Quick start

```bash
# 1. Instalar (una vez)
pip install mirror-pdf-drive

# 2. Configurar Google Drive OAuth
#    a. Crear proyecto en https://console.cloud.google.com/
#    b. Habilitar Google Drive API
#    c. Crear OAuth 2.0 Client ID tipo "Desktop app"
#    d. Bajar client_secret.json a ~/.config/mirror-pdf-drive/
#    e. Agregar tu email como Test user en el OAuth consent screen

# 3. Crear config del proyecto
cp mirror-pdf-drive.config.example.yaml mirror-pdf-drive.config.yaml
# Editar paths: source.root, output.root, drive.folder_id

# 4. Bootstrap OAuth (primera vez)
mirror-pdf-drive --init

# 5. Corrida normal
mirror-pdf-drive
```

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

**Importante**: instalar `mirror-pdf-drive` en un **venv aislado** evita problemas con `DYLD_LIBRARY_PATH` en macOS:

```bash
python -m venv .venv
source .venv/bin/activate
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
drive:
  folder_id: "tu-folder-id-de-drive"
  conflict_strategy: skip  # skip | replace | version
auth:
  dir: ~/.config/mirror-pdf-drive
```

## Variables de entorno

| Variable | Default | Para qué |
|---|---|---|
| `MIRROR_PDF_DRIVE_AUTH_DIR` | `~/.config/mirror-pdf-drive` | Override del directorio de auth |

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
| `mirror-pdf-drive --folder-id <id>` | Override del folder_id de Drive. |

Exit codes: 0 (OK), 1 (config error), 2 (auth), 3 (render fail), 4 (upload fail), 5 (unexpected).

## Tests

```bash
# Suite completa (unit + integration con Drive real, requiere env var)
MIRROR_PDF_DRIVE_SANDBOX_FOLDER_ID=tu-folder-id pytest -v

# Solo unit (sin credenciales, default en CI)
pytest -q

# Solo integration
pytest -m integration
```

72 tests unitarios, 5 integration, 97% cobertura.

## Documentación

| Sección | Para qué |
|---|---|
| [`docs/arquitectura/`](./docs/arquitectura/) | Cómo están conectadas las piezas, qué hace cada módulo. |
| [`docs/script/`](./docs/script/) | Diseño del script Python. |
| [`docs/configuracion/`](./docs/configuracion/) | Schema del `mirror-pdf-drive.config.yaml`. |
| [`docs/skill/`](./docs/skill/) | Diseño de la `SKILL.md` de Pi. |
| [`docs/operacion/`](./docs/operacion/) | Cómo correr la herramienta end-to-end. |
| [`docs/referencias/`](./docs/referencias/) | Decisiones de diseño y dependencias. |

## Skill de Pi

`mirror-pdf-drive` se activa automáticamente cuando decís algo como "convertir MD a PDF", "subir docs a Drive", o "regenerar los PDFs". La skill vive en `~/.pi/agent/skills/mirror-pdf-drive/`. Ver [`docs/skill/skill.md`](./docs/skill/skill.md) para el diseño.

## Stack

- **Lenguaje:** Python 3.11+
- **Renderizado:** `pandoc` + `weasyprint`
- **API de Google:** `google-api-python-client` + OAuth scope `drive.file`
- **Validación de config:** `pydantic` v2
- **Tests:** `pytest` + `pytest-cov`
- **CI:** GitHub Actions
- **Coverage:** Codecov
- **Distribución:** PyPI / TestPyPI

## Licencia

MIT — ver [`LICENSE`](./LICENSE).

## Autor

Sebastián Illa.
