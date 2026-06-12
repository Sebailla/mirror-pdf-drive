---
title: Instalar mirror-pdf-drive en un nuevo repo
author: Sebastián Illa
version: 0.5.1
status: stable
---

# Instalar `mirror-pdf-drive` en un nuevo repo

Guía paso a paso para que cualquier dev pueda configurar
`mirror-pdf-drive` en un proyecto desde cero, sin importar
si es el dev original o alguien nuevo.

## Resumen del flujo

1. **Una sola vez por máquina**: instalar el CLI, las deps de sistema, y configurar OAuth de Google.
2. **Una sola vez por proyecto**: crear el `mirror-pdf-drive.config.yaml` y (opcional) ajustar `.gitignore`.
3. **Cada vez que quieras regenerar PDFs**: correr `mirror-pdf-drive`.

Las secciones están marcadas con **[una vez por máquina]** o
**[una vez por proyecto]** o **[cada corrida]** según corresponda.

---

## [Una vez por máquina] Instalar el CLI

### Opción A: desde PyPI / TestPyPI (recomendado)

```bash
pip install mirror-pdf-drive
# O, si está solo en TestPyPI:
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ mirror-pdf-drive
```

### Opción B: desde el repo fuente (para desarrollo)

```bash
git clone https://github.com/Sebailla/mirror-pdf-drive.git
cd mirror-pdf-drive
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Verificar

```bash
mirror-pdf-drive --version
# Esperado: mirror-pdf-drive 0.5.1
```

---

## [Una vez por máquina] Instalar las deps de sistema

El CLI usa `pandoc` para MD→HTML y `weasyprint` para HTML→PDF.
WeasyPrint necesita libs nativas (`pango`, `cairo`, `glib`,
`harfbuzz`, etc.).

### macOS (con Homebrew)

```bash
brew install pandoc pango cairo glib gobject-introspection \
             harfbuzz fribidi libffi pkg-config
```

### Debian / Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y pandoc \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
    libpangocairo-1.0-0
```

### ⚠️ Importante: usar un venv en macOS

El Python del sistema de macOS
(`/Library/Frameworks/Python.framework/...`) **no respeta
`DYLD_LIBRARY_PATH` para las libs nativas de brew**. Por eso,
en macOS, WeasyPrint falla con `cannot load library 'libgobject-2.0-0'`
cuando se instala globalmente.

**Solución**: instalar `mirror-pdf-drive` en un venv aislado,
NO en el Python del framework. El venv hereda correctamente
las libs nativas vía `DYLD_LIBRARY_PATH` o `brew --prefix`.

```bash
python -m venv ~/.venvs/mirror-pdf-drive  # o donde prefieras
source ~/.venvs/mirror-pdf-drive/bin/activate
pip install mirror-pdf-drive
```

Y antes de invocar el CLI, **siempre activá el venv** (o usá
`pipx` para aislarlo aún más).

### Verificar

```bash
# En el venv activado
python -c "import weasyprint; print(weasyprint.__version__)"
# Esperado: 60.0 o superior
```

Si tira `OSError: cannot load library`, las libs nativas no
están visibles. Verificá que `brew list | grep -E "(pango|cairo|glib|harfbuzz)"`
muestre las 4 paquetes.

---

## [Una vez por máquina] Configurar OAuth de Google Drive

`mirror-pdf-drive` usa OAuth con `drive.file` scope (permite
crear y modificar archivos en Drive, pero no borrar la cuenta
entera). La primera vez tenés que:

### 1. Crear un proyecto en GCP

1. Andá a https://console.cloud.google.com/
2. "Select a project" → "New project" → nombre sugerido:
   `mirror-pdf-drive` (o tu nombre preferido)
3. Anotá el **Project ID** para después

### 2. Habilitar la Google Drive API

1. En el menú lateral: **APIs & Services** → **Library**
2. Buscá "Google Drive API" → click → **Enable**

### 3. Configurar la pantalla de consentimiento

