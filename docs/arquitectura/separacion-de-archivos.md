# Arquitectura — Separación de Archivos

> **Lee esto antes de reorganizar el código del script. La
> separación actual es deliberada y testeable; mover archivos
> "por prolijidad" suele romper los tests unitarios.**

## Ubicación global

```
~/.local/share/mirror-pdf-drive/
├── pyproject.toml          # Dependencias y entrypoint
├── README.md               # Doc de uso rápido para el dev que la mantiene
├── mirror.py               # Entry point CLI
├── config.py               # Carga y validación del config
├── renderer.py             # Conversión MD → PDF
├── drive_client.py         # Subida a Google Drive
├── auth.py                 # OAuth flow y refresh de token
├── exceptions.py           # Códigos de error estables
├── .venv/                  # Virtualenv (no versionar)
└── tests/                  # Tests unitarios (no versionar)
    ├── test_mirror.py
    ├── test_config.py
    ├── test_renderer.py
    ├── test_drive_client.py
    └── test_auth.py
```

**Por qué en `~/.local/share/`, no en `~/.pi/agent/skills/`:**

- `~/.local/share/` es el estándar XDG para datos de aplicación
  por usuario. Es la convención para herramientas CLI.
- `~/.pi/agent/skills/` es para skills de Pi, que son Markdown
  con frontmatter que Pi lee e interpreta. El código Python
  **no es** una skill de Pi; la skill de Pi es un wrapper que
  invoca al binario.
- Mantener la separación hace que la herramienta sea usable
  desde OpenCode, cron, o un script bash, sin tener que
  reescribir nada.

## Responsabilidades por archivo

### `mirror.py` — El orquestador

- Parsea argumentos CLI con `argparse`.
- Carga el config.
- Obtiene el cliente de Drive autenticado.
- Descubre los archivos Markdown.
- Para cada archivo, llama a `renderer` y después a `drive_client`.
- Imprime el resumen final.
- Devuelve el exit code apropiado.

**No hace:** renderizar, autenticar, validar schema del config
más allá de la carga, manejar reintentos.

**Cuándo modificarlo:**
- Agregás un nuevo flag CLI.
- Cambiás el formato del resumen.
- Cambiás la estrategia de exit codes.

**Cuándo NO modificarlo:**
- Cambia el formato de salida del PDF → va en `renderer.py`.
- Cambia el comportamiento de OAuth → va en `auth.py`.
- Cambia la forma de descubrir archivos → es un helper interno,
  podés refactorizarlo, pero la firma pública debe quedar igual.

### `config.py` — Configuración validada

- Carga el YAML desde el path provisto (o default).
- Lo valida con Pydantic.
- Expone el dataclass `MirrorConfig` (o un modelo de Pydantic)
  listo para consumir.

**No hace:** renderizar, autenticar, subir.

**Cuándo modificarlo:**
- Agregás un campo nuevo al config (con default y validación).
- Cambiás la versión del schema.
- Cambiás los mensajes de error de validación.

**Cuándo NO modificarlo:**
- Cambia el comportamiento de algún consumidor del config →
  cada módulo lee el config que necesita, no importa el
  dataclass entero.

### `renderer.py` — MD a PDF

- Toma un path a un `.md` y un path destino.
- Llama a `pandoc` con `--pdf-engine=weasyprint` o el método
  que se decida (ver [`../script/renderizado.md`](../script/renderizado.md)).
- Devuelve el path al PDF generado.

**No hace:** autenticarse, subir, decidir qué archivos procesar.

**Cuándo modificarlo:**
- Cambia el motor de renderizado (ej. de pandoc a mkdocs).
- Cambia la plantilla HTML/CSS.
- Cambia la metadata del PDF.

**Cuándo NO modificarlo:**
- Cambia el formato del input → si en el futuro se quiere
  aceptar `.docx` o `.rst`, agregá una función nueva
  (`render_docx_to_pdf`), no modifiques la existente.

### `drive_client.py` — Subida a Drive

- Toma un path local y un cliente de Drive ya autenticado.
- Sube el archivo a la carpeta destino.
- Maneja conflictos según la estrategia del config
  (`skip`, `replace`, `version`).
- Devuelve el ID de Drive del archivo subido.

**No hace:** autenticarse (recibe el cliente ya listo),
renderizar, descubrir archivos.

**Cuándo modificarlo:**
- Cambia la estrategia de manejo de conflictos.
- Cambia el formato del nombre de archivo en Drive.
- Cambia los reintentos de la API.

