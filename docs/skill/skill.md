---
name: mirror-pdf-drive
description: |
  Convierte la documentación Markdown bilingüe (Documents-es/) a PDF
  y la sube a una carpeta de Google Drive. Trigger: /mirror-pdf-drive
  o cuando el usuario pida "convertir docs a PDF y subir a Drive".
version: 0.1.0
author: Sebastián Illa
---

# mirror-pdf-drive

Convierte `Documents-es/` (espejo español) a PDFs y los sube a
una carpeta de Google Drive.

## Cuándo usar esta skill

- El usuario dice "convertir los MD a PDF" o "subir la doc a Drive".
- El usuario corre `/mirror-pdf-drive` explícitamente.
- El usuario quiere regenerar los PDFs después de un cambio
  grande en `Documents-es/`.

## Cuándo NO usar

- El usuario quiere un PDF de un solo archivo para compartir
  manualmente → usá `pandoc` directo.
- El usuario quiere subir archivos que no son `.md` → esta
  skill solo procesa Markdown.
- El usuario está en un repo sin `Documents-es/` ni
  `mirror-pdf-drive.config.yaml` → sugerí crearlo primero.

## Prerrequisitos

### Software (en la máquina del usuario)

- Python 3.11+
- `pandoc` (`brew install pandoc`)
- `pango` y `cairo` para weasyprint (`brew install pango cairo`)
- Deps Python: `pip install weasyprint google-api-python-client
  google-auth-oauthlib pydantic pypandoc pyyaml`

### Credenciales OAuth

- `client_secret.json` bajado de GCP Console (Desktop app OAuth
  Client, con Drive API habilitada).
- Por default vive en `~/.config/mirror-pdf-drive/`.

### Config del proyecto

- `mirror-pdf-drive.config.yaml` en la raíz del proyecto.

## Comandos

| Comando | Cuándo usarlo |
|---|---|
| `/mirror-pdf-drive --init` | Primera vez (bootstrap). |
| `/mirror-pdf-drive` | Corrida normal. |
| `/mirror-pdf-drive --dry-run` | Ver qué haría sin gastar quota. |
| `/mirror-pdf-drive --no-upload` | Solo generar PDFs, sin subir. |
| `/mirror-pdf-drive --force` | Regenerar todo, ignorando mtime. |
| `/mirror-pdf-drive --verbose` | Diagnosticar problemas. |

## Comportamiento esperado

- **Por defecto:** idempotente. PDFs viejos no se re-renderizan
  si el MD no cambió.
- **Errores:** el script imprime qué falló y por qué. Exit
  codes estables (ver sección "Si algo falla").
- **OAuth vencido:** detecta 401, sugiere `--init`.

## Outputs

- **PDFs locales:** en `dist/mirror-pdf-drive/` (relativo al
  config).
- **Archivos subidos:** en la carpeta de Drive configurada
  (default: "Documents-es PDFs" en la raíz de tu Drive).
- **Logs:** en stdout (text) o JSON con `--logging-format json`.

## Variables de entorno

- `MIRROR_PDF_DRIVE_AUTH_DIR`: override del directorio de auth
  (donde están `client_secret.json` y `token.json`).
- `MIRROR_PDF_DRIVE_CONFIG`: override del path al config YAML.

## Si algo falla

| Exit | Significado | Solución |
|---|---|---|
| 0 | Todo OK. | Nada. |
| 1 | Error de config. | Corré con `--verbose`, leé el error, corregí el config. |
| 2 | Auth faltante o vencida. | Corré `/mirror-pdf-drive --init`. |
| 3 | Render falló. | Algunos MD no se pudieron convertir. Pegá el log. |
| 4 | Upload falló. | Algunos PDFs no se pudieron subir. Pegá el log. |
| 5 | Error inesperado. | Probablemente un bug. Pegá el log completo. |

## Mensajes que vas a ver

- **Inicio:** "Iniciando mirror-pdf-drive..."
- **Por archivo:** "Renderizando: {path}" o "Subiendo: {path}"
- **Skip:** "Omitiendo (sin cambios): {path}"
- **Resumen:** "Listo. Renderizados: N. Subidos: M. Omitidos: K. Fallos: F."

## Referencias

- Diseño completo: `~/Documents/Proyectos/2026/mirror-pdf-drive-design/Document-es/`
- Schema del config: `configuracion/schema.md`
- Troubleshooting: `operacion/troubleshooting.md`
- Códigos de error: `operacion/codigos-de-error.md`
