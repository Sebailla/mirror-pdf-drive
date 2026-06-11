# Referencias — Dependencias

> **Lista completa de dependencias de la herramienta, con su
> versión mínima, su licencia, y por qué se eligió cada una.
> Si vas a agregar o cambiar una dep, revisá esta lista
> primero.**

## Dependencias del sistema

| Dependencia | Versión mínima | Licencia | Por qué |
|---|---|---|---|
| Python | 3.11+ | PSF | Type hints modernos, `match` statements, performance. |
| `pandoc` | 3.0+ | GPL-2.0 | Estándar de conversión de Markdown. |
| `pango` | 1.50+ | LGPL-2.1 | Rendering de texto en weasyprint. |
| `cairo` | 1.16+ | LGPL-2.1 / MPL-1.1 | Gráficos 2D en weasyprint. |
| `gdk-pixbuf` | 2.0+ | LGPL-2.1 | Carga de imágenes en weasyprint. |
| `libffi` | 3.0+ | MIT | Foreign function interface (transitiva). |

**Por qué no reemplazar Python 3.11 por algo más viejo:**
los type hints con `Self`, `ParamSpec` y el match statement
mejoran la legibilidad del código. Bajar el mínimo a 3.9 o
3.10 es factible pero requiere trabajo extra sin beneficio
claro.

## Dependencias Python

Definidas en `pyproject.toml` del script:

| Paquete | Versión mínima | Licencia | Por qué |
|---|---|---|---|
| `pypandoc` | 1.11+ | MIT | Wrapper de pandoc para Python. Valida que pandoc esté instalado. |
| `weasyprint` | 62.0+ | BSD-3-Clause | Motor de PDF HTML+CSS. |
| `google-api-python-client` | 2.100+ | Apache-2.0 | Cliente oficial de las APIs de Google. |
| `google-auth` | 2.23+ | Apache-2.0 | Manejo de credenciales OAuth. |
| `google-auth-oauthlib` | 1.1+ | Apache-2.0 | Flow de OAuth para apps instaladas. |
| `pydantic` | 2.5+ | MIT | Validación de config y modelos de datos. |
| `pyyaml` | 6.0+ | MIT | Parser de YAML. |

### Por qué cada una

**`pypandoc` y no `subprocess.run(['pandoc', ...])`:**
- `pypandoc` valida que pandoc esté instalado y lanza
  excepción clara si no.
- Maneja paths con espacios correctamente.
- API más limpia que construir command line strings.

**`weasyprint` directo (vía pypandoc) y no como dep Python:**
- pypandoc llama a weasyprint como binario externo, no
  como módulo Python.
- Esto evita problemas de instalación de weasyprint (que
  tiene bindings C complicados).
- Si weasyprint no está, pandoc falla con mensaje claro.

**`google-api-python-client` y no `httpx` + requests manuales:**
- La API de Drive es compleja. El cliente oficial maneja
  auth, retries, multipart uploads, etc.
- Usar HTTP directo es factible pero reinventa la rueda.

**`pydantic` v2 y no dataclasses:**
- Validación automática con mensajes claros.
- Serialización/deserialización para el config.
- En v2, performance comparable a dataclasses.

**`pyyaml` y no `tomllib`:**
- YAML soporta comentarios (clave para config de usuario).
- TOML está bien para `pyproject.toml`, no para config de
  aplicación.

## Dependencias de desarrollo

Solo si vas a desarrollar la herramienta, no para usarla:

| Paquete | Versión | Para qué |
|---|---|---|
| `pytest` | 8.0+ | Tests unitarios. |
| `pytest-mock` | 3.12+ | Mocks para tests. |
| `mypy` | 1.8+ | Type checking estático. |
| `ruff` | 0.3+ | Linter y formateador. |
| `pre-commit` | 3.6+ | Hooks de git. |

## Dependencias externas (no técnicas)

| Dependencia | Tipo | Para qué |
|---|---|---|
| Google Cloud Platform | Servicio | Drive API, OAuth credentials. |
| Google Drive | Servicio | Destino de los PDFs subidos. |
| Homebrew (macOS) o apt (Linux) | Sistema | Instalar pandoc, pango, cairo. |

## Cambios de versión

Cuando bumpees una dep, hacelo así:

1. **Lee el changelog** de la nueva versión.
2. **Buscá breaking changes** que afecten la herramienta.
3. **Actualizá el mínimo** en `pyproject.toml`.
4. **Corré los tests** para verificar.
5. **Actualizá esta tabla** en el mismo commit.
6. **Si es breaking para el usuario** (ej. cambió la API de
   Drive), actualizá la doc de troubleshooting.

## No agregar

| Lo que NO hay que agregar | Por qué |
|---|---|
| `requests` | El cliente de Google ya hace HTTP. Agregar `requests` es dep de más. |
| `click` o `typer` | `argparse` de stdlib es suficiente para 10 flags. |
| `rich` o `colorama` | El logging de stdlib es suficiente. Si querés colores, agregalo al logging formatter, no como dep. |
| `python-dotenv` | El config es YAML, no `.env`. Mezclar es confuso. |
| `pytest-cov` para reporte | Si lo necesitás, agregalo como dep de dev, no de runtime. |
| ORM o DB | La herramienta no tiene estado propio. |
