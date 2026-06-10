# `mirror-pdf-drive` — Documentación de Diseño

> **Estado:** Diseño aprobado, pendiente de implementación.
> **Última revisión:** 2026-06-10
> **Autor:** Sebastián Illa

Este directorio contiene el diseño completo de la herramienta
`mirror-pdf-drive`: una utilidad CLI que convierte la documentación
Markdown de un proyecto (en particular, el espejo español
`Documents-es/`) a PDFs y los sube a una carpeta de Google Drive.

La herramienta **no vive en el repositorio del proyecto**. Vive en
`~/.local/share/mirror-pdf-drive/` y se invoca desde cualquier
proyecto mediante un slash command de Pi o ejecutando el binario
directamente. La configuración, eso sí, **es por proyecto** y vive
en `mirror-pdf-drive.config.yaml` en la raíz de cada repo.

Este directorio es **un espacio de diseño**, no un proyecto
versionado. No tiene git, no tiene dependencias, no se compila.
Cuando llegue el momento de implementar, la implementación se hace
en otro lado; este directorio queda como referencia para futuras
modificaciones.

---

## Índice de la documentación

| Sección | Para qué sirve | Cuándo leerla |
|---|---|---|
| [`arquitectura/`](./arquitectura/) | Cómo están conectadas las piezas, qué responsabilidades tiene cada una, qué interfaces se exponen. | Antes de cambiar la separación de archivos o agregar un componente nuevo. |
| [`script/`](./script/) | Diseño del script Python: módulos, dependencias, CLI, flujo de ejecución, manejo de errores, OAuth. | Antes de tocar el código del script, agregar un módulo nuevo o cambiar el comportamiento de una corrida. |
| [`configuracion/`](./configuracion/) | El archivo `mirror-pdf-drive.config.yaml`: schema, defaults, validación, ejemplos. | Antes de agregar un campo nuevo al config, cambiar defaults o diagnosticar un error de carga. |
| [`skill/`](./skill/) | La `SKILL.md` de Pi: qué dice, cómo se invoca, qué comportamiento tiene la skill, qué pasa cuando algo falla. | Antes de cambiar el slash command, agregar un subcomando o reescribir la cara visible de la herramienta. |
| [`operacion/`](./operacion/) | Cómo correr la herramienta end-to-end: primera corrida, corridas normales, OAuth flow, troubleshooting, mantenimiento. | Cuando algo falla en una corrida real, o cuando hay que rotar el token, cambiar la carpeta de Drive, o agregar un repo nuevo a la lista. |
| [`referencias/`](./referencias/) | Decisiones de diseño con su racional, dependencias externas, excepciones documentadas en `AGENTS.md`, changelog de diseño. | Cuando hay que entender **por qué** algo es como es, no **cómo** funciona. |

---

## Mapa visual del sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Tu sesión de Pi o tu shell                       │
│                                                                     │
│   $ /mirror-pdf-drive        (slash command de Pi)                  │
│   $ mirror-pdf-drive         (binario directo en shell)             │
└──────────────┬───────────────────────────┬───────────────────────────┘
               │                           │
               ▼                           ▼
   ┌──────────────────────┐    ┌──────────────────────────────┐
   │ SKILL.md de Pi       │    │ Binario Python en            │
   │ ~/.pi/agent/skills/  │    │ ~/.local/share/              │
   │ mirror-pdf-drive/    │    │ mirror-pdf-drive/.venv/      │
   │                      │    │ bin/mirror-pdf-drive         │
   │  - Carga contexto    │    │                              │
   │  - Valida precond.   │    │  - Parsea args               │
   │  - Llama al binario  │    │  - Carga config              │
   └──────────┬───────────┘    │  - Renderiza MD → PDF         │
              │                │  - Sube PDF a Drive          │
              └────────────────┤  - Reporta resultado          │
                               └──────────┬───────────────────┘
                                          │
                          ┌───────────────┼───────────────┐
                          ▼               ▼               ▼
                  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
                  │ Tu proyecto  │ │ pandoc +     │ │ Google Drive │
                  │ con su       │ │ weasyprint   │ │ API (OAuth)  │
                  │ config local │ │              │ │              │
                  │              │ │ Local        │ │ Remoto       │
                  └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Principios de diseño

Estos principios están detrás de **cada** decisión de diseño de
la herramienta. Si vas a modificarla, tenelos a mano; si una
modificación los viola, documentá **por qué** la violás.

### 1. La herramienta es global, la configuración es local

El **código** vive en `~/.local/share/mirror-pdf-drive/`. El
**config** vive en cada proyecto. Esto permite que un solo binario
sirva para múltiples proyectos con convenciones distintas, sin
duplicar lógica.

**Por qué no al revés:** si el código fuera por proyecto, cada repo
tendría su propia versión de `mirror-pdf-drive` y los bugs se
arreglarían N veces.

**Por qué no todo global:** si la config fuera global, no podrías
tener dos proyectos con páginas A4 y Letter al mismo tiempo, ni
excluir archivos distintos en cada uno.

### 2. El script es runtime-agnóstico

