---
title: Agent Contract — mirror-pdf-drive
author: Sebastián Illa
version: 0.1.0
status: draft
---

# Agent Contract — `mirror-pdf-drive`

> Contrato del agente para este repositorio. Este archivo es
> el equivalente al `AGENTS.md` raíz de un proyecto de
> producto, pero adaptado a un repositorio de **herramienta**.

## Identidad

Este repositorio contiene la **herramienta CLI
`mirror-pdf-drive`**: un conversor de Markdown a PDF que
sube el resultado a Google Drive. La herramienta es
**runtime-agnostic** y vive en `~/.local/share/mirror-pdf-drive/`
(este repo es la fuente, no el destino de la instalación).

## Reglas no negociables

| Regla | Descripción |
|---|---|
| Idioma del código | Inglés (identificadores, mensajes de log, exit codes). |
| Idioma de la doc | Español (README, docs/, AGENTS.md). |
| Idioma de los commits | Español (Conventional Commits, imperativo presente). |
| Atribución de autor | Toda la doc tiene `Author: Sebastián Illa` en el frontmatter. Sin excepciones. Sin "AI" ni "Assistant" ni "co-authored-by" en commits. |
| Sin trailers de IA | Ningún commit puede tener `Co-authored-by: AI` o similar. |
| Conventional Commits | Formato `<tipo>(<alcance>): <descripción>`. Tipos: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert. |
| Sin `force` a main | `main` es inmutable. Solo recibe PRs desde `develop`. |
| Tests antes de merge | Toda PR tiene tests pasando. Cobertura ≥ 80% por archivo. |
| Pre-commit gate | `gga run` o equivalente antes de cada commit. |
| Doc junto al código | Si tocás código, la doc va en el mismo commit. |

## Estructura del repo

```
.
├── AGENTS.md             # este archivo
├── README.md             # entrada principal
├── .gitignore
├── docs/                 # documentación de diseño (en español)
│   ├── README.md
│   ├── arquitectura/
│   ├── script/
│   ├── configuracion/
│   ├── skill/
│   ├── operacion/
│   └── referencias/
├── src/                  # código del script (a crear)
│   └── mirror_pdf_drive/
│       ├── __init__.py
│       ├── mirror.py
│       ├── config.py
│       ├── renderer.py
│       ├── drive_client.py
│       ├── auth.py
│       └── exceptions.py
├── tests/                # tests unitarios (a crear)
│   ├── test_mirror.py
│   ├── test_config.py
│   ├── test_renderer.py
│   ├── test_drive_client.py
│   └── test_auth.py
├── pyproject.toml        # a crear
└── .gga                  # config de GGA (a crear si se usa)
```

## §13 — Documentación bilingüe

Este repositorio **no** tiene la convención bilingüe
inglés-español. La doc está **solo en español** por
decisión del usuario (ver `docs/referencias/decisiones-de-diseno.md`
sección D-007).

La excepción §13.6 que se documenta en el `AGENTS.md` del
proyecto **`gastos-personales`** (el proyecto donde se usa
esta herramienta) sí aplica: la herramienta es un consumer
de `Documents-es/` que produce PDFs en Drive, no escribe al
espejo español.

## Git workflow

```
main (producción, inmutable)
  ↑
develop (integración) ← PRs desde feat/*, fix/*, etc.
  ↑
feat/mirror-pdf-drive (worktree)
```

| Branch | Regla |
|---|---|
| `main` | Inmutable. Solo recibe PRs desde `develop`. |
| `develop` | Integración. Todas las PRs mergeadas acá. |
| `feat/*`, `fix/*`, `docs/*`, etc. | Branches de tarea, una por concern. |

**Estrategia de merge**: rebase-merge (exclusivo, squash y
merge-commit están deshabilitados en la config del repo).
Cada PR se mergea con `git rebase` y fast-forward, preservando
los SHAs originales de los commits. Resultado: develop queda
como descendiente lineal de main después de cada release, sin
divergencia estructural. Los PRs viejos que se mergeaaron con
squash-merge siguen en la historia con sus SHAs originales;
después del primer PR nuevo con rebase-merge, la divergencia
estructural desaparece.

### Comandos rápidos

```bash
# Crear branch de tarea
git checkout develop && git pull
git checkout -b feat/<nombre-tarea>

# Antes de commit
gga run

# Commit (Conventional Commits en español, imperativo presente)
git add .
git commit -m "feat(script): agregar módulo de autenticación OAuth"

# Push y PR
git push -u origin feat/<nombre-tarea>
gh pr create --base develop
```

## Cómo correr los tests

```bash
# Setup
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Tests
pytest
pytest --cov=src/mirror_pdf_drive --cov-report=term-missing
```

## Cómo instalar localmente

```bash
pip install -e .
mirror-pdf-drive --version
```

## Próximos pasos

Ver `docs/referencias/changelog-diseno.md` para el
seguimiento de decisiones de diseño, y `docs/operacion/`
para cómo usar la herramienta una vez instalada.
