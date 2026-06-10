# Referencias — Decisiones de Diseño

> **El 'por qué' detrás de cada decisión. Si vas a cambiar algo
> de la herramienta, empezá por acá: si tu cambio contradice
> una decisión documentada, probablemente hay una razón que
> no estás viendo.**

## D-001: Código global, configuración local

**Decisión:** el script Python vive en `~/.local/share/mirror-pdf-drive/`
(global), pero el archivo de config vive en cada proyecto
(`mirror-pdf-drive.config.yaml` en la raíz).

**Por qué:**
- Un solo binario para todos los proyectos: los bugs se
  arreglan una vez, no N veces.
- Cada proyecto puede tener convenciones distintas (tamaño
  de página, márgenes, exclusiones) sin duplicar lógica.
- El setup de OAuth (client_secret + token) es por usuario
  de la máquina, no por proyecto. Global es lo correcto.

**Cuándo revertir:** si en el futuro la herramienta crece
tanto que necesita ser un paquete distribuible (con
`setup.py` o `pyproject.toml` público), se mueve a un repo
propio y se distribuye vía `pipx`. Mientras tanto, clone
manual del repo está bien.

## D-002: pandoc + weasyprint como motor de renderizado

**Decisión:** usar `pandoc` con `--pdf-engine=weasyprint` para
la conversión MD → PDF.

**Por qué:**
- pandoc es el estándar de facto para conversión de
  Markdown. Maneja todas las variantes (CommonMark, GFM,
  Pandoc Markdown).
- weasyprint da control total sobre tipografía y layout
  via CSS estándar.
- Ambos son livianos comparados con alternativas (Chromium
  headless).

**Alternativas consideradas:**
- `wkhtmltopdf`: usa QtWebKit viejo, dependencias pesadas,
  desarrollo estancado.
- `puppeteer`/`playwright`: traen Chromium completo, overkill
  para PDFs de doc.
- `mkdocs-with-pdf`: requiere generar sitio web primero,
  más complejo.
- Subir MD a Drive y exportar como PDF desde Drive: pierde
  control sobre tipografía.

**Cuándo revertir:** si el 80% de la doc se vuelve HTML
puro (no Markdown) y se quiere un sitio web, considerar
`mkdocs` o `docusaurus`. Si la doc necesita interactividad
(formularios, scripts), considerar un formato distinto
(ej. HTML autocontenido con un visor interactivo).

## D-003: OAuth con scope `drive.file`

**Decisión:** la herramienta pide solo el scope
`https://www.googleapis.com/auth/drive.file`, no `drive`
completo.

**Por qué:**
- `drive.file` solo permite acceder a archivos que la
  herramienta **creó**. No puede leer tus otros Docs, no
  puede borrar archivos ajenos.
- Si el `token.json` se filtra, el atacante solo ve y
  manipula los PDFs subidos por la herramienta. Tus otros
  archivos están a salvo.
- Es el scope mínimo para que la herramienta funcione
  (necesita subir y, opcionalmente, sobrescribir sus
  propios archivos).

**Cuándo revertir:** nunca, salvo que la herramienta
necesite leer archivos de Drive que no creó (ej. listar
todos los PDFs en una carpeta compartida). En ese caso,
justificar explícitamente y documentar el riesgo.

## D-004: Idempotencia por `mtime`

**Decisión:** el script skipea un MD si el PDF destino es
más nuevo que el MD fuente.

**Por qué:**
- Corridas frecuentes no gastan quota de Drive.
- Es intuitivo: si no tocaste el MD, no re-renderizás.
- No requiere estado adicional (cache de hashes, etc.).

**Limitaciones:**
- Si el CSS o la plantilla cambiaron, no se detecta. El
  MD no cambió, pero el output sí debería cambiar.
- Si el `mtime` del MD se preserva mal (ej. un `git
  checkout` restaura el `mtime` al original), puede dar
  skips incorrectos.

**Cuándo revertir:** si la herramienta se vuelve lenta
porque se cambia el CSS/plantilla seguido, considerar
caching por hash del MD (más robusto, más complejo).

## D-005: Errores con códigos estables

**Decisión:** cada subclase de `AppError` tiene un campo
`code` que es un string estable entre versiones.

