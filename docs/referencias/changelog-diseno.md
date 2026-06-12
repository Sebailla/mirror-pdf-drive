# Referencias — Changelog de Diseño

> **Bitácora de las decisiones y cambios al diseño de
> `mirror-pdf-drive`. Cada vez que se modifica este
> directorio, se agrega una entrada acá.**

## Formato

```markdown
## [YYYY-MM-DD] — <título corto>

**Por qué:** <una oración con la motivación>

**Cambios:**
- `<archivo>`: <qué cambió>
- `<archivo>`: <qué cambió>

**Decisiones afectadas:** D-XXX (link al ID en decisiones-de-diseno.md)

**Impacto en el usuario:** <qué tiene que hacer el usuario si algo>
```

## Entradas

### [2026-06-10] — Diseño inicial

**Por qué:** el usuario pidió convertir la documentación
bilingüe (`Documents-es/`) a PDFs y subirlos a Google Drive.
Después de explorar el repo, se decidió que la herramienta
es global (vive en `~/.local/share/mirror-pdf-drive/`), con
config local (por proyecto), SKILL.md para Pi (no OpenCode
todavía), y OAuth con scope `drive.file`.

**Cambios:**
- `README.md`: índice de toda la documentación.
- `arquitectura/descripcion-general.md`: visión general de las
  tres capas (orquestación, módulos, contratos).
- `arquitectura/separacion-de-archivos.md`: árbol de archivos
  del script con responsabilidades por archivo.
- `script/modulos.md`: diseño detallado de los 6 archivos
  Python (mirror, config, renderer, drive_client, auth,
  exceptions).
- `script/cli.md`: diseño del CLI, flags, exit codes,
  variables de entorno.
- `script/renderizado.md`: justificación de pandoc +
  weasyprint, args, metadata, CSS, troubleshooting de
  renderizado.
- `configuracion/schema.md`: schema completo del
  `mirror-pdf-drive.config.yaml` con tipos, defaults,
  validación, semántica de cada campo.
- `configuracion/ejemplos.md`: 6 ejemplos de configs
  (mínimo, típico, con CSS, multi-doc, sin `Documents-es/`,
  debug).
- `skill/skill.md`: diseño de la SKILL.md (qué es, qué no
  es, frontmatter, secciones, mensajes).
- `skill/SKILL.md`: versión final lista para copiar a
  `~/.pi/agent/skills/mirror-pdf-drive/SKILL.md`.
- `operacion/primera-corrida.md`: paso a paso desde cero
  (instalar deps, GCP, OAuth, primer run).
- `operacion/corridas-normales.md`: uso día a día, dry-run,
  force, no-upload, paths específicos, multi-cuenta.
- `operacion/codigos-de-error.md`: exit codes y códigos de
  error (AppError.code), tabla rápida de diagnóstico.
- `operacion/troubleshooting.md`: guía de diagnóstico
  paso a paso por exit code.
- `referencias/decisiones-de-diseno.md`: 10 decisiones (D-001
  a D-010) con su "por qué" y cuándo revertir.
- `referencias/dependencias.md`: lista completa de deps
  (sistema, Python, desarrollo) con versiones y licencias.
- `referencias/cuando-modificar.md`: guía de scope (qué
  entra, qué no, cómo chained-PR si es grande).
- `referencias/changelog-diseno.md`: este archivo.

**Decisiones afectadas:**
- D-001: código global, config local.
- D-002: pandoc + weasyprint.
- D-003: scope `drive.file`.
- D-004: idempotencia por mtime.
- D-005: errores con códigos estables.
- D-006: script runtime-agnostic.
- D-007: doc en español, código en inglés.
- D-008: config por proyecto, no global.
- D-009: herramienta como excepción documentada (§13.6).
- D-010: SKILL.md en Pi, no en OpenCode.

**Impacto en el usuario:** ninguno todavía. Esto es diseño,
no implementación. Cuando se implemente, el primer impacto
será la §13.6 nueva en el AGENTS.md del proyecto, y la
SKILL.md en `~/.pi/agent/skills/`.

---

## Pendiente de diseño

Cosas que aparecieron en la conversación pero que no se
cerraron como diseño. Vivir acá hasta que se decida.

### Auth storage: ¿1Password / keychain vs XDG estándar?

**Contexto:** en la conversación inicial, el usuario votó
"1Password / keychain" para `client_secret.json` y
`token.json`. Después votó "XDG estándar". No hubo decisión
final.

**Opciones:**
- A. **XDG estándar.** `~/.config/mirror-pdf-drive/` con
  ambos archivos. Simple, funciona siempre.
- B. **1Password / keychain.** Sin archivos en disco, el
  script los lee al vuelo. Más seguro, requiere `op` CLI o
  keychain access.
- C. **Híbrido.** `client_secret.json` en 1Password, materializado
  al primer arranque. `token.json` en XDG (rotación frecuente).

**Recomendación actual:** A (XDG) por simplicidad. Documentar
cómo migrar a B si el usuario quiere más seguridad.

### §13.6 nombrado

**Contexto:** falta decidir cómo se llama la nueva cláusula
en el AGENTS.md raíz del proyecto. Opciones:
- "PDF + Google Drive mirror"
- "PDF mirror to Google Drive"
- "External PDF mirror (Drive)"

**Recomendación actual:** "PDF + Google Drive mirror", para
ser consistente con §13.5 ("OneNote mirror").

### Conflict de preflight con config.yaml

**Contexto:** el `openspec/config.yaml` del proyecto tiene
`chainedPrStrategy: auto-forecast` y `reviewBudgetLines: 400`.
En la conversación, el usuario votó `single-pr-default` y
`200`. No hubo decisión final.

**Recomendación actual:** respetar la votación del usuario
(single-pr-default, 200) y bumpear el config al final del
cambio. Pero la decisión queda abierta hasta que vuelva al
SDD formal.

### `auth-foundation` en curso

**Contexto:** hay un cambio OpenSpec `auth-foundation` activo
en el proyecto. El nuevo cambio `mirror-pdf-drive` se
implementa en el mismo repo. ¿Se mergea antes, después, en
paralelo?

**Opciones:**
- A. Secuencial: cerrar `auth-foundation` primero.
- B. Paralelo: branches separados, mismo target develop.
- C. Independiente: el `mirror-pdf-drive` no toca código de
  aplicación, así que no choca con `auth-foundation` (que
  sí toca).

**Recomendación actual:** C. El script vive global, no en
el repo, y la SKILL.md + §13.6 no tocan código de
aplicación. Pero hay que verificar al volver al SDD formal.

### Atribución de autor en los artifacts de OpenSpec

**Contexto:** `openspec/AGENTS.md` define que el `Author:`
de todo artifact de doc es `Sebastián Illa`, sin excepciones.
Esto aplica a los artifacts del cambio `mirror-pdf-drive`
cuando se cree.

**Acción:** cuando un subagente escriba
`openspec/changes/mirror-pdf-drive/*.md`, el frontmatter
debe tener `Author: Sebastián Illa`. Lo mismo para los
espejos en `Documents-es/openspec/changes/mirror-pdf-drive/*.md`
(con `Autor: Sebastián Illa`).

**Bloqueador conocido:** confirmado, no requiere decisión.
