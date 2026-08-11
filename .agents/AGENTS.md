# Reglas del Proyecto (Workspace Rules)

## Detección de Ciudades en Sabre
Al extraer origen/destino de textos GDS Sabre (ej. `VALENCIA VE,\nVENEZUELA`), las expresiones regulares deben limitarse a coincidir en la misma línea utilizando caracteres horizontales (`[\t ]`) en lugar de `\s` (que incluye saltos de línea). Esto evita que el motor regex de Python desplace el inicio de la búsqueda hacia la derecha por comportamiento no codicioso.

## Condición de Carrera en Inicialización de Catálogo
En el arranque del backend de la aplicación Django, si falla la carga inicial de `airports_master.json`, `CatalogNormalizationService._airports_master` no debe quedarse guardado como un diccionario vacío permanente (`{}`). La validación de inicialización debe comprobar `if not cls._airports_master:` para permitir reintentos automáticos en llamadas subsecuentes.

## Regla de Acceso a Base de Datos (Django ORM Estricto)
Toda operación de entrada, salida, modificación o eliminación de datos en la base de datos DEBE realizarse utilizando exclusivamente el **Django ORM** (`objects.create()`, `objects.filter()`, `bulk_create()`, `transaction.atomic()`). Está prohibido construir consultas mediante cadenas SQL dinámicas o ejecutar SQL directo para manipular entidades de negocio.

## Regla de Parseo Obligatorio por IA en Ingesta de Correos (Mailbot)
Todo boleto o archivo recibido electrónicamente a través del Mailbot (correos HTML o adjuntos) DEBE encolar su procesamiento con `bypass_cache=True` e `ignore_manual=True` para invocar directamente el motor neuronal `UniversalAIParser` (Gemini Pro/Flash), garantizando la máxima precisión sin depender de patrones Regex legados ambiguos.

## Regla de Notificación Automática Multicanal para Boletos
Al completarse la generación del PDF de un boleto (sea importado por correo, manualmente desde la web o re-extraído), el sistema DEBE despachar de forma obligatoria y automática:
1. El documento PDF con su ficha técnica al canal/bot de **Telegram** de la agencia (`send_telegram_document_task`).
2. El boleto PDF por **WhatsApp** (`WhatsAppService.send_document`) si el cliente asociado posee un número telefónico principal registrado.
