# Script — Módulos

> **Diseño detallado de cada archivo Python que forma parte del
> script. Para la separación de archivos y por qué cada uno
> existe, ver [`../arquitectura/separacion-de-archivos.md`](../arquitectura/separacion-de-archivos.md).**

## `mirror.py` — Orquestador

### Función pública

```python
def main(argv: list[str] | None = None) -> int:
    """
    Entry point del CLI.
    
    Parsea args, carga config, autentica, renderiza y sube.
    Devuelve un exit code (ver ../operacion/codigos-de-error.md).
    """
```

### Estructura interna

```python
# Constantes al inicio
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_AUTH_REQUIRED = 2
EXIT_RENDER_FAILED = 3
EXIT_UPLOAD_FAILED = 4
EXIT_UNEXPECTED = 5

def main(argv):
    args = parse_argv(argv)
    return run(args)

def run(args) -> int:
    try:
        config = config.load_config(args.config_path)
    except exceptions.InvalidConfigError as e:
        log_error(e)
        return EXIT_CONFIG_ERROR
    
    try:
        drive_service = auth.get_drive_service(config.auth)
    except exceptions.AuthRequiredError as e:
        log_error(e)
        return EXIT_AUTH_REQUIRED
    
    stats = Stats()
    for md_path in discover_files(config.source, args.paths):
        try:
            pdf_path = render_or_skip(md_path, config, args, stats)
            if pdf_path is None:
                continue
            if not args.no_upload:
                drive_client.upload_pdf(pdf_path, drive_service, config.drive)
                stats.uploaded += 1
        except exceptions.RenderFailedError as e:
            log_error(e)
            stats.render_failures += 1
        except exceptions.UploadFailedError as e:
            log_error(e)
            stats.upload_failures += 1
    
    print_summary(stats)
    return compute_exit_code(stats)

def parse_argv(argv) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mirror-pdf-drive",
        description="Convierte MD a PDF y sube a Google Drive.",
    )
    parser.add_argument("--config", type=Path, default=Path("mirror-pdf-drive.config.yaml"))
    parser.add_argument("--source-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--folder-id", default=None)
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("paths", nargs="*", type=Path, default=[])
    return parser.parse_args(argv)
```

### Puntos de extensión

- **Agregar un nuevo flag:** añadir al `argparse` en
  `parse_argv`. El handler en `run` lo consume.
- **Cambiar el formato del resumen:** modificar `print_summary`.
- **Cambiar exit codes:** cambiar las constantes al inicio
  y actualizar `operacion/codigos-de-error.md`.

### No tocar

- El orden de operaciones: config → auth → render → upload.
  Cambiarlo rompe la idempotencia y el manejo de errores.
- El `try/except` por tipo de error. Cada subclase de
  `AppError` tiene un comportamiento específico.

---

## `config.py` — Carga y validación

### Función pública

```python
from pydantic import BaseModel, Field, field_validator

class SourceConfig(BaseModel):
    root: Path
    include: list[str] = Field(default_factory=lambda: ["**/*.md"])
    exclude: list[str] = Field(default_factory=list)
    max_depth: int = 10
    
    @field_validator("root")
    def root_must_exist(cls, v):
        if not v.exists():
            raise ValueError(f"source.root '{v}' does not exist")
        return v

class OutputConfig(BaseModel):
    root: Path
    clean: bool = False

class RenderConfig(BaseModel):
    html_template: Path | None = None
    css_file: Path | None = None
    page_size: str = "A4"
    margins: dict = Field(default_factory=lambda: {
        "top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0
    })
    metadata: dict = Field(default_factory=lambda: {
        "title": "Documents-es",
        "author": "Sebastián Illa",
    })

class DriveConfig(BaseModel):
    folder_id: str | None = None
    folder_name: str = "Documents-es PDFs"
    conflict_strategy: str = "skip"
    
    @field_validator("conflict_strategy")
    def valid_strategy(cls, v):
        if v not in ("skip", "replace", "version"):
            raise ValueError(f"invalid conflict_strategy: {v}")
        return v

class AuthConfig(BaseModel):
    dir: Path | None = None
    client_secret_file: str = "client_secret.json"
    token_file: str = "token.json"

class MirrorConfig(BaseModel):
    version: int = 1
    source: SourceConfig
    output: OutputConfig
    render: RenderConfig
    drive: DriveConfig
    auth: AuthConfig

def load_config(path: Path) -> MirrorConfig:
    """
    Carga el YAML desde path, valida, y devuelve MirrorConfig.
    
    Lanza:
      - FileNotFoundError si el archivo no existe
      - InvalidConfigError si la validación falla
    """
    if not path.exists():
        raise exceptions.ConfigNotFoundError(
            f"Config file not found: {path}",
            context={"path": str(path)},
        )
    
    with open(path) as f:
        raw = yaml.safe_load(f)
    
    try:
        return MirrorConfig(**raw)
    except pydantic.ValidationError as e:
        raise exceptions.InvalidConfigError(
            f"Config validation failed: {path}",
            context={"path": str(path), "errors": e.errors()},
        ) from e
```

