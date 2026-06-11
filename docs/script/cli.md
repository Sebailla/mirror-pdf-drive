# Script — CLI

> **Diseño de la interfaz de línea de comandos. Para la
> implementación interna de cada flag, ver [`modulos.md`](./modulos.md).**

## Forma general del comando

```
mirror-pdf-drive [opciones] [paths...]
```

Sin argumentos: procesa todos los `.md` bajo `source.root` del
config, según las reglas de `include` y `exclude`.

Con paths: procesa solo esos paths (relativos a `source.root` o
absolutos). El resto del config se respeta.

## Argumentos

### Argumentos posicionales

| Nombre | Tipo | Default | Descripción |
|---|---|---|---|
| `paths` | `list[Path]` | `[]` | Paths específicos a procesar. Si está vacío, procesa todo `source.root`. |

### Opciones

| Flag | Tipo | Default | Descripción |
|---|---|---|---|
| `--config` | `Path` | `./mirror-pdf-drive.config.yaml` | Path al config YAML. |
| `--source-dir` | `Path` | el del config | Override del `source.root`. Útil para probar contra otro árbol sin editar el config. |
| `--output-dir` | `Path` | el del config | Override del `output.root`. |
| `--dry-run` | flag | `False` | Genera PDFs pero no sube. Imprime qué subiría. **No** genera PDFs reales tampoco si se combina con `--no-render` (ver más abajo). |
| `--force` | flag | `False` | Re-renderiza aunque el PDF destino sea más nuevo que el MD. |
| `--verbose` | flag | `False` | Log nivel DEBUG. |
| `--no-upload` | flag | `False` | Solo renderiza, no sube a Drive. Útil para previsualizar PDFs sin gastar quota. |
| `--folder-id` | `str` | el del config | Override del `drive.folderId`. |
| `--init` | flag | `False` | Bootstrap: valida config, hace OAuth flow, opcionalmente crea la carpeta de Drive. Después sale. |
| `--version` | flag | `False` | Imprime versión y sale. |
| `--help` | flag | `False` | Imprime ayuda y sale. |

## Exit codes

| Code | Nombre | Cuándo |
|---|---|---|
| 0 | `EXIT_OK` | Todo salió bien. Algunos archivos pueden haberse skipeado por idempotencia, pero no hubo errores. |
| 1 | `EXIT_CONFIG_ERROR` | El config no existe, no se puede parsear, o la validación falló. |
| 2 | `EXIT_AUTH_REQUIRED` | No hay token OAuth, o venció y no se pudo refrescar. Solución: correr `mirror-pdf-drive --init`. |
| 3 | `EXIT_RENDER_FAILED` | Uno o más archivos no se pudieron renderizar. Otros pueden haber funcionado. El resumen al final indica cuáles. |
| 4 | `EXIT_UPLOAD_FAILED` | Uno o más archivos no se pudieron subir. Otros pueden haberse subido. El resumen al final indica cuáles. |
| 5 | `EXIT_UNEXPECTED` | Un error no clasificado. La traza completa está en el log. Probablemente un bug. |

**Regla de "el peor gana":** si hubo un error de config (1) y
después un error de upload (4), el exit code final es 4. Si
hubo un error de auth (2), el script sale antes de intentar
renderizar, así que el exit es 2 aunque haya errores
potenciales de render. La prioridad es:

```
5 (inesperado) > 2 (auth) > 1 (config) > 4 (upload) > 3 (render) > 0 (ok)
```

(El "peor" se interpreta como el más cercano a la raíz del
problema. Un error inesperado puede ocultar otros, así que gana
a todos. Un error de config hace que el script no pueda
progresar, así que gana sobre errores de ejecución.)

## Comportamiento por modo

### Modo normal (sin flags especiales)

```
$ mirror-pdf-drive
```

1. Carga `./mirror-pdf-drive.config.yaml`.
2. Autentica con OAuth.
3. Descubre todos los `.md` bajo `source.root`.
4. Para cada uno:
   - Si el PDF destino existe y es más nuevo → skip.
   - Si no → renderiza y sube.
5. Imprime resumen.
6. Exit 0 si todo OK, otro si hubo errores.

### Modo `--init`

```
$ mirror-pdf-drive --init
```

1. Carga el config.
2. Verifica que `client_secret.json` existe. Si no, imprime
   instrucciones para bajarlo de GCP Console y sale con exit 1.
3. Hace OAuth flow (abre browser, usuario autoriza).
4. Guarda `token.json` en `auth.dir` (o `~/.config/mirror-pdf-drive/`).
5. Verifica que puede listar archivos de Drive con el scope
   `drive.file`.
6. Si `drive.folderId` es `null` en el config, busca si
   existe una carpeta con `drive.folderName` en la raíz del
   Drive del usuario. Si no, la crea e imprime el nuevo ID
   con instrucciones para actualizar el config.