1. **APIs & Services** → **OAuth consent screen**
2. Tipo: **External** (o Internal si tenés Google Workspace)
3. Completá:
   - App name: `mirror-pdf-drive` (o tu nombre)
   - User support email: tu email
   - Developer contact: tu email
4. **Scopes**: dejá los defaults
5. **Test users**: **agregá tu email** (importante, sino vas a
   ver "Acceso bloqueado" en el paso de OAuth)
6. Save

### 4. Crear OAuth 2.0 Client ID

1. **APIs & Services** → **Credentials** → **Create credentials** → **OAuth client ID**
2. Application type: **Desktop app**
3. Name: `mirror-pdf-drive-cli` (o el que prefieras)
4. Click **Create**
5. Click **Download JSON**

### 5. Guardar el client_secret.json

```bash
mkdir -p ~/.config/mirror-pdf-drive
mv ~/Downloads/client_secret_*.json ~/.config/mirror-pdf-drive/client_secret.json
```

> **Importante**: este archivo contiene un secreto. NO lo
> commitees a ningún repo. Ya está cubierto por
> `mirror-pdf-drive.config.yaml` y `client_secret.json` en
> el `.gitignore` del template.

### 6. Crear la carpeta raíz en Drive

1. Andá a https://drive.google.com/
2. **+ New** → **Folder** → nombre `mirror-pdf-drive` (o lo
   que prefieras) → **Create**
3. Hacé doble click en la carpeta recién creada para abrirla
4. Copiá el **Folder ID** de la URL:
   ```
   https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz
                                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                            este es el ID
   ```

### 7. Autorizar la app (primera corrida)

```bash
mirror-pdf-drive --init
```

Esto abre el browser, te muestra la pantalla de Google
"App no verificada" (es normal en modo Testing), hacés
click en **Advanced** → **Go to mirror-pdf-drive (unsafe)**,
después **Allow**, y el browser redirige a `localhost`
con error. **Eso es OK** — el `mirror-pdf-drive` ya capturó
el código y guardó `token.json` en `~/.config/mirror-pdf-drive/`.

### Verificar

```bash
ls ~/.config/mirror-pdf-drive/
# Esperado: client_secret.json  token.json

python3 -c "
import json
t = json.load(open('/Users/sebailla/.config/mirror-pdf-drive/token.json'))
print('scopes:', t.get('scopes'))
print('expiry:', t.get('expiry'))
print('client_id:', t.get('client_id'))
"
# Esperado: scopes: ['https://www.googleapis.com/auth/drive.file']
#          expiry: una fecha en el futuro (~4 horas)
#          client_id: el mismo que el client_secret.json
```

---

## [Una vez por proyecto] Crear el config del proyecto

El config le dice al CLI:
- Dónde están los `.md` source
- Dónde guardar los PDFs locales
- A qué carpeta de Drive subirlos
- Cómo autenticarse

### 1. Descargar el template

```bash
cd /path/to/your-project
curl -fsSL https://raw.githubusercontent.com/Sebailla/mirror-pdf-drive/main/mirror-pdf-drive.config.example.yaml \
     -o mirror-pdf-drive.config.yaml
```

### 2. Editar los paths

Abrí `mirror-pdf-drive.config.yaml` y ajustá:

```yaml
version: 1

source:
  root: ./docs           # ← cambiá a tu carpeta con .md (ej. ./Documents-es)
  include: ["**/*.md"]
  exclude: []
  max_depth: 10

output:
  root: ./dist/mirror-pdf-drive   # ← PDFs locales van acá
  clean: false

render:
  # Defaults son profesionales (Inter/Roboto, WCAG AA en blanco).
  # Solo sobreescribí lo que necesites customizar.
  page_size: A4
  margins: {top: 2.0, bottom: 2.0, left: 2.0, right: 2.0}
  metadata:
    title: "Mi Proyecto"
    author: "Sebastián Illa"
  # font_family: "Inter, Roboto, Helvetica, sans-serif"
  # font_file: null  # path a .ttf/.otf para embeber via @font-face
  # body_color: "#1a1a1a"
  # heading_color: "#000000"
  # link_color: "#0563c1"
  # code_color: "#1a1a1a"
  # code_bg_color: "#f6f8fa"
  # css_file: null  # override total con tu propio CSS

drive:
  root_folder_id: "TU_FOLDER_ID_DE_DRIVE"   # ← obligatorio
  # project_folder_name: opcional, default = nombre del directorio actual
  conflict_strategy: skip                    # skip | replace | version

auth:
  dir: ~/.config/mirror-pdf-drive
```