No asume que está siendo llamado por Pi. No lee variables de Pi.
No tiene magic. Si lo ejecutás con `python -m mirror_pdf_drive`,
funciona igual. Si lo ejecutás desde un cron, también.

**Implicación:** la skill de Pi es un **wrapper delgado** que
delega al binario. La lógica vive en el binario, no en la skill.

### 3. Idempotencia por defecto

Correr la herramienta dos veces seguidas con el mismo input no
genera PDFs duplicados ni sube dos veces a Drive. La comparación
es por `mtime`: si el PDF destino es más nuevo que el MD fuente,
se skipea. `--force` rompe la idempotencia explícitamente.

**Por qué importa:** Drive tiene quotas. Subir el mismo PDF 50
veces porque alguien corre el comando cada noche sin verificar
es un bug, no una feature.

### 4. Falla loudly, fix localmente

Cada error tiene:
- Un **código** estable (`AUTH_REQUIRED`, `RENDER_FAILED`, etc.).
- Un **mensaje** con contexto (qué archivo, qué intento, qué falló).
- Un **exit code** que la skill de Pi puede leer.

No hay `try/except` genéricos. Si algo explota, la traza sale
entera. El usuario (vos o un agente) puede leer el error, buscar
el código en `operacion/troubleshooting.md`, y arreglar el
problema sin tener que adivinar.

### 5. OAuth con scope mínimo

La herramienta pide `drive.file`, no `drive` completo. Esto
significa que **solo puede acceder a archivos que ella misma
creó**. No puede leer tus otros Docs, no puede borrar archivos
ajenos, no puede listar tu Drive completo.

**Por qué importa:** si el `token.json` se filtra, el atacante
solo puede ver y manipular los PDFs que subió esta herramienta.
Tus otros archivos de Drive están a salvo.

### 6. La doc se mantiene en español

Este directorio está en español por convención del usuario
(ver `AGENTS.md` raíz §13). El código del script, los nombres de
funciones, los mensajes de log y los exit codes van en **inglés**
(convención universal de Python). La cara visible al usuario
(mensajes de error amigables, la SKILL.md) va en **español**.

**Regla clara:**
- Identificadores de código: inglés.
- Mensajes de log y exit codes: inglés.
- Mensajes de error al usuario final: español.
- Doc: español en este directorio, español en `Documents-es/` del
  proyecto, inglés en el repo de la herramienta si se sube a uno.

---

## Cómo usar este directorio

### Si estás por implementar la herramienta

1. Lee `arquitectura/descripcion-general.md` para tener el mapa.
2. Lee `script/modulos.md` y `script/cli.md` para entender las
   piezas.
3. Lee `configuracion/schema.md` para saber qué config necesitás.
4. Lee `skill/SKILL.md` (la versión de diseño, no la final) para
   entender la cara visible.
5. Empezá por `mirror.py` con tests que validen el parseo de
   args, después seguí con `config.py`, después `renderer.py`,
   después `drive_client.py`, finalmente `auth.py` y la
   integración.

### Si estás modificando la herramienta

1. Identificá qué archivo del script cambia.
2. Andá a la sección correspondiente de `script/`.
3. Leé los "Puntos de extensión" y "No tocar" de ese módulo.
4. Modificá el código siguiendo la convención del módulo.
5. Actualizá la doc de diseño en este directorio para reflejar
   el cambio.
6. Si el cambio afecta el schema del config, actualizá
   `configuracion/schema.md` y bumpeá `version` en el config.

### Si algo falla en producción

1. Anotá el exit code y el mensaje de error.
2. Buscá el exit code en `operacion/codigos-de-error.md`.
3. Seguí el flujo de troubleshooting de `operacion/troubleshooting.md`.

---

## Lo que **no** está en este directorio

- **El código del script.** Esto es diseño, no implementación. El
  código va en `~/.local/share/mirror-pdf-drive/` cuando se
  implemente.
- **La SKILL.md final.** Está versionada como diseño en
  `skill/SKILL.md` (este directorio). El archivo final va en
  `~/.pi/agent/skills/mirror-pdf-drive/SKILL.md`.
- **El config real de un proyecto.** Cada proyecto tiene su
  `mirror-pdf-drive.config.yaml`. Este directorio tiene el schema
  y los ejemplos.
- **El `AGENTS.md` raíz del proyecto.** La excepción §13.6 que
  documenta esta herramienta como excepción a la atomicidad
  inglés-español vive en el `AGENTS.md` del proyecto, no acá.

---

## Próximos pasos

Cuando termines de leer este directorio y estés conforme con el
diseño, los siguientes pasos son:

1. Implementar el script en `~/.local/share/mirror-pdf-drive/`.
2. Probarlo contra `Documents-es/openspec/AGENTS.md` (que es el
   único archivo del espejo español en este proyecto).
3. Crear la SKILL.md final en `~/.pi/agent/skills/mirror-pdf-drive/`.
4. Modificar el `AGENTS.md` raíz del proyecto para agregar §13.6.
5. Abrir el PR con todos los cambios juntos.
6. Después del merge, archivar el cambio en
   `openspec/changes/mirror-pdf-drive/archive/`.
7. **No** borrar este directorio. Es la referencia de diseño para
   futuras modificaciones.
