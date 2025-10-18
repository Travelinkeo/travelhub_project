# 🗑️ FASE 6: ARCHIVOS OBSOLETOS

**Fecha**: Enero 2025  
**Objetivo**: Limpiar archivos obsoletos y consolidar código duplicado

---

## 📋 ARCHIVOS A MOVER A `scripts_archive/`

### Monitores de Email Deprecados (3 archivos)
Consolidados en `core/services/email_monitor_service.py`

- [ ] `core/email_monitor.py` → `scripts_archive/deprecated/`
- [ ] `core/email_monitor_v2.py` → `scripts_archive/deprecated/`
- [ ] `core/email_monitor_whatsapp_drive.py` → `scripts_archive/deprecated/`

### Scripts de Prueba en Raíz (30+ archivos)

#### Tests de Email/WhatsApp
- [ ] `test_email_con_adjunto.py`
- [ ] `test_email_connection.py`
- [ ] `test_email_simple.py`
- [ ] `test_monitor_email.py`
- [ ] `test_monitor_whatsapp.py`
- [ ] `test_whatsapp_boleto.py`
- [ ] `test_whatsapp_directo.py`
- [ ] `test_whatsapp_drive.py`
- [ ] `test_whatsapp_simple.py`

#### Tests de Parsers
- [ ] `test_amadeus_parser.py`
- [ ] `test_copa_sprk.py`
- [ ] `test_wingo.py`

#### Scripts de Procesamiento
- [ ] `enviar_email_boleto_41.py`
- [ ] `enviar_pdf_drive_whatsapp.py`
- [ ] `enviar_pdf_whatsapp_ngrok.py`
- [ ] `enviar_pdf_whatsapp_simple.py`
- [ ] `generar_pdf_amadeus_nuevo.py`
- [ ] `generar_pdf_amadeus.py`
- [ ] `generar_pdf_copa.py`
- [ ] `generar_pdf_wingo.py`
- [ ] `marcar_y_procesar_kiu.py`
- [ ] `procesar_correo_kiu_ahora.py`
- [ ] `procesar_ultimo_correo_kiu.py`
- [ ] `test_procesar_correo_kiu.py`

#### Scripts de Verificación
- [ ] `verificar_correo_kiu.py`
- [ ] `verificar_error_twilio.py`
- [ ] `verificar_ultimo_boleto.py`
- [ ] `verificar_ultimo_proceso.py`

### Documentos Obsoletos en Raíz (5 archivos)

- [ ] `CAMBIOS_SEGURIDAD_IMPLEMENTADOS.md` → Consolidado en `SEGURIDAD_ACCION_INMEDIATA.md`
- [ ] `ESTADO_ACTUAL_PROYECTO.md` → Reemplazado por `PROGRESO_PROYECTO.md`
- [ ] `INFORME_ANALISIS_CODIGO.md` → Archivado
- [ ] `PLAN_MEJORAS.md` → Completado en Fases 1-6
- [ ] `REFACTORIZACION_COMPLETADA.md` → Consolidado en `FASE2_PARSERS_COMPLETADA.md`
- [ ] `RESUMEN_EJECUTIVO_ANALISIS.md` → Archivado

---

## 📁 ESTRUCTURA PROPUESTA

### Antes (Raíz desordenada)
```
travelhub_project/
├── test_*.py (30+ archivos)
├── enviar_*.py (4 archivos)
├── generar_*.py (4 archivos)
├── procesar_*.py (3 archivos)
├── verificar_*.py (4 archivos)
├── *.md (50+ archivos)
└── ...
```

### Después (Raíz limpia)
```
travelhub_project/
├── README.md
├── PROGRESO_PROYECTO.md
├── ORGANIZACION_PROYECTO.md
├── SEGURIDAD_ACCION_INMEDIATA.md
├── INICIO_RAPIDO.txt
├── FASE*_*.md (documentos de fases)
├── manage.py
├── requirements.txt
├── .env
├── .gitignore
└── scripts_archive/
    └── deprecated/
        ├── email_monitor.py
        ├── email_monitor_v2.py
        ├── email_monitor_whatsapp_drive.py
        ├── test_*.py (30+ archivos)
        ├── enviar_*.py
        ├── generar_*.py
        ├── procesar_*.py
        └── verificar_*.py
```

---

## 🎯 BENEFICIOS

### Organización
- ✅ Raíz del proyecto más limpia
- ✅ Fácil navegación
- ✅ Menos confusión para nuevos desarrolladores

### Mantenibilidad
- ✅ Código consolidado (3 monitores → 1)
- ✅ Menos duplicación
- ✅ Más fácil de mantener

### Documentación
- ✅ Documentos principales visibles
- ✅ Archivos obsoletos archivados
- ✅ Historia preservada

---

## 📝 PLAN DE EJECUCIÓN

### Fase 1: Consolidar Monitores (Completado)
- [x] Crear `core/services/email_monitor_service.py`
- [x] Unificar funcionalidad de 3 monitores
- [x] Crear script de migración

### Fase 2: Mover Archivos Obsoletos
1. Crear carpeta `scripts_archive/deprecated/`
2. Mover monitores antiguos
3. Mover scripts de prueba
4. Mover documentos obsoletos

### Fase 3: Actualizar Referencias
1. Actualizar batch scripts
2. Actualizar documentación
3. Actualizar imports

### Fase 4: Verificación
1. Verificar que no hay imports rotos
2. Ejecutar tests
3. Verificar scripts batch

---

## ⚠️ PRECAUCIONES

### NO Eliminar
- ❌ No eliminar archivos, solo mover
- ❌ No modificar archivos en `scripts_archive/`
- ❌ Preservar historia del proyecto

### Verificar Antes de Mover
- ✅ Verificar que no hay imports activos
- ✅ Verificar que no hay referencias en código
- ✅ Verificar que no hay dependencias

---

## 📊 IMPACTO

### Archivos a Mover
- **Monitores**: 3 archivos
- **Scripts de prueba**: 30+ archivos
- **Documentos**: 6 archivos
- **Total**: ~40 archivos

### Reducción en Raíz
- **Antes**: ~100 archivos en raíz
- **Después**: ~20 archivos principales
- **Reducción**: 80% menos archivos

---

## 🚀 PRÓXIMOS PASOS

1. Ejecutar script de migración
2. Mover archivos obsoletos
3. Actualizar documentación
4. Verificar funcionamiento
5. Commit y push

---

**Última actualización**: Enero 2025  
**Estado**: En progreso  
**Archivos identificados**: 40+
