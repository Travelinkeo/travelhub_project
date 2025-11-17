# ÍNDICE DE DOCUMENTACIÓN - TRAVELHUB

**Fecha**: 25 de Enero de 2025  
**Versión**: 1.0

---

## 📋 DOCUMENTACIÓN PRINCIPAL

### Informes y Guías Generales
- **[INFORME_COMPLETO_PROYECTO.md](INFORME_COMPLETO_PROYECTO.md)** - Informe completo del proyecto (ESTE DOCUMENTO ES EL MÁS IMPORTANTE)
- **[ORGANIZACION_PROYECTO.md](../ORGANIZACION_PROYECTO.md)** - Guía de organización del proyecto
- **[INICIO_RAPIDO.txt](../INICIO_RAPIDO.txt)** - Comandos rápidos para iniciar
- **[README.md](../README.md)** - README principal

---

## 🏗️ DOCUMENTACIÓN POR CATEGORÍA

### 1. Sistema SaaS (docs/saas/)
- `stripe_setup_guide.md` - Configuración de Stripe
- `saas_implementation.md` - Implementación SaaS multi-tenant
- `planes_suscripcion.md` - Planes y precios
- `billing_api.md` - API de facturación SaaS

### 2. Parsers de Boletos (docs/parsers/)
- `parsers_estado_octubre_2025.md` - Estado actual de parsers
- `parsers_boletos.md` - Documentación de parsers
- `kiu_parser.md` - Parser KIU
- `sabre_parser.md` - Parser SABRE
- `amadeus_parser.md` - Parser AMADEUS
- `copa_sprk_parser.md` - Parser Copa SPRK
- `wingo_parser.md` - Parser Wingo
- `tk_connect_parser.md` - Parser TK Connect

### 3. Facturación Venezolana (docs/facturacion/)
- `ajustes_facturacion_gemini.md` - Ajustes según investigación Gemini
- `billing_api_completa.md` - API de facturación completa
- `consolidacion_facturas_completada.md` - Consolidación de modelos
- `doble_facturacion.md` - Sistema de doble facturación
- `libro_ventas_implementado.md` - Libro de ventas IVA
- `retenciones_islr_implementado.md` - Retenciones ISLR

### 4. Contabilidad VEN-NIF (docs/contabilidad/)
- `contabilidad_venezuela_ven_nif.md` - Sistema contable completo
- `provision_inatur.md` - Provisión INATUR 1%
- `diferencial_cambiario.md` - Diferencial cambiario
- `cierre_mensual.md` - Cierre contable mensual

### 5. Deployment (docs/deployment/)
- `deployment_production.md` - Deployment a producción
- `deployment_options.md` - Opciones de deployment
- `railway_setup.md` - Configuración Railway
- `render_setup.md` - Configuración Render

### 6. APIs (docs/api/)
- `frontend_api_endpoints.md` - Endpoints para frontend
- `authentication_jwt.md` - Autenticación JWT
- `api_reference.md` - Referencia completa de APIs

### 7. Testing (docs/testing/)
- `testing_guide.md` - Guía de testing
- `coverage_report.md` - Reporte de cobertura
- `test_examples.md` - Ejemplos de tests

---

## 📚 DOCUMENTACIÓN HISTÓRICA (docs_archive/)

### Índice Completo
Ver **[docs_archive/INDEX.md](../docs_archive/INDEX.md)** para el índice completo de 39 documentos históricos.

### Categorías Principales
1. **Contabilidad** (8 documentos)
2. **Parsers** (6 documentos)
3. **Notificaciones** (4 documentos)
4. **Deployment** (5 documentos)
5. **Facturación** (7 documentos)
6. **Organización** (4 documentos)
7. **Otros** (5 documentos)

---

## 🔧 SCRIPTS Y HERRAMIENTAS (batch_scripts/)

### Scripts de Inicio
- `start_completo.bat` - Iniciar backend + frontend
- `start_backend.bat` - Solo backend
- `iniciar_con_ngrok.bat` - Backend con ngrok
- `start_cloudflare.bat` - Backend con Cloudflare Tunnel

### Scripts de Celery
- `start_celery_completo.bat` - Worker + Beat
- `start_celery_worker.bat` - Solo worker
- `start_celery_beat.bat` - Solo beat

### Scripts de Contabilidad
- `sincronizar_bcv.bat` - Sincronizar tasa BCV
- `cierre_mensual.bat` - Cierre contable mensual
- `enviar_recordatorios.bat` - Recordatorios de pago

Ver **[batch_scripts/README.md](../batch_scripts/README.md)** para documentación completa.

---

## 🧪 ARCHIVOS DE PRUEBA (test_files_archive/)

