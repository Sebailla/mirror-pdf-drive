# Arquitectura — Descripción General

> **Lee esto primero si vas a modificar la separación de archivos
> del script o agregar un componente nuevo.**

## Visión de una corrida

```
                    ┌────────────────────────────────────┐
                    │  Usuario (vos) en shell o Pi       │
                    └────────────────┬───────────────────┘
                                     │
                                     │ ejecuta
                                     ▼
                    ┌────────────────────────────────────┐
                    │  Binario: mirror-pdf-drive         │
                    │  (Python entrypoint en mirror.py)  │
                    └────────────────┬───────────────────┘
                                     │
                                     │ 1. parsea args
                                     │ 2. carga config
                                     │ 3. para cada MD:
                                     │      a. renderiza
                                     │      b. sube
                                     │ 4. resume
                                     ▼
              ┌──────────────────────┴──────────────────────┐
              │                                             │
              ▼                                             ▼
   ┌──────────────────────┐                    ┌──────────────────────┐
   │ Módulos locales      │                    │ Servicios externos   │
   │ (mismo proceso)      │                    │                      │
   │                      │                    │  - pandoc +          │
   │  config.py           │                    │    weasyprint        │
   │  renderer.py         │                    │  - Google Drive API  │
   │  drive_client.py     │                    │                      │
   │  auth.py             │                    │                      │
   │  exceptions.py       │                    │                      │
   └──────────────────────┘                    └──────────────────────┘
```

## Las tres capas

La herramienta tiene **tres capas conceptuales**. Los archivos
del script están en una sola carpeta plana (`~/.local/share/
mirror-pdf-drive/`), pero conceptualmente cumplen uno de estos
tres roles:

| Capa | Responsabilidad | Archivos | Puede fallar sin que el resto funcione |
|---|---|---|---|
| **Orquestación** | Decide qué se hace, en qué orden, con qué argumentos. | `mirror.py` | Sí (es el entrypoint) |
| **Módulos de trabajo** | Hacen una cosa bien. Renderizan, suben, autentican, validan config. | `renderer.py`, `drive_client.py`, `auth.py`, `config.py` | Sí (cada uno es testeable por separado) |
| **Contratos** | Definen qué errores existen, qué datos se pasan entre módulos. | `exceptions.py`, los dataclasses/Pydantic models de `config.py` | No (los importan todos) |

**Por qué una sola carpeta plana y no capas en subcarpetas:**

El script es chico (6 archivos, ~600 líneas estimadas). Crear
`mirror_pdf_drive/core/`, `mirror_pdf_drive/integrations/`, etc.
sería over-engineering. Si el script crece más de 1500 líneas
totales o aparece un segundo binario, **entonces** se refactoriza
a paquete con subcarpetas. Mientras tanto, plano.

## Interfaces entre módulos

Los módulos **no se importan entre sí directamente**. Cada módulo
expone funciones puras que reciben datos primitivos o dataclasses
y devuelven datos primitivos o dataclasses. La orquestación
(`mirror.py`) es la única que compone los módulos.

```python
# config.py expone:
@dataclass
class MirrorConfig:
    source: SourceConfig
    output: OutputConfig
    render: RenderConfig
    drive: DriveConfig
    auth: AuthConfig

def load_config(path: Path) -> MirrorConfig: ...

# renderer.py expone:
def render_markdown_to_pdf(
    md_path: Path,
    output_path: Path,
    config: RenderConfig,
) -> Path: ...

# drive_client.py expone:
def upload_pdf(
    pdf_path: Path,
    drive_service: Resource,  # cliente ya autenticado
    folder_id: str,
    conflict_strategy: str,
) -> str:  # devuelve el ID de Drive del archivo subido
    ...

# auth.py expone:
def get_drive_service(config: AuthConfig) -> Resource: ...
def run_oauth_flow(config: AuthConfig) -> None: ...

# exceptions.py expone:
class AppError(Exception):
    code: str
    context: dict

class ConfigNotFoundError(AppError): ...
class AuthRequiredError(AppError): ...
class RenderFailedError(AppError): ...
class UploadFailedError(AppError): ...
class InvalidConfigError(AppError): ...
```