7. Sale con exit 0.

### Modo `--dry-run`

```
$ mirror-pdf-drive --dry-run
```

1. Carga el config.
2. Autentica (necesario para verificar la carpeta de Drive).
3. Descubre los `.md`.
4. Para cada uno, imprime qué **haría**:
   ```
   [DRY-RUN] render: Documents-es/AGENTS.md -> dist/AGENTS.pdf
   [DRY-RUN] upload: AGENTS.pdf -> folder abc123 (strategy: skip)
   [DRY-RUN] skip (exists): dist/openspec/AGENTS.pdf
   ```
5. NO renderiza, NO sube.
6. Sale con exit 0 (los errores de dry-run son de config o
   auth, no de render/upload).

### Modo `--no-upload`

```
$ mirror-pdf-drive --no-upload
```

Igual al modo normal pero sin subir. Útil para generar PDFs
localmente y revisarlos antes de gastar quota de Drive.

### Modo `--force`

```
$ mirror-pdf-drive --force
```

Ignora la verificación de `mtime`. Re-renderiza todo y sube
todo (si no se combina con `--no-upload`).

**Cuidado:** si combinás `--force` con `drive.conflictStrategy:
replace`, sobreescribís todos los PDFs en Drive. Usar con
cuidado.

## Argumentos posicionales

### Sin paths

```
$ mirror-pdf-drive
```

Procesa todos los `.md` bajo `source.root` (recursivo,
respetando `include` y `exclude`).

### Con paths relativos

```
$ mirror-pdf-drive Documents-es/AGENTS.md
```

Procesa solo ese archivo. El path se interpreta como
**relativo a `source.root`**, no al cwd. Si el archivo no
está dentro de `source.root`, sale con error.

### Con paths absolutos

```
$ mirror-pdf-drive /Users/sebailla/Documents/Proyectos/2026/gastos-personales/Documents-es/AGENTS.md
```

Procesa solo ese archivo. El path absoluto se acepta, pero
el output se calcula **relativo a `source.root`**, lo que
puede dar resultados raros. Recomendación: usar paths
relativos.

## Variables de entorno

| Variable | Default | Efecto |
|---|---|---|
| `MIRROR_PDF_DRIVE_AUTH_DIR` | `~/.config/mirror-pdf-drive/` | Override del directorio de auth (donde vive `client_secret.json` y `token.json`). |
| `MIRROR_PDF_DRIVE_CONFIG` | (ninguno) | Si está seteada, override del path al config. Tiene prioridad sobre `--config` y sobre el default. |

**Por qué una variable de env y no un flag CLI:** las
variables de entorno son útiles para configuración que
querés **persistir entre corridas** sin editar el config.
Por ejemplo, si tenés dos cuentas de Google (personal y
trabajo) y querés que el `auth.dir` apunte a una u otra
según la sesión de shell.

## Ejemplos de uso

### Primera vez en un proyecto nuevo

```bash
# 1. Bajar client_secret.json de GCP Console a ~/.config/mirror-pdf-drive/

# 2. Crear el config del proyecto
cat > mirror-pdf-drive.config.yaml <<EOF
version: 1
source:
  root: "Documents-es"
EOF

# 3. Bootstrap
mirror-pdf-drive --init

# 4. Corrida normal
mirror-pdf-drive
```

### Regenerar todo después de un cambio grande

```bash
mirror-pdf-drive --force
```

### Previsualizar sin gastar quota

```bash
mirror-pdf-drive --dry-run
```

### Solo generar PDFs, no subir

```bash
mirror-pdf-drive --no-upload
ls dist/mirror-pdf-drive/
```

### Diagnosticar un error

```bash
mirror-pdf-drive --verbose
# O con más detalle:
mirror-pdf-drive --verbose 2>&1 | tee mirror-pdf-drive.log
```

## Mensajes al usuario

Los mensajes al usuario final van en **español**. Los logs
internos van en **inglés**.

| Cuándo | Español | Inglés (log) |
|---|---|---|
| Error de config | `No se encontró el archivo de configuración: {path}` | `config not found: {path}` |
| Auth requerida | `Necesitás autorizar la herramienta. Corré: mirror-pdf-drive --init` | `OAuth token missing, suggest --init` |
| Render falló | `No se pudo renderizar {archivo}. Revisa que pandoc esté instalado y el MD sea válido.` | `render failed: {md_path}` |
| Upload falló | `No se pudo subir {archivo} a Google Drive. Verificá tu conexión y quota.` | `upload failed: {pdf_path}, api_error: {e}` |
| Resumen | `Renderizados: {N}. Subidos: {M}. Omitidos: {K}. Fallos: {F}.` | `summary: rendered={N} uploaded={M} skipped={K} failed={F}` |