### Tests de Parsers
- `test_amadeus_parser.py`
- `test_copa_sprk.py`
- `test_wingo.py`
- `test_sabre_parser_v*.py`

### Tests de Email/WhatsApp
- `test_email_monitor*.py`
- `test_whatsapp_notifications.py`

### PDFs de Prueba
- Boletos de ejemplo de diferentes aerolíneas
- Facturas de prueba

---

## 🛠️ HERRAMIENTAS (tools_bin/)

### Ejecutables
- `ngrok.exe` - Túnel HTTP para desarrollo
- `cloudflared.exe` - Cloudflare Tunnel

---

## 📝 MEMORIA DEL PROYECTO (.amazonq/rules/memory-bank/)

### Documentos Clave
- `proyecto_travelhub.md` - Memoria general del proyecto
- `historial_cambios.md` - Historial de cambios
- `fase6_completada.md` - Fase 6 completada
- `saas_implementation.md` - Implementación SaaS
- `stripe_setup_guide.md` - Guía de Stripe
- `deployment_production.md` - Deployment a producción

### Documentos Técnicos
- `parsers_estado_octubre_2025.md` - Estado de parsers
- `consolidacion_facturas_completada.md` - Consolidación de facturas
- `libro_ventas_implementado.md` - Libro de ventas
- `retenciones_islr_implementado.md` - Retenciones ISLR
- `mejoras_boleteria_completas.md` - Mejoras de boletería

### Documentos de Fixes
- `boletos_manuales_fix.md` - Fix de boletos manuales
- `errores_corregidos.md` - Errores corregidos Fase 6
- `fix_parsers_confusion_enero_2025.md` - Fix de parsers

---

## 🎯 CÓMO USAR ESTA DOCUMENTACIÓN

### Para Desarrolladores Nuevos
1. Leer **INFORME_COMPLETO_PROYECTO.md** (este documento)
2. Leer **ORGANIZACION_PROYECTO.md**
3. Seguir **INICIO_RAPIDO.txt**
4. Explorar documentación por categoría según necesidad

### Para Deployment
1. Leer **deployment_production.md**
2. Elegir plataforma (Railway/Render)
3. Seguir guía específica de la plataforma
4. Configurar variables de entorno

### Para Desarrollo de Features
1. Revisar documentación de la categoría relevante
2. Ver ejemplos en `test_files_archive/`
3. Seguir patrones existentes en el código
4. Agregar tests

### Para Troubleshooting
1. Revisar **errores_corregidos.md**
2. Buscar en documentación histórica
3. Ver logs en `batch_scripts/`
4. Consultar memoria del proyecto

---

## 📊 ESTADÍSTICAS DE DOCUMENTACIÓN

### Documentación Principal
- **Documentos**: 10+
- **Categorías**: 7
- **Páginas totales**: 200+

### Documentación Histórica
- **Documentos**: 39
- **Categorías**: 7
- **Archivos archivados**: 75+

### Scripts y Herramientas
- **Scripts batch**: 13
- **Tests**: 15+
- **Herramientas**: 2

### Memoria del Proyecto
- **Documentos**: 30+
- **Guías técnicas**: 20+
- **Fixes documentados**: 5+

---

## 🔍 BÚSQUEDA RÁPIDA

### Por Tema
- **SaaS/Stripe**: `docs/saas/`
- **Parsers**: `docs/parsers/`
- **Facturación**: `docs/facturacion/`
- **Contabilidad**: `docs/contabilidad/`
- **Deployment**: `docs/deployment/`
- **APIs**: `docs/api/`
- **Testing**: `docs/testing/`

### Por Problema
- **Error de parseo**: `fix_parsers_confusion_enero_2025.md`
- **Error de BD**: `errores_corregidos.md`
- **Error de Celery**: `troubleshooting_celery_cloud.md`
- **Error de deployment**: `deployment_production.md`

### Por Funcionalidad
- **Boletos**: `parsers_boletos.md`, `mejoras_boleteria_completas.md`
- **Facturas**: `billing_api_completa.md`, `consolidacion_facturas_completada.md`
- **Contabilidad**: `contabilidad_venezuela_ven_nif.md`
- **SaaS**: `saas_implementation.md`, `stripe_setup_guide.md`

---

## 📞 CONTACTO Y SOPORTE

### Repositorio
- **GitHub**: https://github.com/Travelinkeo/travelhub_project

### Contacto
- **Email**: boletotravelinkeo@gmail.com
- **WhatsApp**: +584126080861

---

**Última actualización**: 25 de Enero de 2025  
**Versión**: 1.0  
**Generado por**: Amazon Q Developer
