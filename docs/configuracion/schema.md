# Configuración — Schema

> **Schema completo del archivo `mirror-pdf-drive.config.yaml`.
> Cada campo, su tipo, su default, su validación, y por qué
> existe. Para ejemplos de configs reales, ver [`ejemplos.md`](./ejemplos.md).**

## Anatomía del archivo

```yaml
# Comentarios con # son permitidos y recomendados.
# El orden de las secciones es libre.
version: 1                     # Schema version, siempre entero positivo.
source: { ... }                # Qué procesar.
output: { ... }                # Dónde dejar los PDFs antes de subir.
render: { ... }                # Cómo renderizar MD a PDF.
drive:  { ... }                # Dónde y cómo subir a Google Drive.
auth:   { ... }                # Dónde está el OAuth client y el token.
logging: { ... }               # Nivel y formato de los logs.
```

## Versionado

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `version` | `int` | (obligatorio) | Entero positivo. El script rechaza versiones mayores a las que conoce. |

**Por qué versionado:** si en el futuro cambia el schema
(por ejemplo, se agrega un campo obligatorio), el script
puede rechazar configs viejos con un mensaje claro, en vez
de fallar de formas confusas.

**Cuándo bumpear:**
- Se agrega un campo obligatorio.
- Se cambia el tipo de un campo existente.
- Se renombra un campo.

**Cuándo NO bumpear:**
- Se agrega un campo opcional con default.
- Se cambia un mensaje de error.
- Se cambia la implementación interna sin tocar el schema.

## Sección `source`

Define **qué archivos Markdown** se procesan.

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `source.root` | `Path` | (obligatorio) | Debe existir. Relativo al config o absoluto. |
| `source.include` | `list[str]` | `["**/*.md"]` | Globs válidos. |
| `source.exclude` | `list[str]` | `[]` | Globs válidos. Se aplican después de `include`. |
| `source.maxDepth` | `int` | `10` | Entero positivo. |

### `source.root`

Path al directorio raíz desde donde se buscan los `.md`.

- **Relativo:** se interpreta相对于 al path del config.
- **Absoluto:** se usa tal cual.

```yaml
source:
  root: "Documents-es"          # relativo
  # o
  root: "/Users/seba/proyecto/Documents-es"   # absoluto
```

### `source.include`

Lista de patrones glob. Solo los archivos que matcheen al
menos un patrón se procesan.

- `**` matchea cualquier número de directorios.
- `*` matchea cualquier número de caracteres en un nivel.
- `?` matchea un carácter.

```yaml
source:
  include:
    - "**/*.md"            # todos los .md recursivos
    - "**/*.markdown"      # y los .markdown también
```

### `source.exclude`

Lista de patrones glob. Los archivos que matcheen **cualquiera**
de estos patrones se excluyen, aunque estén en `include`.

```yaml
source:
  exclude:
    - "**/node_modules/**"
    - "**/dist/**"
    - "**/.tmp/**"
    - "**/WIP.md"          # un archivo específico
```

**Por qué exclude se aplica después de include:** así podés
hacer "todos los .md excepto los de node_modules" sin tener
que negar el patrón.

### `source.maxDepth`

Límite de recursión. Útil para no procesár directorios
enormes por accidente.

```yaml
source:
  maxDepth: 5     # como máximo 5 niveles de subdirectorios
```

## Sección `output`

Define **dónde se escriben los PDFs** antes de subirlos a
Drive.

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `output.root` | `Path` | (obligatorio) | Path válido. Se crea si no existe. |
| `output.clean` | `bool` | `false` | Si `true`, borra el contenido de `output.root` antes de cada corrida. |

### `output.root`

Path al directorio donde se escriben los PDFs. La estructura
de subdirectorios se preserva: un MD en
`Documents-es/posts/post-1.md` produce un PDF en
`dist/mirror-pdf-drive/posts/post-1.pdf`.

**Convención recomendada:** `dist/mirror-pdf-drive/` y agregar
`dist/` al `.gitignore` del proyecto.

### `output.clean`

Si es `true`, el script borra todo el contenido de
`output.root` antes de empezar. Útil si querés asegurarte de
que no queden PDFs viejos de MDs que ya no existen.

**Cuidado:** con `--force` y `output.clean: true`, re-renderizás
todo y borrás PDFs viejos. Si el MD fuente se borró pero
todavía querés conservar el PDF, no uses `clean: true`.

## Sección `render`

Define **cómo se renderiza** MD a PDF.

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `render.htmlTemplate` | `Path \| null` | `null` | Debe existir si no es null. |
| `render.cssFile` | `Path \| null` | `null` | Debe existir si no es null. |
| `render.pageSize` | `str` | `"A4"` | Uno de: `A4`, `Letter`, `Legal`. |
| `render.margins` | `dict` | `{top: 2.0, bottom: 2.0, left: 2.0, right: 2.0}` | Cada valor es un float positivo en cm. |
| `render.metadata` | `dict` | `{title: "Documents-es", author: "Sebastián Illa"}` | Keys: `title`, `author`, `subject`, `keywords`. |

### `render.htmlTemplate`

