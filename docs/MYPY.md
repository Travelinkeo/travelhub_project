# Chequeo de tipos con **mypy**

Esta guía muestra cómo ejecutar el verificador de tipos estático **mypy** en el proyecto **TravelHub**.

## 1. Instalación de dependencias de desarrollo

```bash
# Desde la raíz del proyecto
pip install -r requirements/dev.txt
# Instala los *type‑stubs* necesarios (ejemplo con requests)
pip install types-requests
```

> **Nota:** `requirements/dev.txt` ya incluye `mypy` y `mypy-django-plugin`.

## 2. Ejecutar el análisis

```bash
# Analiza todo el código del proyecto
mypy .
```

El comando utiliza la configuración definida en `mypy.ini` (modo estricto y el plugin `django-stubs`).

## 3. Interpretar la salida

- Cada línea indica **archivo**, **línea**, **tipo de error** y una breve descripción.
- Los errores más comunes son:
  - `no-untyped-def`: funciones sin anotaciones de tipos.
  - `no-untyped-call`: llamadas a funciones no tipadas.
  - `misc`: atributos inexistentes en objetos (p.ej. `Settings.GCP_PROJECT_ID`).

## 4. Mitigar errores rápidamente

- Añade anotaciones de tipo a funciones críticas.
- Si una función externa no tiene stubs, instala el paquete correspondiente (`types-requests`, `types-pillow`, etc.) o usa `# type: ignore`.
- Para ignorar temporalmente avisos específicos, edita `mypy.ini`:
  ```ini
  [mypy]
  disallow_untyped_defs = False  # permite funciones sin anotaciones
  disallow_untyped_calls = False # permite llamadas a funciones no tipadas
  ```

## 5. Integración CI

El workflow de GitHub Actions ya ejecuta `mypy` en el job `type_check`. Si deseas que falle el pipeline cuando haya errores, elimina la opción `fail_ci_if_error: false` en `.github/workflows/ci.yml`.

---

Con estos pasos podrás mantener la calidad de tipos del código y detectar errores antes de que lleguen a producción.
