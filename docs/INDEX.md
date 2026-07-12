# Índice de Documentación — TravelHub

**Última actualización:** 12 de Julio de 2026

Bienvenido a la documentación oficial de TravelHub. Este índice organiza todos los documentos activos del proyecto.

> **¿Buscas el manual de usuario?** Accede a la versión pública desde la aplicación en `/manual/` o lee la versión completa en [manual_del_usuario.md](manual_del_usuario.md).

---

## 1. Introducción y Visión General

Documentos para entender qué es TravelHub y cómo está construido.

- **[manual_del_usuario.md](manual_del_usuario.md)** — Manual completo para agencias de viaje. Explica paso a paso cómo usar el sistema, sin tecnicismos.
- **[business_model.md](business_model.md)** — Modelo de negocio SaaS: cómo funciona la plataforma, quiénes son los clientes y cómo se generan ingresos.
- **[architecture_map.md](architecture_map.md)** — Mapa visual de la arquitectura con diagramas. Ideal para entender todos los componentes del sistema de un vistazo.
- **[reporte_arquitectura_2026.md](reporte_arquitectura_2026.md)** — Documento maestro de arquitectura. La fuente de verdad detallada sobre el estado actual del ecosistema.
- **[estructura_carpetas.md](estructura_carpetas.md)** — Mapa detallado de todos los módulos y carpetas del proyecto.
- **[multi_tenancy.md](multi_tenancy.md)** — Cómo funciona la arquitectura multi-tenant (múltiples agencias en una misma instalación).

---

## 2. Guías de Desarrollo

Para programadores y personal técnico que trabaja con el código.

- **[desarrollo.md](desarrollo.md)** — Guía de desarrollo: tecnologías, estructura del proyecto, estándares de código, pruebas y flujo de trabajo.
- **[organizacion_proyecto.md](organizacion_proyecto.md)** — Organización general del código y las aplicaciones Django.
- **[cron_setup.md](cron_setup.md)** — Configuración de tareas programadas (Celery Beat).
- **[backend/](backend/)** — Documentación técnica del backend (auditoría, contabilidad, Redis).

---

## 3. APIs e Integraciones

Documentación de las interfaces de programación y componentes clave.

- **[data_dictionary.md](data_dictionary.md)** — Diccionario de datos de la base de datos.
- **[api_automation.md](api/automation.md)** — Automatizaciones y webhooks.
- **[translator_api.md](translator_api.md)** — Motor de traducción de itinerarios (GDS a JSON/HTML).
- **[voucher_system.md](voucher_system.md)** — Sistema de generación de vouchers.
- **[api/](api/)** — Documentación detallada de los endpoints REST.

---

## 4. Despliegue, Operaciones y Seguridad

Guías para administradores del sistema y encargados de infraestructura.

- **[despliegue.md](despliegue.md)** — Guía completa de despliegue: desde desarrollo local hasta producción con Cloudflare Tunnel.
- **[seguridad.md](seguridad.md)** — Medidas de seguridad implementadas, riesgos identificados y buenas prácticas.
- **[operations.md](operations.md)** — Guía de operaciones del ERP.
- **[deployment/](deployment/)** — Documentación adicional de despliegue (configuración de tareas, BCV, cierre mensual).

---

## 5. Procesamiento de Itinerarios (GDS)

Documentación sobre el negocio principal: procesamiento de reservas de aerolíneas.

- **[parsing_rules.md](parsing_rules.md)** — Las reglas de estandarización para KIU, Sabre y Amadeus.
- **[guia_amadeus.md](guia_amadeus.md)** — Procesamiento específico de Amadeus.
- **[manual_funcional.md](manual_funcional.md)** — Guía funcional para gerentes y contadores.
- **[manual_sistema.md](manual_sistema.md)** — Guía técnica del sistema.
- **[wiki/GDS/](wiki/GDS/)** — Documentación detallada de los parsers GDS (Amadeus, KIU, Sabre).

---

## 6. Demostraciones

- **[guia_demo_en_vivo.md](guia_demo_en_vivo.md)** — Guía paso a paso para realizar demostraciones comerciales a agencias potenciales.

---

### Documentos archivados

Los documentos obsoletos, duplicados o que documentaban problemas ya resueltos se han movido a [`_archive/`](_archive/) para mantener la documentación actual limpia y enfocada.
