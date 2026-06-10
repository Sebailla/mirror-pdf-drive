# Operación — Troubleshooting

> **Guía de diagnóstico paso a paso para los problemas más
> comunes. Si tu problema no está acá, corré con `--verbose`
> y revisá [`codigos-de-error.md`](./codigos-de-error.md).**

## Exit 1 — Error de Config

### Síntoma

```
ERROR [CONFIG_NOT_FOUND] Config file not found: mirror-pdf-drive.config.yaml
```

o

```
ERROR [INVALID_CONFIG] Config validation failed: mirror-pdf-drive.config.yaml
  - source.root: Path does not exist: 'Document-es' (got: Document-es)
```

### Causas probables

| Causa | Cómo verificar | Solución |
|---|---|---|
| No existe el config. | `ls -la mirror-pdf-drive.config.yaml` | Crear el config (ver `configuracion/ejemplos.md`). |
| Estás en el directorio equivocado. | `pwd` | `cd` a la raíz del proyecto. |
| El `source.root` no existe. | `ls -la Document-es` (o el path que pusiste) | Corregir el path en el config. |
| Typo en el nombre del campo. | Abrir el config | Ver `configuracion/schema.md` para los nombres correctos. |
| El YAML está mal indentado. | `python -c "import yaml; yaml.safe_load(open('mirror-pdf-drive.config.yaml'))"` | Corregir la indentación. |
| La versión del schema no es 1. | Abrir el config | Cambiar `version: 1` o actualizar la herramienta. |

### Solución rápida

```bash
# Validar el YAML
python -c "import yaml; yaml.safe_load(open('mirror-pdf-drive.config.yaml'))"

# Ver el config efectivo (con defaults)
mirror-pdf-drive --dry-run --verbose
```

## Exit 2 — Auth Requerida

### Síntoma

```
ERROR [AUTH_REQUIRED] OAuth token not found or invalid
  context:
    auth_dir: "/Users/seba/.config/mirror-pdf-drive"
```

### Causas probables

| Causa | Cómo verificar | Solución |
|---|---|---|
| Nunca corriste `--init`. | `ls -la ~/.config/mirror-pdf-drive/` | Correr `mirror-pdf-drive --init`. |
| El `token.json` se borró. | `ls -la ~/.config/mirror-pdf-drive/token.json` | Correr `mirror-pdf-drive --init` de nuevo. |
| El `client_secret.json` no está. | `ls -la ~/.config/mirror-pdf-drive/client_secret.json` | Bajar de GCP Console (ver `primera-corrida.md`). |
| El token venció y no se puede refrescar. | `cat ~/.config/mirror-pdf-drive/token.json` | Si tiene `refresh_token`, debería refrescarse solo. Si no, correr `--init`. |
| El `auth.dir` del config apunta a otro lado. | `cat mirror-pdf-drive.config.yaml \| grep auth` | Verificar que `auth.dir` sea el correcto. |
| Variable de env apunta a otro lado. | `echo $MIRROR_PDF_DRIVE_AUTH_DIR` | `unset MIRROR_PDF_DRIVE_AUTH_DIR` o apuntarla al lugar correcto. |

### Solución rápida

```bash
# Resetear todo y volver a autorizar
rm -f ~/.config/mirror-pdf-drive/token.json
mirror-pdf-drive --init
```

## Exit 3 — Render Falló

### Síntoma

```
ERROR [RENDER_FAILED] pandoc failed to render Documents-es/posts/post-1.md
  context:
    md_path: "Documents-es/posts/post-1.md"
    pandoc_error: "..."
```

### Causas probables

| Causa | Cómo verificar | Solución |
|---|---|---|
| `pandoc` no está instalado. | `which pandoc` | `brew install pandoc` (macOS) o `apt install pandoc` (Linux). |
| `pango` o `cairo` faltan (weasyprint). | `python -c "import weasyprint"` | `brew install pango cairo` (macOS) o `apt install libpango-1.0-0 libcairo2` (Linux). |
| El MD referencia una imagen que no existe. | Buscar el path en el error | Crear la imagen, corregir el path, o hacer el link relativo correctamente. |
| El MD tiene sintaxis Markdown inválida. | Abrir el MD en un editor con preview | Corregir el MD. |
| El MD es demasiado grande (>10MB). | `ls -la Document-es/archivo.md` | Considerar splitearlo en varios archivos. |
| Una plantilla custom está mal. | Renderizar con la plantilla manualmente | Corregir la plantilla o usar la default. |
| El CSS custom tiene errores. | Renderizar con el CSS manualmente | Corregir el CSS o usar el embebido. |

### Diagnóstico manual

