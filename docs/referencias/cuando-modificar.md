# Referencias — Cuándo Modificar

> **Guía para saber si un cambio que querés hacer entra en
> el scope de la herramienta o no. Si tu cambio no entra,
> probablemente es una herramienta nueva, no una modificación
> de esta.**

## Cambios que entran en scope

Modificás la herramienta si el cambio es **interno a la
herramienta** y no cambia su contrato externo.

### Cambiar comportamiento interno (sí, modificar)

- Optimizar el renderizado (paralelizar, cachear por hash).
- Cambiar la estrategia de reintentos.
- Mejorar mensajes de error.
- Refactorizar la separación de archivos.
- Agregar tests.
- Cambiar el motor de renderizado (ej. de pandoc+weasyprint
  a otra cosa).
- Bump de dependencias.
- Cambiar el formato del log (de text a json, etc.).

### Agregar funcionalidad compatible hacia atrás (sí, modificar)

- Agregar un nuevo flag CLI.
- Agregar un nuevo campo al config (con default).
- Agregar un nuevo código de error.
- Agregar un nuevo comando a la skill (`--status`, por
  ejemplo).

### Cambios de tipo bug fix (sí, modificar)

- Un MD específico no se renderiza.
- El token no se refresca correctamente.
- El script no maneja un error de la API de Drive.
- La idempotencia falla en un edge case.
- El output no coincide con el input.

## Cambios que NO entran en scope

Si el cambio es **un nuevo producto o una nueva integración
mayor**, lo que necesitás es **una herramienta nueva**, no
modificar esta.

### Lo que NO es esta herramienta

- **Subir a otro servicio** (S3, Dropbox, GitHub Releases,
  Notion). Hacé una herramienta nueva o un plugin.
- **Convertir a otros formatos** (DOCX, EPUB, HTML estático).
  Esta es MD → PDF. Otros formatos son otra herramienta
  (o un fork con config distinta).
- **Servir los PDFs en un sitio web**. Necesitás un web
  server, no un CLI.
- **Sincronización bidireccional** (Drive → repo). Esta
  herramienta es unidireccional (repo → Drive).
- **Edición colaborativa**. Drive tiene Google Docs para eso.
- **Indexar o buscar en los PDFs subidos**. Necesitás una
  capa de indexación aparte.

### Cómo saber si tu cambio es scope o no

Preguntate:

1. **¿El cambio mantiene el contrato externo?** (mismos
   flags CLI, mismo schema de config, misma SKILL.md).
   - Sí → entra en scope, modificá.
   - No → no entra, herramiente nueva.

2. **¿El cambio requiere una dep nueva significativa?**
   (más allá de bump de versión).
   - Sí → reconsiderar. ¿Hay una herramienta especializada
     mejor?
   - No → entra en scope, modificá.

3. **¿El cambio hace que la herramienta deje de ser un CLI
   batch?**
   - Sí → no entra. Esta herramienta es batch por diseño.
     Si querés interactivo, otra herramienta.
   - No → entra en scope.

## Ejemplos concretos

| Pedido del usuario | ¿Modificar esta herramienta? | Por qué |
|---|---|---|
| "Quiero que el log incluya el SHA del MD" | Sí | Es un cambio interno, no toca el contrato. |
| "Quiero subir también a S3 además de Drive" | No | Es una integración nueva significativa. Hacé un plugin o una herramienta de orquestación. |
| "Quiero generar también DOCX" | No (o sí, según cómo) | Si es "además de PDF, también DOCX" → modificá el renderer para soportar ambos formatos. Si es "reemplazar PDF por DOCX" → no entra, herramienta nueva. |
| "Quiero servir los PDFs en una URL pública" | No | Requiere un web server, no un CLI. |
| "Quiero que el script también baje los PDFs de Drive" | No | Esto es unidireccional por diseño. Otra herramienta para sync bidireccional. |
| "Quiero cambiar el motor a wkhtmltopdf" | Sí | Es una decisión interna, no toca el contrato. |
| "Quiero agregar un flag `--exclude`" | Sí | Es un flag nuevo compatible hacia atrás. |
| "Quiero que el config soporte TOML" | No (o sí, según) | Si es "además de YAML, también TOML" → modificá el loader. Si es "reemplazar YAML por TOML" → breaking, mejor herramienta nueva. |
| "Quiero ejecutar esto en CI" | Parcial | El script en sí es ejecutable en CI. Pero la SKILL.md y el `--init` no. Si necesitás un workflow de GitHub Actions, eso es un cambio aparte. |
| "Quiero multi-cuenta (Google Workspace)" | Sí (cuenta por `auth.dir`) | Ya soportado vía env var y config. Sin cambios al script. |
| "Quiero multi-cuenta con un solo config" | No | El config es por cuenta. Para multi-cuenta, múltiples configs. |
| "Quiero usar Drive API v4" | No (por ahora) | No existe Drive API v4. Cuando exista, evaluar. |

## Si no entra en scope: qué hacer

1. **Hacé una herramienta nueva.** Mismo directorio de
   diseño, mismo estilo de doc, mismo enfoque. Pero con
   scope propio.
2. **Reusá los módulos** de esta herramienta. Por ejemplo,
   `renderer.py` se puede reusar en una herramienta que
   también genere PDFs. Está pensado para eso (es una
   interfaz pública, no un detalle interno).
3. **Reusá la SKILL.md** como template. Cambiá el frontmatter,
   el nombre, y el contenido. No copies a ciegas.
4. **Documentá en este directorio** que la herramienta nueva
   existe. Un link en `README.md` y un `decisiones-de-diseno.md`
   que diga "esta herramienta se complementa con X".

## Si entra en scope pero es grande (>400 líneas)

Chained PR. Ver la skill `estrategia-git` (en español) o
`chained-pr` (en inglés) para el approach.

Reglas básicas:
- **Una cosa por PR.** Si tu cambio toca la API, la CLI y
  la skill, son tres PRs.
- **Cada PR mergeable solo.** No PRs que dependen de otros
  no mergeados.
- **Tests con cada PR.** No "agrego tests después".

## Si entra en scope pero rompe el contrato

Es una decisión de versionado. Si el cambio es:
- **Patch (0.1.x):** bug fix, sin breaking changes.
- **Minor (0.x.0):** nueva funcionalidad compatible hacia
  atrás.
- **Major (x.0.0):** breaking change.

Para un breaking change, además de bumpear:
1. Documentar el cambio en `decisiones-de-diseno.md` (qué
   cambió y por qué).
2. Actualizar `codigos-de-error.md` si cambió algún código.
3. Actualizar la SKILL.md (es el contrato con el usuario).
4. Considerar un periodo de deprecation (soportar el
   contrato viejo por una versión antes de romperlo).