**Importante**:
- `drive.root_folder_id` es el ID de la carpeta raíz en Drive
  donde se van a crear las subcarpetas por proyecto.
- NO necesitás `project_folder_name` salvo que quieras override
  del nombre auto-detectado del CWD.
- NO commitees este archivo si tiene datos sensibles (Folder ID
  público está OK, pero `client_secret.json` y `token.json` NO).

#### Tipografía y color (v0.5.0+)

Los defaults de `render` son profesionales y no requieren
configuración:

- **Tipografía**: Inter/Roboto como preferred, fallback a
  Helvetica/Arial/sans-serif del sistema.
- **Colores**: validados para WCAG AA en fondo blanco
  (contraste ≥ 4.5:1).
- **CSS generado**: respeta los colores inline del MD original
  (los `<span style="color: ...">` se preservan).
- **CSS cacheado**: en `output.root/.mirror-pdf-drive-cache/`
  con un hash de la config, no se regenera en cada corrida.

Si querés customizar:

```yaml
render:
  # Custom font stack (ej. usar SF Pro en vez de Inter)
  font_family: "'SF Pro Display', Helvetica, sans-serif"

  # Embeber font custom (debe existir en disco)
  font_file: /Users/sebailla/fonts/Inter-Regular.ttf

  # Custom colors
  body_color: "#222222"
  link_color: "#cc0066"
```

Para control total del CSS (márgenes custom, headers,
footer, etc.), pasá un archivo CSS completo:

```yaml
render:
  css_file: ~/my-styles.css
```

Si pasás `css_file`, los defaults se ignoran totalmente.
La skill de Pi de `mirror-pdf-drive` documenta todos los
campos y los defaults actuales. Ver la sección "Tipografía y
color" de la SKILL.md.

### 3. Actualizar .gitignore (recomendado)

Agregá al `.gitignore` del proyecto:

```gitignore
# mirror-pdf-drive runtime
client_secret.json
token.json

# mirror-pdf-drive config local
mirror-pdf-drive.config.yaml

# mirror-pdf-drive output (ya cubierto por dist/ en muchos proyectos)
dist/mirror-pdf-drive/
```

Si el config tiene paths específicos del proyecto que sí querés
versionar (ej. un template compartido), nombralo distinto
(`mirror-pdf-drive.config.example.yaml`).

### Verificar

```bash
# Activá el venv si usás uno
source ~/.venvs/mirror-pdf-drive/bin/activate

# Probá que el config se carga
mirror-pdf-drive --dry-run
```

**Esperado**: lista de archivos a renderizar con la jerarquía
de Drive donde se subirían. Ejemplo:
```
[DRY-RUN] render: docs/README.md -> dist/mirror-pdf-drive/README.pdf
[DRY-RUN] upload: README.pdf -> folder <root_id>/<project_name>
[DRY-RUN] render: docs/operacion/troubleshooting.md -> dist/mirror-pdf-drive/operacion/troubleshooting.pdf
[DRY-RUN] upload: troubleshooting.pdf -> folder <root_id>/<project_name>/operacion
Renderizados: 2. Subidos: 0. Omitidos: 0. Fallos: 0.
Drive: <root_id>/<project_name>/
```

Si dice `Renderizados: 0. Subidos: 0. Fallos: 0.`, hay un
problema con `source.root` o el config. Verificá que el
directorio source existe y tiene `.md` adentro.

---

## [Cada corrida] Usar el CLI

### Comandos principales