**Cuándo NO modificarlo:**
- Cambia la autenticación → va en `auth.py`.
- Cambia el formato del PDF → va en `renderer.py`.

### `auth.py` — OAuth flow y token

- Detecta si existe `token.json` válido.
- Si no existe o venció, lanza `AuthRequiredError` con
  instrucciones para correr `--init`.
- Si existe, lo refresca silenciosamente con `google-auth`.
- Expone `get_drive_service(config) -> Resource` listo para
  usar.

**No hace:** subir, renderizar, validar config más allá de la
sección `auth`.

**Cuándo modificarlo:**
- Cambian los scopes de OAuth.
- Cambia la ubicación del `client_secret.json` o `token.json`.
- Cambia el flujo de refresh del token.

**Cuándo NO modificarlo:**
- Cambia la lógica de upload → `drive_client.py`.
- Cambia el formato del PDF → `renderer.py`.

### `exceptions.py` — Contratos de error

- Define la jerarquía de `AppError`.
- Cada subclase tiene un `code` estable (string).
- Cada subclase tiene `context` opcional (dict con datos
  relevantes para el diagnóstico).

**No hace:** nada más. Es un módulo de definiciones.

**Cuándo modificarlo:**
- Agregás un código de error nuevo (con su subclase).
- Cambia el formato del `context`.

**Cuándo NO modificarlo:**
- Cambia el manejo de un error específico → eso es en el módulo
  que lanza el error, no en `exceptions.py`.

## Dependencias entre archivos

```
       ┌──────────┐
       │ mirror.py│
       └────┬─────┘
            │
   ┌────────┼────────┬────────┐
   ▼        ▼        ▼        ▼
┌──────┐┌────────┐┌──────┐┌──────┐
│config││renderer││drive ││ auth │
│ .py  ││  .py   ││.py   ││ .py  │
└──┬───┘└────────┘└──┬───┘└──┬───┘
   │                  │       │
   └─────────┬────────┘       │
             ▼                │
       ┌──────────┐           │
       │exception │◄──────────┘
       │  s.py    │
       └──────────┘
```

- `mirror.py` importa a todos.
- `config.py` importa `exceptions.py` (para `InvalidConfigError`).
- `renderer.py` importa `exceptions.py` (para `RenderFailedError`).
- `drive_client.py` importa `exceptions.py` (para
  `UploadFailedError`) y NO importa `auth.py` (recibe el
  cliente ya autenticado, no lo crea).
- `auth.py` importa `exceptions.py` (para `AuthRequiredError`)
  y NO importa `drive_client.py` (no sabe qué se va a hacer
  con el cliente).
- `exceptions.py` no importa nada del proyecto.

**Por qué `drive_client.py` no importa `auth.py`:**

Si `drive_client.py` importara `auth.py`, no podrías testear
`drive_client.py` con un cliente de Drive mockeado. Mantener la
dependencia unidireccional (auth → drive_client) permite
sustituir la autenticación en tests sin tocar la lógica de
subida.

## Tests por archivo

| Archivo | Testeable con | No necesita |
|---|---|---|
| `mirror.py` | mocks de `config`, `renderer`, `drive_client`, `auth` | filesystem real, Drive real, pandoc real |
| `config.py` | archivos YAML temporales | nada externo |
| `renderer.py` | archivos MD de fixture | Drive, auth, internet |
| `drive_client.py` | mock de `Resource` (cliente de Drive) | pandoc, filesystem real, OAuth |
| `auth.py` | mocks del flujo OAuth, archivos de token temporales | Drive, pandoc, filesystem real |
| `exceptions.py` | nada (es solo definiciones) | nada |

## No crear estos archivos

- **`utils.py`.** Es el anti-patrón clásico. Si una función
  helper es útil para dos módulos, ponela en el módulo que
  mejor la describa y que el otro la importe. Si no la podés
  ubicar, es que la función no tiene un dueño claro y
  probablemente hay que repensar la separación.
- **`helpers/`, `common/`, `shared/`.** Mismo argumento.
- **`__init__.py` con lógica.** El paquete
  `mirror_pdf_drive` solo expone los entrypoints; el
  `__init__.py` solo importa los módulos, no tiene
  side effects.
- **`models.py` separado de `config.py`.** Los modelos de
  datos son la config. Si en el futuro hay modelos de
  dominio (no config), entonces sí.