**Por qué interfaces explícitas:**

- **Testeable.** `renderer.py` se puede testear con un
  `RenderConfig` mock sin tocar Drive ni auth.
- **Sustituible.** Si mañana querés cambiar `pandoc` por
  `mkdocs`, solo cambia `renderer.py`. El resto no se entera.
- **Documentado por el código.** Las funciones públicas son
  el contrato. No hace falta leer el cuerpo para saber qué hace
  cada módulo.

## Flujo de datos en una corrida exitosa

```
mirror.py:main()
    │
    ├── args = parse_argv()
    │
    ├── config = config.load_config(args.config_path)
    │       │
    │       └─► (lanza InvalidConfigError si el YAML está mal)
    │
    ├── drive_service = auth.get_drive_service(config.auth)
    │       │
    │       └─► (lanza AuthRequiredError si no hay token)
    │
    ├── markdown_files = discover_files(config.source)
    │
    ├── for md_path in markdown_files:
    │       │
    │       ├── pdf_path = compute_output_path(md_path, config)
    │       │
    │       ├── if pdf_exists_and_is_newer(pdf_path, md_path) and not args.force:
    │       │       log("skip", md_path)
    │       │       continue
    │       │
    │       ├── pdf_path = renderer.render_markdown_to_pdf(...)
    │       │       │
    │       │       └─► (lanza RenderFailedError si pandoc falla)
    │       │
    │       └── if not args.no_upload:
    │               file_id = drive_client.upload_pdf(...)
    │               │
    │               └─► (lanza UploadFailedError si la API falla)
    │
    ├── print_summary(stats)
    │
    └── exit(stats.worst_exit_code)
```

## Lo que **no** hace la arquitectura

- **No hay estado global.** Cada corrida es independiente. No
  hay caches en memoria, no hay conexiones persistentes (más
  allá del token de OAuth en disco).
- **No hay async.** El script es secuencial. Renderizar es CPU-
  bound, subir es I/O-bound, pero la diferencia de performance
  entre `requests` secuencial y `aiohttp` no justifica la
  complejidad para el caso de uso (decenas de archivos, no
  miles).
- **No hay base de datos.** El estado se mantiene en el sistema
  de archivos (PDFs, tokens, config) y en Google Drive. No
  necesita estado propio.
- **No hay web server.** Es un CLI. Si en el futuro se quiere
  exponer como API, se agrega un entrypoint `serve.py` que
  reutiliza los módulos, pero el script CLI es la fuente de
  verdad.

## Puntos de extensión

Si necesitás agregar funcionalidad, estos son los puntos
naturales de extensión **sin romper la arquitectura**:

| Querés agregar... | Tocá... | No toques... |
|---|---|---|
| Un nuevo formato de output (ej. DOCX además de PDF) | `renderer.py` (agregá una función `render_markdown_to_docx`) | `mirror.py` (solo agregar un flag) |
| Otra estrategia de upload (ej. S3 además de Drive) | `drive_client.py` → renombrarlo a `uploader.py` con un dispatcher | El resto |
| Un nuevo campo de config | `config.py` (agregá el campo al dataclass y al schema YAML) | Los módulos consumidores (reciben `MirrorConfig` ya actualizado) |
| Un nuevo código de error | `exceptions.py` (subclase de `AppError`) | `mirror.py` (el handler genérico lo agarra) |
| Un nuevo subcomando CLI | `mirror.py` (agregá al `argparse`) | El resto |
| Validación custom del MD antes de renderizar | `renderer.py` (agregá al inicio) | `config.py` (la validación del config es ortogonal) |

## Puntos de **no** extensión (no tocar)

- **El dataclass `MirrorConfig`.** Es la interfaz pública. Si lo
  cambiás, rompés todos los módulos. Si necesitás un campo nuevo,
  agregalo al final con default razonable.
- **Los códigos de error en `exceptions.py`.** Son el contrato con
  la skill de Pi. Cambiarlos rompe la integración. Si agregás
  uno nuevo, documentá el código en `operacion/codigos-de-error.md`.
- **Las dependencias externas listadas en `script/dependencias.md`.**
  Cualquier cambio requiere una decisión arquitectónica, no un
  simple bump de versión.