### Puntos de extensión

- **Agregar un campo nuevo al config:** agregar el campo al
  `BaseModel` correspondiente con default razonable y
  `field_validator` si necesita validación custom.
- **Cambiar los defaults:** cambiar los defaults en el
  `Field(default_factory=...)`.
- **Cambiar los mensajes de error:** mejorar el mensaje de
  cada `field_validator`.

### No tocar

- **`version: int = 1`.** El versionado del schema es un
  contrato. Bumpear a 2 requiere una decisión de
  compatibilidad hacia atrás, no un cambio trivial.
- **El nombre de los campos.** Son YAML público. Cambiar
  `folder_id` a `folderId` rompe configs existentes.

---

## `renderer.py` — MD a PDF

### Función pública

```python
import pypandoc
from pathlib import Path
from . import exceptions

def render_markdown_to_pdf(
    md_path: Path,
    output_path: Path,
    config: RenderConfig,
) -> Path:
    """
    Convierte un .md a PDF usando pandoc + weasyprint.
    
    Args:
        md_path: Path al archivo .md fuente.
        output_path: Path donde escribir el PDF. Se crea el
            directorio padre si no existe.
        config: Config de renderizado.
    
    Returns:
        El path al PDF generado (igual a output_path).
    
    Raises:
        RenderFailedError si pandoc falla.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    extra_args = build_pandoc_args(config)
    
    try:
        pypandoc.convert_file(
            str(md_path),
            "pdf",
            outputfile=str(output_path),
            extra_args=extra_args,
        )
    except RuntimeError as e:
        raise exceptions.RenderFailedError(
            f"pandoc failed to render {md_path}",
            context={
                "md_path": str(md_path),
                "output_path": str(output_path),
                "pandoc_error": str(e),
            },
        ) from e
    
    return output_path

def build_pandoc_args(config: RenderConfig) -> list[str]:
    """Construye los argumentos extra para pandoc."""
    args = [
        f"--pdf-engine=weasyprint",
        f"-V", f"papersize={config.page_size}",
    ]
    if config.html_template:
        args.extend(["--template", str(config.html_template)])
    if config.css_file:
        # Pandoc con weasyprint usa CSS vía variable
        args.extend(["-c", str(config.css_file)])
    for key, value in config.metadata.items():
        if value:
            args.extend(["-V", f"{key}={value}"])
    return args
```

### Puntos de extensión

- **Cambiar el motor de renderizado:** modificar
  `build_pandoc_args` o reemplazar `pypandoc.convert_file`
  por otra llamada. El resto de la herramienta no se entera.
- **Agregar metadata al PDF:** agregar al dict `metadata` en
  `RenderConfig`. Aparece automáticamente.
- **Cambiar la plantilla HTML/CSS:** pasar `--template` o
  `-c` en los extra args.

### No tocar

- **La firma de `render_markdown_to_pdf`.** Es el contrato
  con `mirror.py`. Cambiarla requiere actualizar el
  orquestador.
- **El orden de las operaciones.** Primero crear el
  directorio padre, después llamar a pandoc. Invertirlo
  falla si el directorio no existe.

---

## `drive_client.py` — Subida a Drive

### Función pública

```python
from googleapiclient.http import MediaFileUpload
from pathlib import Path
from . import exceptions

def upload_pdf(
    pdf_path: Path,
    drive_service: Resource,
    folder_id: str,
    conflict_strategy: str,
) -> str:
    """
    Sube un PDF a Google Drive.
    
    Args:
        pdf_path: Path al PDF local.
        drive_service: Cliente de Drive API ya autenticado.
        folder_id: ID de la carpeta destino en Drive.
        conflict_strategy: "skip" | "replace" | "version".
    
    Returns:
        El ID de Drive del archivo subido.
    
    Raises:
        UploadFailedError si la API falla.
    """
    file_name = pdf_path.name
    
    if conflict_strategy == "skip":
        existing = find_file_in_folder(drive_service, file_name, folder_id)
        if existing:
            log_info(f"skip (exists): {file_name}")
            return existing["id"]
    
    if conflict_strategy == "replace":
        existing = find_file_in_folder(drive_service, file_name, folder_id)
        if existing:
            return update_file(drive_service, existing["id"], pdf_path)
    
    if conflict_strategy == "version":
        file_name = next_versioned_name(drive_service, file_name, folder_id)
    
    return create_file(drive_service, file_name, folder_id, pdf_path)

def find_file_in_folder(service, name, folder_id):
    """Busca un archivo por nombre en una carpeta."""
    query = f"name='{name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [{}])[0] or None

def create_file(service, name, folder_id, pdf_path):
    """Sube un archivo nuevo a Drive."""
    file_metadata = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(str(pdf_path), mimetype="application/pdf")
    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
        ).execute()
        return file.get("id")
    except HttpError as e:
        raise exceptions.UploadFailedError(
            f"Failed to upload {pdf_path.name}",
            context={"pdf_path": str(pdf_path), "api_error": str(e)},
        ) from e

def update_file(service, file_id, pdf_path):
    """Reemplaza el contenido de un archivo existente."""
    media = MediaFileUpload(str(pdf_path), mimetype="application/pdf")
    try:
        file = service.files().update(
            fileId=file_id,
            media_body=media,
            fields="id",
        ).execute()
        return file.get("id")
    except HttpError as e:
        raise exceptions.UploadFailedError(
            f"Failed to update {pdf_path.name}",
            context={"pdf_path": str(pdf_path), "file_id": file_id, "api_error": str(e)},
        ) from e
```

