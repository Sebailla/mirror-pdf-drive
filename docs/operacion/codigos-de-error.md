# Operación — Códigos de Error

> **Referencia de los exit codes y los códigos de error que la
> herramienta puede devolver. Para diagnóstico paso a paso, ver
> [`troubleshooting.md`](./troubleshooting.md).**

## Exit codes

| Code | Constante | Significado |
|---|---|---|
| 0 | `EXIT_OK` | Todo salió bien. |
| 1 | `EXIT_CONFIG_ERROR` | El config no existe, no se puede parsear, o la validación falló. |
| 2 | `EXIT_AUTH_REQUIRED` | No hay token OAuth, o venció y no se pudo refrescar. |
| 3 | `EXIT_RENDER_FAILED` | Uno o más archivos no se pudieron renderizar. |
| 4 | `EXIT_UPLOAD_FAILED` | Uno o más archivos no se pudieron subir a Drive. |
| 5 | `EXIT_UNEXPECTED` | Un error no clasificado. Probablemente un bug. Reportar. |

## Códigos de error (campo `code` de `AppError`)

Estos códigos aparecen en los logs y en los mensajes de
error. Son **estables** entre versiones (no se renombran
sin bump MAJOR).

| Code | Cuándo se lanza | Solución |
|---|---|---|
| `CONFIG_NOT_FOUND` | El archivo `mirror-pdf-drive.config.yaml` no existe en el path esperado. | Crear el config o pasar `--config PATH`. |
| `INVALID_CONFIG` | El config existe pero la validación falló (campo faltante, tipo incorrecto, valor inválido). | Leer el mensaje de error, corregir el config. |
| `AUTH_REQUIRED` | No hay `token.json` o venció y no se puede refrescar. | Correr `mirror-pdf-drive --init`. |
| `RENDER_FAILED` | pandoc no pudo convertir un MD a PDF. | Verificar que pandoc está instalado, que el MD es válido, que las imágenes referenciadas existen. |
| `UPLOAD_FAILED` | La API de Drive devolvió un error al subir un PDF. | Verificar quota de Drive, permisos de la carpeta destino, conexión a internet. |
| `APP_ERROR` | Error genérico que no encaja en los anteriores. | Reportar como bug. |

## Cómo se ven en los logs

### Ejemplo de error de config

```
ERROR [INVALID_CONFIG] Config validation failed: mirror-pdf-drive.config.yaml
  context:
    path: "mirror-pdf-drive.config.yaml"
    errors:
      - source.root: Path does not exist: 'Document-es' (got: Document-es)
      - render.pageSize: invalid value 'A5', must be one of A4, Letter, Legal
```

### Ejemplo de error de auth

```
ERROR [AUTH_REQUIRED] OAuth token not found or invalid
  context:
    auth_dir: "/Users/seba/.config/mirror-pdf-drive"
  suggestion: Run 'mirror-pdf-drive --init' to authenticate
```

### Ejemplo de error de render

```
ERROR [RENDER_FAILED] pandoc failed to render Documents-es/posts/2024-01-15.md
  context:
    md_path: "Documents-es/posts/2024-01-15.md"
    output_path: "dist/mirror-pdf-drive/posts/2024-01-15.pdf"
    pandoc_error: "pandoc: Documents-es/posts/2024-01-15.md:25:51: could not find image `missing.png'"
```

### Ejemplo de error de upload

```
ERROR [UPLOAD_FAILED] Failed to upload AGENTS.pdf
  context:
    pdf_path: "dist/mirror-pdf-drive/AGENTS.pdf"
    api_error: "<HttpError 403 when requesting ... returned \"The user's Drive storage quota has been exceeded.\">"
  suggestion: Free up space in your Google Drive or use a different account
```

## Exit code vs código de error

**No son lo mismo.** El exit code es un número del 0 al 5.
El código de error es un string estable.

- **Un exit code** = el resultado agregado de toda la corrida.
- **Un código de error** = el detalle de un fallo específico.

Una corrida puede tener:
- Exit 0 + un `WARNING` (no hubo errores, pero algo fue raro).
- Exit 3 + un `RENDER_FAILED` para un archivo específico.
- Exit 4 + tres `UPLOAD_FAILED` (tres archivos fallaron).
- Exit 1 + un `INVALID_CONFIG` (el config está mal).

## Tabla rápida de diagnóstico

| Exit | Code más probable | Qué revisar primero |
|---|---|---|
| 0 | (ninguno) | Nada, salió bien. |
| 1 | `CONFIG_NOT_FOUND` o `INVALID_CONFIG` | El archivo `mirror-pdf-drive.config.yaml`. |
| 2 | `AUTH_REQUIRED` | El `token.json` y el `client_secret.json`. |
| 3 | `RENDER_FAILED` | Los MD que fallaron (aparecen en el log). |
| 4 | `UPLOAD_FAILED` | Tu cuenta de Drive (quota, permisos, conexión). |
| 5 | (variable) | El log completo, probablemente un bug. |

## Cómo pegar un error en un issue

Cuando reportes un problema, incluí:

1. **El comando que corriste** (con flags).
2. **El exit code**.
3. **El mensaje de error completo** (con el `code` y el
   `context`).
4. **El log completo** con `--verbose`.
5. **Tu OS y versión** (macOS 14.4, Ubuntu 22.04, etc.).
6. **Versión de la herramienta** (`mirror-pdf-drive --version`).
7. **Versión de pandoc** (`pandoc --version`).
8. **Versión de Python** (`python --version`).
