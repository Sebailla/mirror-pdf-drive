# Operación — Corridas Normales

> **Cómo usar la herramienta en el día a día, después de la
> primera corrida exitosa. Asume que ya seguiste
> [`primera-corrida.md`](./primera-corrida.md).**

## El caso del 90%: corrida idempotente

Si cambiaste un par de archivos en `Documents-es/`:

```bash
mirror-pdf-drive
```

El script:
1. Detecta qué `.md` cambiaron (por `mtime`).
2. Re-renderiza solo esos.
3. Sube solo los PDFs que cambiaron.
4. Skipea el resto.
5. Imprime un resumen.

**Tiempo típico:** segundos para doc pequeña, hasta 1-2
minutos para doc mediana (cientos de archivos).

## Regenerar todo

Si querés regenerar todo (por ejemplo, después de cambiar
el CSS o la plantilla):

```bash
mirror-pdf-drive --force
```

Esto re-renderiza todos los `.md` y sube todos los PDFs (con
la estrategia de conflicto configurada).

**Cuidado:** si tu `drive.conflictStrategy` es `replace` y
corrés `--force`, sobreescribís todos los PDFs en Drive. Si
querés conservar historial, usá `version` o `skip`.

## Solo generar PDFs, no subir

Útil para revisar localmente antes de gastar quota de Drive:

```bash
mirror-pdf-drive --no-upload
```

Los PDFs quedan en `dist/mirror-pdf-drive/`. Después los
podés:

- Abrir directamente con `open dist/mirror-pdf-drive/...pdf`
  (macOS) o `xdg-open` (Linux).
- Compartir manualmente.
- Subir a mano si querés.

## Ver qué haría sin ejecutar

```bash
mirror-pdf-drive --dry-run
```

Imprime cada acción que **haría** (renderizar, subir, skip)
sin ejecutarla. Útil para:
- Verificar que el config está apuntando a los archivos
  correctos.
- Estimar cuánto va a tardar una corrida.
- Verificar que la estrategia de conflictos es la correcta.

## Diagnosticar un problema

```bash
mirror-pdf-drive --verbose
```

Log nivel DEBUG: muestra cada paso, cada argumento, cada
llamada a la API. Para guardar el log:

```bash
mirror-pdf-drive --verbose 2>&1 | tee mirror-pdf-drive-$(date +%Y%m%d).log
```

## Procesar archivos específicos

Si solo querés regenerar un archivo o un subdirectorio:

```bash
# Un archivo
mirror-pdf-drive Documents-es/AGENTS.md

# Varios archivos
mirror-pdf-drive Documents-es/AGENTS.md Documents-es/openspec/AGENTS.md

# Un subdirectorio (con un glob)
mirror-pdf-drive "Documents-es/posts/**/*.md"
```

**Importante:** los paths son relativos a `source.root` del
config, no al cwd.

## Cambiar de cuenta de Google

Si tenés dos cuentas (personal y trabajo):

```bash
# Opción 1: variable de entorno para esta corrida
MIRROR_PDF_DRIVE_AUTH_DIR="/path/a/auth-de-trabajo" \
  mirror-pdf-drive

# Opción 2: config con auth.dir distinto
# (requiere editar el config)
```

Para que la opción 1 funcione, tenés que haber corrido
`--init` con esa variable de entorno al menos una vez, para
generar el `token.json` correspondiente.

## Cuándo correr la herramienta

| Cuándo | Por qué |
|---|---|
| Después de un commit grande a `Documents-es/` | Mantener Drive sincronizado. |
| Antes de un release | Tener PDFs frescos para distribución. |
| Después de cambiar el CSS o la plantilla | Que el nuevo estilo se aplique a todos. |
| Después de cambiar el config | Verificar que el config nuevo funciona. |
| Antes de un demo o presentación a un stakeholder | Asegurarte de que los PDFs están actualizados. |

**Cuándo NO correrla:**

- En cada commit (es overhead). Mejor después de un PR mergeado.
- En un cron diario sin supervisión (puede subir archivos no
  deseados si el config cambia).

## Frecuencia recomendada

- **Proyecto activo:** semanal o después de cada release.
- **Proyecto en mantenimiento:** mensual.
- **Proyecto archivado:** bajo demanda, no programado.

## Logs

Los logs van a stdout por default. Para tener logs
persistentes:

```bash
# Con timestamp en el nombre
mirror-pdf-drive 2>&1 | tee logs/mirror-$(date +%Y%m%d-%H%M).log

# Con rotación (si tenés logrotate configurado)
mirror-pdf-drive 2>&1 | tee -a logs/mirror-pdf-drive.log
```

**Convención recomendada:** crear `logs/` en la raíz del
proyecto y agregarlo al `.gitignore` (los logs no se
versionan).

## Salida esperada (ejemplo)

```
Iniciando mirror-pdf-drive...
Config: mirror-pdf-drive.config.yaml
Source: Documents-es/
Output: dist/mirror-pdf-drive/
Drive: folder abc123 (strategy: skip)

Renderizando: Documents-es/AGENTS.md
  -> dist/mirror-pdf-drive/AGENTS.pdf
  -> Subiendo a Drive...
Omitiendo (sin cambios): Documents-es/openspec/AGENTS.md
Renderizando: Documents-es/openspec/changes/auth-foundation/proposal.md
  -> dist/mirror-pdf-drive/openspec/changes/auth-foundation/proposal.pdf
  -> Subiendo a Drive...

Listo. Renderizados: 2. Subidos: 2. Omitidos: 1. Fallos: 0.
Tiempo total: 4.3s.
```

## Salida con error (ejemplo)

```
Iniciando mirror-pdf-drive...
Config: mirror-pdf-drive.config.yaml

ERROR: No se pudo renderizar Documents-es/posts/2024-01-15.md
  Contexto: pandoc failed with exit code 1
  Sugerencia: abrí el MD localmente y verificá que pandoc pueda convertirlo
  Comando manual: pandoc Documents-es/posts/2024-01-15.md --pdf-engine=weasyprint -o /tmp/test.pdf

ERROR: No se pudo subir Documents-es/AGENTS.pdf
  Contexto: googleapiclient.errors.HttpError: 403, quotaExceeded
  Sugerencia: tu cuenta de Drive no tiene espacio. Liberá espacio o cambiá de cuenta.

Listo. Renderizados: 1. Subidos: 0. Omitidos: 0. Fallos: 2.
Tiempo total: 3.1s.
Exit code: 4 (upload failed)
```

(Exit 4, no 3, porque el peor de los errores fue el upload.)