### Puntos de extensión

- **Cambiar la estrategia de conflictos:** agregar un valor
  nuevo a `conflict_strategy` y manejarlo en `upload_pdf`.
- **Cambiar el formato del nombre de archivo:** modificar
  `next_versioned_name` o el flujo principal.
- **Agregar reintentos con backoff:** envolver las llamadas a
  la API en un loop con `time.sleep`.

### No tocar

- **La firma de `upload_pdf`.** Es el contrato con
  `mirror.py`.
- **El parámetro `drive_service`.** Se recibe ya
  autenticado. `drive_client.py` no sabe ni le importa cómo
  se autenticó.

---

## `auth.py` — OAuth

### Función pública

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from pathlib import Path
from . import exceptions

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_service(auth_config: AuthConfig):
    """
    Devuelve un cliente de Drive autenticado.
    
    Si el token no existe o venció, lanza AuthRequiredError
    con instrucciones para correr --init.
    """
    creds = load_or_refresh_credentials(auth_config)
    if not creds:
        raise exceptions.AuthRequiredError(
            "OAuth token not found or invalid. Run 'mirror-pdf-drive --init' to authenticate.",
            context={"auth_dir": str(resolve_auth_dir(auth_config))},
        )
    return build("drive", "v3", credentials=creds)

def run_oauth_flow(auth_config: AuthConfig) -> None:
    """
    Hace el flow completo de OAuth la primera vez.
    
    Abre el browser, el usuario autoriza, el token se guarda
    en disco.
    """
    client_secret = resolve_client_secret_path(auth_config)
    if not client_secret.exists():
        raise FileNotFoundError(
            f"client_secret.json not found at {client_secret}. "
            f"Download it from GCP Console: "
            f"https://console.cloud.google.com/apis/credentials"
        )
    
    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secret), SCOPES
    )
    creds = flow.run_local_server(port=0)
    
    token_path = resolve_token_path(auth_config)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())

def load_or_refresh_credentials(auth_config):
    """Carga credenciales del disco, refresca si vencieron."""
    token_path = resolve_token_path(auth_config)
    if not token_path.exists():
        return None
    
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    return creds if creds and creds.valid else None

def resolve_auth_dir(auth_config: AuthConfig) -> Path:
    """Resuelve el directorio de auth, con override por env var."""
    env_dir = os.environ.get("MIRROR_PDF_DRIVE_AUTH_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    if auth_config.dir:
        return Path(os.path.expandvars(auth_config.dir)).expanduser()
    return Path.home() / ".config" / "mirror-pdf-drive"

def resolve_client_secret_path(auth_config: AuthConfig) -> Path:
    return resolve_auth_dir(auth_config) / auth_config.client_secret_file

def resolve_token_path(auth_config: AuthConfig) -> Path:
    return resolve_auth_dir(auth_config) / auth_config.token_file
```

### Puntos de extensión

- **Cambiar los scopes:** modificar la constante `SCOPES`.
  **Cuidado:** agregar `drive` completo es riesgoso.
- **Cambiar el puerto del flow local:** modificar
  `flow.run_local_server(port=0)`. `0` significa "elige uno
  libre".
- **Soportar headless servers:** cambiar `run_local_server`
  por `flow.run_console()` (que imprime una URL para
  visitar manualmente).

### No tocar

- **El scope `drive.file`.** Es la decisión de seguridad
  principal. Cambiarlo a `drive` requiere una justificación
  explícita.
- **El path default `~/.config/mirror-pdf-drive/`.** Es el
  estándar XDG. Si lo cambiás, rompés instalaciones
  existentes.

---

## `exceptions.py` — Códigos de error

### Contenido

```python
class AppError(Exception):
    """Base para todos los errores de la herramienta."""
    code: str = "APP_ERROR"
    
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}

class ConfigNotFoundError(AppError):
    code = "CONFIG_NOT_FOUND"

class InvalidConfigError(AppError):
    code = "INVALID_CONFIG"

class AuthRequiredError(AppError):
    code = "AUTH_REQUIRED"

class RenderFailedError(AppError):
    code = "RENDER_FAILED"

class UploadFailedError(AppError):
    code = "UPLOAD_FAILED"
```

### Puntos de extensión

- **Agregar un código nuevo:** subclasear `AppError` con
  `code` único. Documentar en
  `operacion/codigos-de-error.md`.

### No tocar

- **Los códigos existentes.** Son contrato con la skill de
  Pi y con el usuario.
- **El formato de `context`.** Es un dict libre pero la
  convención es `{"<key>": <value>, ...}` con strings
  serializables a JSON.
