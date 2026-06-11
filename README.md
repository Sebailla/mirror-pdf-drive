---
title: mirror-pdf-drive
author: Sebastián Illa
version: 0.3.0
status: stable
---

# `mirror-pdf-drive`

> Convierte documentación Markdown a PDFs y los sube a Google
> Drive. Runtime-agnostic. Configurable por proyecto.

## ¿Qué es?

Una herramienta CLI que:

1. Lee un árbol de archivos `.md` (por default, el espejo
   español `Documents-es/` de un proyecto).
2. Convierte cada archivo a PDF usando `pandoc` + `weasyprint`.
3. Sube cada PDF a una carpeta de Google Drive.
4. Mantiene idempotencia: si el MD no cambió, no re-renderiza.

## Estado actual

**Diseño completo, pendiente de implementación.**

El diseño vive en [`docs/`](./docs/). Empezá por
[`docs/README.md`](./docs/README.md) para tener el mapa
completo.

## Quick start (post-implementación)

```bash
# Instalar (una vez)
pip install -e .

# Bootstrap (primera vez en un proyecto)
mirror-pdf-drive --init

# Corrida normal
mirror-pdf-drive
```

## Documentación

| Sección | Para qué |
|---|---|
| [`docs/arquitectura/`](./docs/arquitectura/) | Cómo están conectadas las piezas, qué hace cada módulo. |
| [`docs/script/`](./docs/script/) | Diseño del script Python. |
| [`docs/configuracion/`](./docs/configuracion/) | Schema del `mirror-pdf-drive.config.yaml`. |
| [`docs/skill/`](./docs/skill/) | Diseño de la `SKILL.md` de Pi. |
| [`docs/operacion/`](./docs/operacion/) | Cómo correr la herramienta end-to-end. |
| [`docs/referencias/`](./docs/referencias/) | Decisiones de diseño y dependencias. |

## Stack

- **Lenguaje:** Python 3.11+
- **Renderizado:** `pandoc` + `weasyprint`
- **API de Google:** `google-api-python-client` + OAuth
- **Validación de config:** `pydantic` v2
- **Tests:** `pytest`

## Licencia

Por definir.

## Autor

Sebastián Illa.