| Comando | Para qué |
|---|---|
| `mirror-pdf-drive` | Corrida normal. Idempotente. |
| `mirror-pdf-drive --dry-run` | Ver qué haría sin subir. |
| `mirror-pdf-drive --no-upload` | Solo generar PDFs locales. |
| `mirror-pdf-drive --force` | Regenerar todo, ignorando mtime. |
| `mirror-pdf-drive --verbose` | Logs en DEBUG. |
| `mirror-pdf-drive --init` | Re-autorizar OAuth (si el token venció). |
| `mirror-pdf-drive --version` | Versión del CLI. |
| `mirror-pdf-drive --help` | Lista de flags. |

### Flags avanzados

| Flag | Para qué |
|---|---|
| `--config <path>` | Override del path al YAML. |
| `--source-dir <path>` | Override del `source.root` del config. |
| `--output-dir <path>` | Override del `output.root` del config. |
| `--folder-id <id>` | Override del `folder_id` legacy (no de `root_folder_id`). |
| `--project-folder-name <name>` | Override del nombre del proyecto (default: CWD basename). |

### Ejemplos de uso

```bash
# Primera vez en un proyecto nuevo (sin PDFs locales)
mirror-pdf-drive

# Después de editar un .md, regenerar solo ese
mirror-pdf-drive

# Regenerar todo (cuando querés forzar)
mirror-pdf-drive --force

# Probar sin subir (cuando querés ver qué pasaría)
mirror-pdf-drive --dry-run

# Solo generar PDFs locales (sin tocar Drive)
mirror-pdf-drive --no-upload

# Diagnosticar un fallo
```

### Output esperado
mirror-pdf-drive --verbose

Al final de cada corrida, el summary muestra:

```
Renderizados: N. Subidos: M. Omitidos: K. Fallos: F.
Drive: <root_folder_id>/<project_name>/
```

Donde:
- **N** = archivos PDF generados
- **M** = archivos subidos a Drive (puede ser menor que N si había
  archivos con el mismo nombre que se skipearon)
- **K** = archivos que se skipearon (PDF local más nuevo que el MD)
- **F** = archivos que fallaron (render o upload)
- **Drive:** = la ubicación en Drive donde se subieron

### Exit codes

| Exit | Significado | Solución |
|---|---|---|
| 0 | OK | Nada. |
| 1 | Error de config | Corré con `--verbose`, leé el error, corregí el YAML. |
| 2 | Auth faltante o vencida | Corré `mirror-pdf-drive --init`. |
| 3 | Falló el render de uno o más archivos | Pegá el log con `--verbose`. |
| 4 | Falló la subida de uno o más PDFs | Pegá el log. |
| 5 | Error inesperado (bug) | Pegá el log completo. |

---

## Automatización (opcional)

### Cron / scheduled task

Si querés que el mirror corra automáticamente cada vez que
cambian los docs:

```bash
# En crontab (corre cada hora)
0 * * * * cd /path/to/project && mirror-pdf-drive --no-upload
```

### Pre-commit hook (si querés validación local)

```bash
# .git/hooks/pre-commit
#!/bin/bash
mirror-pdf-drive --dry-run
```

### CI

El proyecto `mirror-pdf-drive` ya incluye un workflow de
GitHub Actions en `.github/workflows/test.yml` que corre
`pytest -q` en cada push y PR. Para tus proyectos, podés
copiar ese workflow y adaptarlo.

---

## Troubleshooting

### "OAuth token not found" o "Acceso bloqueado"

- Verificá que `~/.config/mirror-pdf-drive/{client_secret,token}.json` existen.
- Si el token venció, corré `mirror-pdf-drive --init` para re-autorizar.
- Si Google dice "Acceso bloqueado", agregá tu email como
  **Test user** en GCP Console → APIs & Services → OAuth consent screen.

### "WeasyPrint could not import some external libraries"

En macOS, el Python del framework no encuentra las libs nativas.
**Solución**: usá un venv (ver "Usar un venv en macOS" arriba).

### "No se encontró el archivo de configuración"

- Verificá que `mirror-pdf-drive.config.yaml` está en el
  directorio desde donde corrés el CLI.
- O usá `mirror-pdf-drive --config /path/to/config.yaml`.