```bash
# Renderizar el archivo problemático directo con pandoc
pandoc Documents-es/posts/post-1.md \
  --pdf-engine=weasyprint \
  -V papersize=A4 \
  -o /tmp/test.pdf

# Si esto funciona, el problema está en los flags extra del script
# Compará con los flags que pasa el script (ver --verbose)
mirror-pdf-drive --verbose Documents-es/posts/post-1.md 2>&1 | grep -A 20 "extra_args"
```

### Solución rápida

Si solo es un archivo problemático, skipealo y seguí:

```bash
# Procesar todo excepto el archivo problemático
mirror-pdf-drive --exclude Documents-es/posts/post-1.md
# (--exclude no implementado todavía, es un placeholder)
```

O corregir el MD y volver a correr.

## Exit 4 — Upload Falló

### Síntoma

```
ERROR [UPLOAD_FAILED] Failed to upload AGENTS.pdf
  context:
    pdf_path: "dist/mirror-pdf-drive/AGENTS.pdf"
    api_error: "<HttpError 403 ...>"
```

### Causas probables (por código HTTP)

| HTTP | Significado | Solución |
|---|---|---|
| 401 | Token inválido o vencido. | Correr `--init` de nuevo. |
| 403 | Permisos insuficientes, o quota excedida, o la app no está autorizada. | Verificar que el scope `drive.file` está en el consent. Liberar espacio en Drive. |
| 404 | La carpeta de Drive no existe. | Verificar que el `folderId` del config es correcto, o correr `--init` para crear la carpeta. |
| 429 | Rate limit de la API. | Esperar unos minutos y volver a correr. El script reintenta automáticamente 3 veces con backoff. |
| 500/502/503 | Error del servidor de Google. | Esperar y volver a correr. Es transitorio. |
| Timeout | Conexión lenta o caída. | Verificar internet. Si persiste, puede ser un firewall corporativo. |

### Diagnóstico manual

```bash
# Probar la API de Drive con curl (usando el token)
TOKEN=$(python -c "import json; print(json.load(open('/Users/seba/.config/mirror-pdf-drive/token.json'))['token'])")
curl -H "Authorization: Bearer $TOKEN" \
  https://www.googleapis.com/drive/v3/files?pageSize=1
```

Si esto falla, el problema es el token o la red, no el script.

### Solución rápida

```bash
# Reautorizar y reintentar
mirror-pdf-drive --init
mirror-pdf-drive
```

## Exit 5 — Error Inesperado

### Síntoma

```
ERROR [APP_ERROR] Unexpected error
  context: ...
  traceback: ...
```

### Qué hacer

1. **No es tu culpa** (probablemente). Es un bug de la
   herramienta.
2. Copiá el log completo con `--verbose`.
3. Abrí un issue con:
   - Comando que corriste.
   - Log completo.
   - OS y versiones (ver `codigos-de-error.md` para qué
     incluir).
4. Mientras tanto, podés:
   - Generar PDFs localmente con `--no-upload` y subirlos a
     mano a Drive.
   - Revertir a la versión anterior de la herramienta.

## Performance: tarda demasiado

### Síntoma

Una corrida que antes tardaba segundos ahora tarda minutos.

### Causas probables

| Causa | Cómo verificar | Solución |
|---|---|---|
| Hay muchos archivos nuevos. | `mirror-pdf-drive --dry-run` | Normal, esperar. |
| Un MD específico es enorme. | `find Documents-es -name "*.md" -size +1M` | Splitear el MD. |
| La conexión a Drive está lenta. | Probar otro servicio | Esperar, o reintentar más tarde. |
| El rate limit de Drive te pega. | Ver si hay muchos 429 en el log | Esperar una hora. |

## "Funciona pero el PDF se ve mal"

Esto NO es un error de la herramienta; es un problema de
estilo. Soluciones:

1. **Custom CSS:** crear tu propio CSS y apuntar
   `render.cssFile` a él. Ver `script/renderizado.md`.

2. **Custom plantilla:** crear una plantilla Pandoc y apuntar
   `render.htmlTemplate` a ella.

3. **Reportar el problema de estilo** como issue, no como
   bug. La herramienta no es un diseñador de PDFs; es un
   conversor MD → PDF.

## "Quiero agregar un nuevo proyecto"

1. En la raíz del nuevo proyecto, crear
   `mirror-pdf-drive.config.yaml`.
2. Apuntar `source.root` a donde está la doc del proyecto.
3. (Opcional) Apuntar `drive.folderId` a una carpeta de Drive
   específica para ese proyecto, o dejar que `--init` la
   cree.
4. Correr `mirror-pdf-drive --init` (la primera vez).
5. Correr `mirror-pdf-drive` (corrida normal).

## "Quiero cambiar de cuenta de Google"

Ver `corridas-normales.md` sección "Cambiar de cuenta de
Google". TL;DR: usar la variable de entorno
`MIRROR_PDF_DRIVE_AUTH_DIR` apuntando a un directorio de
auth distinto, y correr `--init` ahí.