**Por qué:**
- La skill de Pi y el usuario pueden referirse a errores
  por código, no por mensaje (que puede cambiar).
- Permite hacer tablas de troubleshooting indexadas por
  código.
- El exit code (numérico) es para scripts y shells; el
  código (string) es para humanos y logs.

**Cuándo revertir:** nunca. Los códigos son contrato.

## D-006: Script runtime-agnostic

**Decisión:** el script no asume que está siendo invocado
por Pi. No lee variables de Pi, no tiene código que solo
funciona dentro de un slash command.

**Por qué:**
- Reusable desde OpenCode, cron, bash script, otros
  agentes.
- Testeable de forma aislada.
- Si Pi cambia, el script no se rompe.

**Implicación:** la SKILL.md de Pi es un wrapper delgado
que delega al binario. La lógica vive en el binario.

## D-007: Documentación en español

**Decisión:** la doc de este directorio está en español. Los
identificadores de código, los mensajes de log y los exit
codes van en inglés.

**Por qué:**
- El usuario (vos) escribe en español. La doc refleja eso.
- El código en inglés es convención universal de Python;
  rompe la búsqueda en GitHub, en docs oficiales, en
  StackOverflow.
- Los mensajes al usuario final (en el stdout de la skill)
  van en español para ser amigables.

**Regla clara:**
- Doc: español.
- Código: inglés.
- Logs internos: inglés.
- Mensajes al usuario: español.

**Cuándo revertir:** nunca, salvo que el equipo se vuelva
angloparlante.

## D-008: Config por proyecto, no global

**Decisión:** el archivo `mirror-pdf-drive.config.yaml`
vive en la raíz de cada proyecto, no en
`~/.config/mirror-pdf-drive/config.yaml`.

**Por qué:**
- El config puede commitearse al repo (especifica la
  convención del proyecto, no las preferencias del
  usuario).
- Dos proyectos con convenciones distintas no se pisan.
- Si clonás el repo en otra máquina, el config ya está
  ahí; solo falta el `client_secret.json` y el `token.json`
  (que sí son globales y por usuario).

**Excepción:** el `auth.dir` puede apuntar a un lugar
distinto del default XDG. Esto es por si compartís máquina
con otro usuario o querés mantener credenciales de Drive
separadas.

## D-009: Tool como excepción documentada en §13.6

**Decisión:** esta herramienta se documenta como una
excepción a la atomicidad inglés-español del mismo commit
(§13.3 del AGENTS.md raíz), con su propia cláusula §13.6.

**Por qué:**
- La atomicidad dice: "todo cambio a un Markdown en
  inglés viene con su espejo español en el mismo commit".
- La herramienta PDF→Drive **lee** el español, lo convierte
  a PDF, y lo sube a Drive. No escribe al español, no
  requiere un commit coordinated con el inglés.
- Drive es un servicio externo, no parte del repo. La
  atomicidad no aplica.

**Implicación:** si modificás la herramienta, tenés que
mantener §13.6 actualizado. Si la herramienta crece y
empieza a generar archivos en el repo (ej. un índice de
PDFs subidos), reconsiderar la excepción.

**Cuándo revertir:** si en el futuro el PR a Drive pasa
a ser parte del CI (no manual), la excepción sigue
valiendo (es lo mismo que §13.5 para OneNote). Si
empieza a escribir al repo, hay que repensar.

## D-010: SKILL.md en Pi, no en OpenCode

**Decisión:** la SKILL.md existe para Pi, no para OpenCode.

**Por qué:**
- El proyecto del usuario (gastos-personales) usa Pi como
  runtime principal.
- Las convenciones de SKILL.md son distintas entre Pi
  (frontmatter, slash commands) y OpenCode (formato
  distinto, otros triggers).
- Escribirla "neutral" la haría funcionar subóptimamente
  en ambos.

**Implicación:** si en el futuro el proyecto migra a
OpenCode, hay que reescribir la skill. La lógica del
binario Python sigue siendo la misma.

**Cuándo revertir:** si el usuario decide usar OpenCode
como runtime principal, o si quiere soporte en ambos
simultáneamente (lo que duplica el mantenimiento).
