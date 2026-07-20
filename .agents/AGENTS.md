# Reglas del Proyecto (Workspace Rules)

## Detección de Ciudades en Sabre
Al extraer origen/destino de textos GDS Sabre (ej. `VALENCIA VE,\nVENEZUELA`), las expresiones regulares deben limitarse a coincidir en la misma línea utilizando caracteres horizontales (`[\t ]`) en lugar de `\s` (que incluye saltos de línea). Esto evita que el motor regex de Python desplace el inicio de la búsqueda hacia la derecha por comportamiento no codicioso.

## Condición de Carrera en Inicialización de Catálogo
En el arranque del backend de la aplicación Django, si falla la carga inicial de `airports_master.json`, `CatalogNormalizationService._airports_master` no debe quedarse guardado como un diccionario vacío permanente (`{}`). La validación de inicialización debe comprobar `if not cls._airports_master:` para permitir reintentos automáticos en llamadas subsecuentes.

## Regla de Acceso a Base de Datos (Django ORM Estricto)
Toda operación de entrada, salida, modificación o eliminación de datos en la base de datos DEBE realizarse utilizando exclusivamente el **Django ORM** (`objects.create()`, `objects.filter()`, `bulk_create()`, `transaction.atomic()`). Está prohibido construir consultas mediante cadenas SQL dinámicas o ejecutar SQL directo para manipular entidades de negocio.
