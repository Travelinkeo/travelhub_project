# 📚 Índice de Documentación - TravelHub

**Última actualización**: 2 de Mayo de 2026

Bienvenido a la documentación oficial de TravelHub. Tras una extensa revisión y limpieza, este índice centraliza los documentos técnicos y manuales operativos que se encuentran **actualmente activos**. Todos los reportes obsoletos, pruebas y scripts legacy han sido aislados para su futura eliminación.

---

## 🏛️ 1. Arquitectura y Visión General
Documentos centrales que describen la estructura y el propósito del sistema.

- **[REPORTE_ARQUITECTURA_2026.md](REPORTE_ARQUITECTURA_2026.md)** - 🌟 Documento Maestro de Arquitectura (La fuente de la verdad para el estado actual del ecosistema).
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Resumen técnico de la arquitectura.
- **[ESTRUCTURA_CARPETAS.md](ESTRUCTURA_CARPETAS.md)** - Mapa detallado de todos los módulos del proyecto.
- **[SYSTEM_SNAPSHOT.md](SYSTEM_SNAPSHOT.md)** - Resumen de la infraestructura.
- **[BUSINESS_MODEL.md](BUSINESS_MODEL.md)** - Modelo de negocio SaaS.

## ⚙️ 2. Guías de Desarrollo e Infraestructura
Para desarrolladores y encargados de DevOps.

- **[README.md](README.md)** - Guía de entrada principal al repositorio.
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Flujos de trabajo y estándares.
- **[DOCKER_README.md](DOCKER_README.md)** - Todo lo necesario para levantar el proyecto con contenedores.
- **[ORGANIZACION_PROYECTO.md](ORGANIZACION_PROYECTO.md)** - Guía de organización general de código.
- **[CRON_SETUP.md](CRON_SETUP.md)** - Configuración de tareas programadas (Celery Beat).
- **[MULTI_TENANCY.md](MULTI_TENANCY.md)** - Cómo funciona la arquitectura SaaS para múltiples agencias.

## 🔌 3. APIs y Componentes Clave
Documentación de interfaces y microservicios internos.

- **[DATA_DICTIONARY.md](DATA_DICTIONARY.md)** - Diccionario de datos de la base de datos central.
- **[API_AUTOMATION.md](API_AUTOMATION.md)** - Automatizaciones y Webhooks.
- **[TRANSLATOR_API.md](TRANSLATOR_API.md)** - Documentación del motor de traducción de itinerarios (GDS a JSON/HTML).

## ✈️ 4. Operaciones, Uso y Parsers (GDS)
Guías sobre el negocio principal y manuales de usuario.

- **[MANUAL_DEL_USUARIO.md](MANUAL_DEL_USUARIO.md)** - 📖 **El Gran Libro de Consultas.** Manual paso a paso, súper amigable y sin tecnicismos, ideal para entrenar a cualquier persona que vaya a usar el sistema.
- **[MANUAL_FUNCIONAL.md](MANUAL_FUNCIONAL.md)** - 👥 Guía para gerentes y contadores. Describe el "por qué" funcional de la plataforma.
- **[OPERATIONS.md](OPERATIONS.md)** - Guía de operaciones del ERP y despliegue.
- **[PARSING_RULES.md](PARSING_RULES.md)** - 📜 Los "10 Mandamientos" del parseo. Reglas técnicas de estandarización para KIU, Sabre, Amadeus.
- **[GUIA_AMADEUS.md](GUIA_AMADEUS.md)** - Documentación sobre el procesamiento específico de Amadeus.
- *(Nota: Para documentación extensa sobre parsers (Sabre, KIU, etc.) consultar el REPORTE_ARQUITECTURA_2026.md)*

## 🎥 5. Presentación y Demostraciones
- **[GUIA_DEMO_EN_VIVO.md](GUIA_DEMO_EN_VIVO.md)** - Guía paso a paso para realizar demostraciones comerciales a potenciales agencias cliente.

---

### 🗂️ Navegación por Subdirectorios
Si buscas detalles muy específicos, puedes explorar los subdirectorios funcionales:
- `api/`: Documentación de los endpoints REST.
- `backend/` y `frontend/`: Detalles muy específicos del código legado o integraciones.
- `contabilidad/` y `facturacion/`: Especificaciones del módulo contable VEN-NIF.
- `saas/`: Detalles del modelo de negocio, integraciones de pago (Stripe) y métricas.
- `deployment/`: Configuraciones de nube (Render, Railway).

*(Nota: Los archivos que antes se encontraban aquí y que hacían referencia a bugs ya solucionados o reportes antiguos, han sido movidos a la cuarentena `_cuarentena_para_borrar/docs_desfasados/`)*
