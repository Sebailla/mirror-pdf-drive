# Configuración — Ejemplos

> **Configs reales para distintos casos de uso. Copiá el que
> más se parezca a tu situación, ajustá los paths, y listo.**

## Mínimo absoluto

Solo lo obligatorio. Todo lo demás toma defaults.

```yaml
# mirror-pdf-drive.config.yaml
version: 1
source:
  root: "Documents-es"
```

**Lo que hace este config:**
- Procesa todos los `.md` bajo `Documents-es/`, recursivo.
- Saca los PDFs a `dist/mirror-pdf-drive/`.
- Usa A4, márgenes de 2cm, autor "Sebastián Illa".
- Sube a una carpeta llamada "Documents-es PDFs" en la raíz
  de tu Drive (o usa el `folderId` si está en el config).
- Si el PDF ya existe en Drive, lo skipea.

## Típico para un proyecto bilingüe

```yaml
# mirror-pdf-drive.config.yaml
version: 1

source:
  root: "Documents-es"
  include:
    - "**/*.md"
  exclude:
    - "**/node_modules/**"
    - "**/dist/**"
    - "**/.tmp/**"
    - "**/_drafts/**"
  maxDepth: 10

output:
  root: "dist/mirror-pdf-drive"
  clean: false

render:
  pageSize: "A4"
  margins:
    top: 2.5
    bottom: 2.5
    left: 3.0
    right: 2.0
  metadata:
    title: "Documentación del Proyecto"
    author: "Sebastián Illa"
    subject: "Espejo en español"
    keywords: "proyecto, docs, español"

drive:
  folderName: "Docs - PDFs"
  conflictStrategy: "skip"

auth:
  dir: null   # usa el default XDG

logging:
  level: "INFO"
  format: "text"
```

**Diferencias con el mínimo:**
- Excluye directorios de tooling y drafts.
- Configura márgenes un poco más amplios (3cm a la izquierda
  para encuadernación).
- Metadata más descriptiva.
- Cambia el nombre de la carpeta de Drive a algo más
  reconocible.

## Proyecto con CSS y plantilla custom

```yaml
version: 1

source:
  root: "Documents-es"

render:
  htmlTemplate: "tools/pdf-template.html"
  cssFile: "tools/pdf-styles.css"
  pageSize: "Letter"          # US Letter, no A4
  metadata:
    title: "Atlas Documentation"
    author: "Sebastián Illa"
    keywords: "atlas, biology, myxomycetes"
  margins:
    top: 2.0
    bottom: 2.0
    left: 2.5
    right: 2.5

output:
  root: "dist/pdfs"

drive:
  folderId: "1aBcDeFgHiJkLmNoPqRsTuVwXyZ"   # carpeta específica
  conflictStrategy: "version"   # conserva historial
```

**Lo que agrega:**
- Plantilla HTML custom en `tools/pdf-template.html`.
- CSS custom en `tools/pdf-styles.css`.
- Tamaño Letter (US).
- Folder ID hardcodeado (ya corriste `--init` antes y sabés
  el ID).
- Estrategia `version` para conservar historial en Drive.

## Múltiples documentos en un repo

Si tu repo tiene `docs/`, `docs-es/` y `docs-pt/`, y querés
que cada uno vaya a una carpeta de Drive distinta, **no uses
un solo config**. En vez de eso:

1. **Opción A: tres configs separados.** Corrés el script
   tres veces, una por cada config. Cada uno con su
   `source.root` y `drive.folderId`.

   ```bash
   mirror-pdf-drive --config configs/docs-es.yaml
   mirror-pdf-drive --config configs/docs-pt.yaml
   mirror-pdf-drive --config configs/docs.yaml
   ```

2. **Opción B: un solo config con un script que procesa
   varios.** Esto requiere agregar al script el concepto de
   "perfil" o "target". **No implementado todavía**; si lo
   necesitás, ver `operacion/multiples-documentos.md` (no
   existe aún, es un placeholder).

   ```yaml
   version: 1
   targets:
     - name: "docs-es"
       source: { root: "Documents-es" }
       drive:  { folderId: "abc123" }
     - name: "docs-en"
       source: { root: "Documents" }
       drive:  { folderId: "def456" }
   ```

## Repo sin `Documents-es/`

Si tu repo no tiene `Documents-es/`, simplemente apuntá
`source.root` a donde esté tu doc:

```yaml
version: 1
source:
  root: "docs"
```

El nombre `Documents-es` es solo la convención del proyecto
`gastos-personales`. El script no lo requiere.

## Repo con doc en varios idiomas y querés solo el español

```yaml
version: 1
source:
  root: "docs"
  include:
    - "es/**/*.md"   # solo el subdirectorio es/
  exclude:
    - "**/drafts/**"
    - "**/_archive/**"
```

## Uso con auth custom

Si querés tener un `auth.dir` distinto del default XDG (por
ejemplo, porque compartís la máquina con otro usuario y cada
uno tiene su OAuth):

```yaml
version: 1
source:
  root: "Documents-es"
auth:
  dir: "${HOME}/.config/seba-mirror-pdf-drive"
```

O por env var sin tocar el config:

```bash
export MIRROR_PDF_DRIVE_AUTH_DIR="/Users/seba/.config/seba-mirror-pdf-drive"
mirror-pdf-drive
```

## Debug: ver el config efectivo

Si querés ver qué config está usando el script (con los
defaults aplicados), corré:

```bash
mirror-pdf-drive --config mirror-pdf-drive.config.yaml --dry-run --verbose
```

El log en modo DEBUG incluye el config completo parseado.

## Validación del config

Para validar el config **sin** correr el script:

```bash
# Opción 1: usar el script en modo dry-run
mirror-pdf-drive --dry-run

# Opción 2: parsear con python
python -c "
import yaml
from mirror_pdf_drive.config import load_config
from pathlib import Path
config = load_config(Path('mirror-pdf-drive.config.yaml'))
print(config.model_dump_json(indent=2))
"
```

La opción 2 es útil para CI: podés tener un test que valide
que el config del proyecto es parseable.
