# Guía de Contribución para TravelHub

¡Gracias por tu interés en contribuir a TravelHub! Esta guía establece las pautas para asegurar un desarrollo coherente, de alta calidad y colaborativo.

## Tabla de Contenidos

1.  [Filosofía General](#filosofía-general)
2.  [Flujo de Ramas (Branching Workflow)](#flujo-de-ramas-branching-workflow)
3.  [Convención de Commits](#convención-de-commits)
4.  [Estilo de Código](#estilo-de-código)
5.  [Proceso de Pruebas y Cobertura](#proceso-de-pruebas-y-cobertura)
6.  [Proceso de Pull Request (PR)](#proceso-de-pull-request-pr)

---

### Filosofía General

- **Calidad por encima de todo:** El código nuevo debe ser legible, mantenible y estar cubierto por pruebas.
- **Mejora continua:** Buscamos mejorar la base de código de forma incremental. Cada contribución debe dejar el proyecto en un estado mejor que el anterior.
- **Respeto por las convenciones:** Adherirse a las convenciones establecidas es crucial para la mantenibilidad a largo plazo.

---

### Flujo de Ramas (Branching Workflow)

Utilizamos un flujo de trabajo simple basado en ramas temáticas que se fusionan en `master` (o `main`).

1.  **Sincroniza tu rama `master` local:**
    ```bash
    git checkout master
    git pull origin master
    ```

2.  **Crea una nueva rama** con un prefijo descriptivo. Usa `main` o `master` como base.
    - Para nuevas características: `feature/<nombre-corto-de-la-caracteristica>` (ej: `feature/parser-amadeus`)
    - Para corrección de errores: `fix/<nombre-corto-del-bug>` (ej: `fix/login-rate-limit`)
    - Para refactorización: `refactor/<area-a-refactorizar>` (ej: `refactor/move-models-to-services`)
    - Para documentación: `docs/<tema-documentado>` (ej: `docs/update-readme-auth`)

    ```bash
    git checkout -b feature/nueva-funcionalidad
    ```

3.  **Realiza tus cambios** en esta rama.

4.  **Envía tu rama** al repositorio remoto y abre un Pull Request.

---

### Convención de Commits

Para mantener un historial de cambios limpio y legible, seguimos la especificación de **Conventional Commits**. Cada mensaje de commit debe tener el siguiente formato:

```
<tipo>[ámbito opcional]: <descripción>

[cuerpo opcional]

[pie opcional]
```

- **Tipos comunes:**
  - `feat`: Una nueva característica para el usuario.
  - `fix`: Una corrección de un bug.
  - `refactor`: Un cambio en el código que no arregla un bug ni añade una característica.
  - `test`: Añadir pruebas faltantes o corregir pruebas existentes.
  - `docs`: Cambios en la documentación.
  - `style`: Cambios que no afectan el significado del código (espacios, formato, etc.).
  - `chore`: Cambios en el proceso de build, herramientas o tareas auxiliares.

- **Ejemplo:**
  ```
  feat(parser): Añade soporte inicial para boletos de Amadeus
  
  Se implementa la detección heurística y la extracción básica de los campos
  principales del GDS Amadeus. Aún no cubre todos los casos de itinerario.
  ```

---

### Estilo de Código

- **Python:** El proyecto utiliza **`ruff`** para el formateo y el linting. La configuración se encuentra en el archivo `.ruff.toml`.
  - Antes de hacer commit, asegúrate de que tu código cumple con las reglas ejecutando:
    ```bash
    ruff check .
    ruff format .
    ```
  - Se recomienda configurar un hook de pre-commit para automatizar esto.

- **JavaScript/TypeScript:** Se utiliza `prettier` y `eslint`, con la configuración en los archivos correspondientes del directorio `frontend/`.

---

### Proceso de Pruebas y Cobertura

- **Nuevas características deben incluir pruebas:** Cualquier nueva lógica de negocio, función de utilidad o endpoint de API debe ir acompañada de sus correspondientes pruebas unitarias o de integración.
- **Los arreglos de bugs deben incluir una prueba de regresión:** Si corriges un bug, primero escribe una prueba que falle debido al bug y luego arréglalo para que la prueba pase.

- **Cobertura de Código (Code Coverage):**
  - El proyecto tiene un objetivo de cobertura que se incrementa de forma escalonada.
  - **Plan actual:** `71%` -> `75%` -> `80%` -> `85%`.
  - Tu contribución no debe disminuir el umbral de cobertura actual. La CI fallará si la cobertura total baja.
  - Para verificar la cobertura localmente, ejecuta:
    ```bash
    pytest --cov
    ```

---

### Proceso de Pull Request (PR)

1.  **Asegúrate de que tu rama está actualizada** con `master` para evitar conflictos.
2.  **Abre un Pull Request (PR)** dirigido a la rama `master`.
3.  **Escribe una descripción clara** en el PR, explicando *qué* cambios has hecho y *por qué*.
4.  **Verifica que todas las comprobaciones de CI pasen** con éxito (linting, tests, cobertura).
5.  **Espera la revisión de al menos un miembro del equipo.** Atiende los comentarios y sugerencias que puedan surgir.
6.  Una vez aprobado y con la CI en verde, el PR será fusionado.