Path a una plantilla Pandoc HTML. Si no se especifica, pandoc
usa su default. Ver
[`../script/renderizado.md`](../script/renderizado.md#plantillas-pandoc).

### `render.cssFile`

Path a un archivo CSS que se aplica durante la conversión a
PDF. Si no se especifica, se usa el CSS mínimo embebido en
el script.

### `render.pageSize`

Tamaño de página. Valores soportados:

- `A4` (210 × 297 mm) — default, estándar internacional.
- `Letter` (8.5 × 11 in) — estándar US.
- `Legal` (8.5 × 14 in) — legal US.

### `render.margins`

Márgenes de página en centímetros.

```yaml
render:
  margins:
    top: 2.5
    bottom: 2.5
    left: 3.0
    right: 2.0
```

### `render.metadata`

Metadata que aparece en las propiedades del PDF.

```yaml
render:
  metadata:
    title: "Atlas de Myxomycetes"      # título del PDF
    author: "Sebastián Illa"            # autor
    subject: "Documentación del proyecto"
    keywords: "atlas, myxomycetes, biología"
```

**Por qué `author` default a "Sebastián Illa":** el AGENTS.md
del proyecto define que toda la doc tiene como autor a
Sebastián Illa. El script respeta esa convención.

## Sección `drive`

Define **cómo se suben los PDFs a Google Drive**.

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `drive.folderId` | `str \| null` | `null` | Formato de ID de Drive (string alfanumérico con `-` y `_`). |
| `drive.folderName` | `str` | `"Documents-es PDFs"` | String no vacío. |
| `drive.conflictStrategy` | `str` | `"skip"` | Uno de: `skip`, `replace`, `version`. |

### `drive.folderId`

ID de la carpeta de Google Drive donde se suben los PDFs.

- **Si es `null`:** el script asume que `--init` ya corrió y
  la carpeta existe, o que la va a crear la primera corrida
  con `--init`.
- **Si está seteado:** se usa ese ID directamente. El script
  no verifica que la carpeta exista hasta el momento del
  upload (falla con 404 si no existe).

**Cómo obtener el ID de una carpeta de Drive:**
1. Abrí Drive en el browser.
2. Navegá a la carpeta.
3. La URL termina en `/folders/<ID_AQUÍ>`. Copialo.

### `drive.folderName`

Nombre de la carpeta que se crea si `folderId` es `null` y
corre `--init`.

### `drive.conflictStrategy`

Qué hacer si ya existe un PDF con el mismo nombre en la
carpeta destino.

| Valor | Comportamiento |
|---|---|
| `skip` | No subir. El PDF local se descarta (se borrá si `--force` no se usó). Loggea `skip (exists)`. |
| `replace` | Sobrescribir el archivo existente. El nuevo PDF reemplaza al viejo. |
| `version` | Subir con sufijo `-v2`, `-v3`, etc. Ej: `AGENTS.pdf` → `AGENTS-v2.pdf` → `AGENTS-v3.pdf`. |

**Cuándo usar cada uno:**
- `skip` (default): docs que se regeneran frecuentemente y
  querés conservar la URL pública de Drive estable.
- `replace`: docs donde la versión vieja no tiene valor
  histórico (ej. snapshots, exports de un día).
- `version`: docs donde querés historial completo en Drive.

## Sección `auth`

Define **dónde están las credenciales OAuth**.

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `auth.dir` | `Path \| null` | `null` | Si se especifica, debe existir o poder crearse. Acepta `${ENV_VAR}`. |
| `auth.clientSecretFile` | `str` | `"client_secret.json"` | Nombre del archivo. |
| `auth.tokenFile` | `str` | `"token.json"` | Nombre del archivo. |

### `auth.dir`

Path al directorio donde vive `client_secret.json` y
`token.json`.

- **Si es `null`:** se usa `~/.config/mirror-pdf-drive/`
  (estándar XDG).
- **Si está seteado:** se usa ese path, con expansión de
  variables de entorno.

```yaml
auth:
  dir: "${HOME}/.config/mirror-pdf-drive"   # explícito
  # o
  dir: "/opt/secrets/mirror-pdf-drive"      # absoluto, sin env vars
```

### `auth.clientSecretFile`

Nombre del archivo con el client secret de OAuth. **No** el
secret en sí: es el JSON que bajás de GCP Console.

### `auth.tokenFile`

Nombre del archivo donde se cachea el token de OAuth
después del flow inicial. El script lo crea, vos no.

## Sección `logging`

Define **cómo se loggean** los mensajes.

| Campo | Tipo | Default | Validación |
|---|---|---|---|
| `logging.level` | `str` | `"INFO"` | Uno de: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `logging.format` | `str` | `"text"` | Uno de: `text`, `json`. |

### `logging.level`

Nivel mínimo de log. Los mensajes por debajo del nivel
configurado se descartan.

- `DEBUG`: include `--verbose`.
- `INFO`: corrida normal, informa qué se procesó.
- `WARNING`: algo raro pasó pero se pudo continuar.
- `ERROR`: algo falló y el archivo no se procesó.

### `logging.format`

- `text`: formato humano, con timestamp y color (si el
  terminal lo soporta).
- `json`: formato estructurado para parsear con `jq` o
  similar. Útil para CI o logs centralizados.

## Validación completa

Cuando se carga el config, Pydantic valida:

1. **Tipos:** cada campo tiene el tipo esperado. Si pasás
   `pageSize: 4` (int en vez de str), falla.
2. **Defaults:** los campos opcionales que no estén en el
   YAML toman el default de Pydantic.
3. **Validadores custom:** `field_validator` en cada modelo.
4. **Paths:** los paths se verifican que existan (si aplica).

Si algo falla, el script imprime:

```
Error: Config validation failed: mirror-pdf-drive.config.yaml
  - source.root: Path does not exist: 'Document-es' (got: Document-es)
  - render.pageSize: invalid value 'A5', must be one of A4, Letter, Legal
  
Sugerencia: revisá el archivo de config. Para más info, ver
  Document-es/configuracion/schema.md
```

Y sale con exit code 1.
