---
title: Validación end-to-end de la skill de Pi
author: Sebastián Illa
version: 0.1.0
status: draft
---

# Validación end-to-end de la skill de `mirror-pdf-drive`

Esta guía explica cómo verificar que la skill de Pi (en
`~/.pi/agent/skills/mirror-pdf-drive/`) se carga correctamente
y se activa con los triggers definidos en su frontmatter.

## Prerrequisitos

Antes de validar, asegurate de tener:

1. La skill instalada en `~/.pi/agent/skills/mirror-pdf-drive/SKILL.md`.
2. El CLI instalado y funcional (`mirror-pdf-drive --version` responde).
3. Si vas a probar el flujo con Drive: `client_secret.json` y
   `token.json` en `~/.config/mirror-pdf-drive/`.
4. Si vas a probar el flujo end-to-end (no solo `--version`): un
   `mirror-pdf-drive.config.yaml` válido en el directorio donde
   abrís pi.
5. Un venv con el CLI y sus deps (recomendado en macOS por el
   tema de las libs nativas de WeasyPrint).

## Pasos

### 1. Abrí una terminal nueva

```bash
cd /Users/sebailla/Documents/Proyectos/2026/mirror-pdf-drive
source .venv/bin/activate
mirror-pdf-drive --version
```

**Esperado**: `mirror-pdf-drive 0.3.0`. Si da error, el problema
es de instalación, no de la skill.

### 2. Abrí pi en este mismo directorio

```bash
pi
```

### 3. Probá los prompts de validación

Ejecutá uno a la vez. Después de cada uno, verificá el resultado
esperado antes de pasar al siguiente.

#### a) Comando explícito (con slash)

```
/mirror-pdf-drive --version
```

**Esperado**: pi lee el `SKILL.md`, ejecuta el binario desde el
venv, reporta `mirror-pdf-drive 0.3.0`.

#### b) Trigger por intención

```
convertir los MD a PDF
```

**Esperado**: pi carga la skill automáticamente porque el
`description:` del frontmatter matchea. Puede que pi pregunte
si querés `--dry-run` o ejecución real.

#### c) Otro trigger por intención

```
regenerar los PDFs de la documentación
```

**Esperado**: pi reconoce la skill y ofrece correr
`mirror-pdf-drive` (probablemente con `--force`).

#### d) Trigger de upload

```
subir los docs a Drive
```

**Esperado**: pi carga la skill y menciona la flag `--no-upload`
y `--init` para el caso de auth faltante.

### 4. Forzar la carga (si los triggers no funcionan)

Si en (3) pi no carga la skill, forzá:

```
/skill mirror-pdf-drive
```

Eso carga la skill explícitamente sin importar el trigger.

### 5. Reportar resultado

Si todo anduvo, la skill está validada. Si algo falló, pegá
el output de pi (con el detalle del trigger usado y la
respuesta del agente) en una sesión de pi nueva y te ayudo
a diagnosticar.

## Cómo sabe pi que cargue la skill

Pi escanea `~/.pi/agent/skills/*/SKILL.md` y carga los
frontmatters. Cuando el prompt del usuario matchea el campo
`description:` de un SKILL.md, pi lo activa.

Para que tu skill sea descubrible:

- El campo `name:` debe matchear el nombre del directorio.
- El campo `description:` debe tener una descripción clara que
  incluya las frases que el usuario típicamente diría
  (triggers de intención).
- Las frases exactas que matchearon se listan en el
  `description:` actual: `/mirror-pdf-drive`, "convertir MD a
  PDF", "subir docs a Drive", "mirror de documentos a PDF",
  "regenerar los PDFs", "correr mirror-pdf-drive".

## Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| pi no reconoce `/mirror-pdf-drive` | La skill no está en `~/.pi/agent/skills/mirror-pdf-drive/SKILL.md` | Re-crear la skill con el frontmatter correcto |
| pi carga otra skill primero | Otra skill tiene un `description:` que matchea antes | Editar el `description:` para ser más específico |
| pi ejecuta `pandoc` directo en vez de `mirror-pdf-drive` | El trigger matchea con `pdf-reader` u otra skill de PDF | Ser más específico en el prompt o forzar con `/skill mirror-pdf-drive` |
| pi no encuentra el binario | El venv no está activo o el binario no está en PATH | Activar el venv antes de abrir pi, o exportar `MIRROR_PDF_DRIVE_AUTH_DIR` y otras env vars |

## Próximos pasos

Una vez validada, podés usar la skill en tu flujo normal:

- Cada vez que cambies docs y quieras regenerar PDFs,
  decí "regenerar los PDFs" en pi.
- Cuando empieces un proyecto nuevo con docs, corré
  `/mirror-pdf-drive --init` la primera vez para autorizar
  Drive.

Si la skill se queda corta, podés iterar el SKILL.md con
más casos o agregar nuevos triggers sin tocar el código del
CLI.
