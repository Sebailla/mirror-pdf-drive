# Operación — Primera Corrida

> **Paso a paso para configurar `mirror-pdf-drive` desde cero
> en una máquina nueva. Asume que la herramienta ya está
> implementada (script en `~/.local/share/mirror-pdf-drive/`).**

## Overview

La primera corrida hace **tres cosas**:

1. Instala las dependencias del sistema (pandoc, weasyprint).
2. Crea un proyecto de GCP con OAuth y baja el `client_secret.json`.
3. Hace el flow de OAuth para autorizar la herramienta.
4. Crea el config del proyecto.
5. Verifica que todo funciona con una corrida de prueba.

Tiempo estimado: **15-30 minutos**, la mayor parte en la
consola de GCP.

## 1. Instalar dependencias del sistema

### macOS con Homebrew

```bash
# Pandoc
brew install pandoc

# Deps de weasyprint (Pango, Cairo, GDK-Pixbuf)
brew install pango cairo gdk-pixbuf libffi

# Python 3.11+ (si no lo tenés)
brew install python@3.11
```

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y pandoc python3-pip python3-venv \
  libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
  libcairo2 libgdk-pixbuf2.0-0 libffi-dev
```

### Windows

No documentado todavía. Si lo necesitás, abrí un issue. (La
herramienta está pensada para macOS/Linux.)

## 2. Instalar la herramienta Python

```bash
# Crear el directorio de la herramienta
mkdir -p ~/.local/share/mirror-pdf-drive
cd ~/.local/share/mirror-pdf-drive

# Si tenés el código fuente (ej. clonando el repo donde vive)
git clone <url-del-repo> .

# Crear virtualenv
python3.11 -m venv .venv
source .venv/bin/activate

# Instalar
pip install -e .

# Verificar que el binario funciona
mirror-pdf-drive --version
# Debería imprimir: mirror-pdf-drive 0.1.0
```

## 3. Crear el proyecto en GCP y bajar `client_secret.json`

### 3.1. Crear el proyecto

1. Ir a [Google Cloud Console](https://console.cloud.google.com/).
2. Arriba a la izquierda, click en el selector de proyecto
   → "Nuevo proyecto".
3. Nombre: `mirror-pdf-drive` (o el que quieras).
4. Click "Crear".

### 3.2. Habilitar la Drive API

1. En el menú lateral, ir a "APIs y servicios" → "Biblioteca".
2. Buscar "Google Drive API".
3. Click en el resultado.
4. Click "Habilitar".

### 3.3. Configurar la pantalla de consentimiento OAuth

1. Ir a "APIs y servicios" → "Pantalla de consentimiento de OAuth".
2. User type: "Externo" (a menos que tengas Google Workspace,
   en cuyo caso puede ser "Interno").
3. Completar:
   - **Nombre de la app:** `mirror-pdf-drive`.
   - **Email de soporte:** tu email.
   - **Dominio autorizado:** dejarlo vacío por ahora.
   - **Scopes:** agregar `https://www.googleapis.com/auth/drive.file`.
4. En "Usuarios de prueba" (si es tipo Externo), agregar tu
   propio email.
5. Guardar.

### 3.4. Crear el OAuth Client ID

1. Ir a "APIs y servicios" → "Credenciales".
2. Arriba, click "Crear credenciales" → "ID de cliente de OAuth".
3. Tipo: **Aplicación de escritorio** (Desktop app).
4. Nombre: `mirror-pdf-drive-desktop`.
5. Click "Crear".
6. En la pantalla que aparece, click "Descargar JSON".
7. Renombrar el archivo a `client_secret.json`.
8. Moverlo a `~/.config/mirror-pdf-drive/`:

   ```bash
   mkdir -p ~/.config/mirror-pdf-drive
   mv ~/Downloads/client_secret.json ~/.config/mirror-pdf-drive/
   chmod 600 ~/.config/mirror-pdf-drive/client_secret.json
   ```

## 4. Crear el config del proyecto

En la raíz de tu proyecto (donde está `Documents-es/`):

```bash
cat > mirror-pdf-drive.config.yaml <<EOF
version: 1
source:
  root: "Documents-es"
EOF
```

Para más opciones, ver [`../configuracion/ejemplos.md`](../configuracion/ejemplos.md).

## 5. Hacer el bootstrap de OAuth

```bash
# Desde la raíz del proyecto
mirror-pdf-drive --init
```

Esto:
1. Valida el config.
2. Detecta el `client_secret.json`.
3. Abre el browser para que autorices.
4. Guarda el `token.json` en `~/.config/mirror-pdf-drive/`.
5. Si `drive.folderId` es null, busca o crea la carpeta
   "Documents-es PDFs" en tu Drive.
6. Imprime el ID de la carpeta si la creó, para que lo
   agregues al config.

## 6. Verificar con un dry-run

```bash
mirror-pdf-drive --dry-run
```

Deberías ver algo como:

```
Iniciando mirror-pdf-drive...
[DRY-RUN] render: Documents-es/openspec/AGENTS.md -> dist/mirror-pdf-drive/openspec/AGENTS.pdf
[DRY-RUN] upload: AGENTS.pdf -> folder abc123 (strategy: skip)

Listo. Renderizados: 0. Subidos: 0. Omitidos: 0. Fallos: 0. (dry-run)
```

## 7. Corrida real

```bash
mirror-pdf-drive
```

Debería:
1. Renderizar todos los `.md` bajo `Documents-es/`.
2. Subirlos a Drive.
3. Imprimir un resumen.
4. Salir con exit 0.

Si algo falla, ver [`troubleshooting.md`](./troubleshooting.md).

## 8. Verificar en Drive

1. Ir a [drive.google.com](https://drive.google.com/).
2. Buscar la carpeta "Documents-es PDFs" (o el nombre que
   configuraste).
3. Verificar que los PDFs están ahí, con el contenido
   correcto.

## Checklist de primera corrida

- [ ] Deps del sistema instaladas (pandoc, pango, cairo).
- [ ] Python 3.11+ instalado.
- [ ] Tool instalada en `~/.local/share/mirror-pdf-drive/`.
- [ ] Proyecto GCP creado.
- [ ] Drive API habilitada.
- [ ] Pantalla de consentimiento OAuth configurada.
- [ ] OAuth Client ID de tipo "Desktop" creado.
- [ ] `client_secret.json` bajado y guardado en
  `~/.config/mirror-pdf-drive/`.
- [ ] `mirror-pdf-drive.config.yaml` en la raíz del proyecto.
- [ ] `mirror-pdf-drive --init` corrió OK.
- [ ] `mirror-pdf-drive --dry-run` muestra los archivos esperados.
- [ ] `mirror-pdf-drive` corrió OK y los PDFs están en Drive.

## Próximas corridas

Una vez que la primera corrida funciona, las siguientes son:

```bash
mirror-pdf-drive
```

…y listo. Ver [`corridas-normales.md`](./corridas-normales.md).