### "File not found: 13_5_kYsHpUXD0t2lEqrGZzEp11QzS0Uo"

El Folder ID de Drive es inválido o no tenés acceso.
- Verificá que el ID esté bien copiado de la URL de Drive.
- Verificá que la carpeta existe y que la app OAuth tiene
  permisos sobre ella (es tu cuenta, no la de otro).

### "No such file or directory: 'mirror-pdf-drive'"

Estás corriendo el comando desde un directorio que no tiene
`mirror-pdf-drive.config.yaml`. Andá al directorio del
proyecto o usá `--config`.

### Los PDFs se suben a la raíz de Drive en vez de a una subcarpeta

Versión vieja. Actualizá a v0.4.0+ (`pip install --upgrade
mirror-pdf-drive`). El feature de project folder isolation
se introdujo en v0.4.0.

### El nombre de la subcarpeta en Drive no es lo que esperaba

Default: `Path.cwd().name`. Si corrés desde un subdirectorio
del proyecto, podés:

- Correr desde la raíz del proyecto.
- Usar `mirror-pdf-drive --project-folder-name "nombre-correcto"`.
- O setear `project_folder_name: "nombre-correcto"` en el config.

### "Cannot find package mirror-pdf-drive"

El CLI no está instalado. Ver:

```bash
pip show mirror-pdf-drive
# Si dice "WARNING: Package(s) not found", instalá:
pip install mirror-pdf-drive
# O si lo querés desde el repo fuente:
pip install -e .
```

---

## Setup en 60 segundos (TL;DR)

Para alguien que ya tiene todo configurado y solo necesita
agregar un proyecto nuevo:

```bash
# 1. En el directorio del proyecto
curl -fsSL https://raw.githubusercontent.com/Sebailla/mirror-pdf-drive/main/mirror-pdf-drive.config.example.yaml \
     -o mirror-pdf-drive.config.yaml

# 2. Editar paths y drive.root_folder_id
$EDITOR mirror-pdf-drive.config.yaml

# 3. Probar
mirror-pdf-drive --dry-run

# 4. Correr
mirror-pdf-drive
```

Eso es todo.

---

## Setup completo desde cero (TL;DR)

Si es la primera vez en una máquina:

```bash
# 1. Instalar CLI
pip install mirror-pdf-drive

# 2. Instalar deps de sistema (macOS)
brew install pandoc pango cairo glib gobject-introspection \
             harfbuzz fribidi libffi pkg-config

# 3. Setup OAuth
#    a. Crear proyecto en GCP, habilitar Drive API, crear
#       OAuth Desktop client, descargar client_secret.json
#    b. Crear carpeta en Drive, copiar el Folder ID
#    c. Mover client_secret.json a ~/.config/mirror-pdf-drive/
#    d. Agregar tu email como Test user en OAuth consent screen
#    e. Correr mirror-pdf-drive --init (autoriza con el browser)

# 4. En cada proyecto
curl -fsSL https://raw.githubusercontent.com/Sebailla/mirror-pdf-drive/main/mirror-pdf-drive.config.example.yaml \
     -o mirror-pdf-drive.config.yaml
$EDITOR mirror-pdf-drive.config.yaml
mirror-pdf-drive
```

---

## Referencias

- Repo: https://github.com/Sebailla/mirror-pdf-drive
- Release v0.5.1: https://github.com/Sebailla/mirror-pdf-drive/releases/tag/v0.5.1
- Release v0.5.0: https://github.com/Sebailla/mirror-pdf-drive/releases/tag/v0.5.0
- Release v0.4.1: https://github.com/Sebailla/mirror-pdf-drive/releases/tag/v0.4.1
- Config de ejemplo: https://github.com/Sebailla/mirror-pdf-drive/blob/main/mirror-pdf-drive.config.example.yaml
- Validación de la skill: `docs/operacion/validar-skill-pi.md`
- Códigos de error: `docs/operacion/codigos-de-error.md`
- Troubleshooting detallado: `docs/operacion/troubleshooting.md`
