# 🚀 Inicio Rápido - TravelHub Frontend

## ✅ Verificación Completada

Todas las funcionalidades han sido implementadas exitosamente:
- ✅ 11/11 archivos creados/modificados
- ✅ 9/9 directorios creados
- ✅ 100% de implementación

---

## 📋 Nuevas Funcionalidades Disponibles

### 1. **Dashboard Mejorado**
   - Métricas en tiempo real
   - Alertas automáticas
   - Top clientes y ventas por estado

### 2. **Liquidaciones a Proveedores**
   - Gestión completa de pagos
   - Marcar como pagada
   - Pagos parciales

### 3. **Pasaportes OCR**
   - Upload de imágenes
   - Extracción automática de datos
   - Creación de clientes

### 4. **Auditoría**
   - Timeline de ventas
   - Estadísticas de cambios
   - Filtros avanzados

### 5. **Reportes Contables**
   - Libro Diario
   - Balance de Comprobación
   - Validación de Cuadre

### 6. **Comunicaciones**
   - Inbox de proveedores
   - Categorización automática
   - Búsqueda avanzada

### 7. **Generación de Vouchers**
   - Botón en tabla de ventas
   - Descarga automática de PDF

---

## 🎯 Cómo Iniciar

### Paso 1: Iniciar el Backend
```bash
cd c:\Users\ARMANDO\travelhub_project
python manage.py runserver
```

### Paso 2: Iniciar el Frontend (en otra terminal)
```bash
cd c:\Users\ARMANDO\travelhub_project\frontend
npm run dev
```

### Paso 3: Abrir el Navegador
```
http://localhost:3000
```

---

## 🗺️ Mapa de Navegación

### Desde el Menú Lateral:

```
📊 Dashboard (/)
   └─ Métricas, alertas, top clientes

📁 CRM
   ├─ Clientes (/crm/clientes)
   └─ Proveedores (/crm/proveedores)

📦 ERP
   ├─ Ventas (/erp/ventas)
   │  └─ Botón "Voucher" en cada fila
   ├─ Boletos Importados (/erp/boletos-importados)
   ├─ Facturas (/erp/facturas-clientes)
   ├─ Cotizaciones (/erp/cotizaciones)
   ├─ 🆕 Liquidaciones (/erp/liquidaciones)
   ├─ 🆕 Pasaportes OCR (/erp/pasaportes)
   └─ 🆕 Auditoría (/erp/auditoria)

📊 Reportes
   ├─ 🆕 Libro Diario (/reportes/libro-diario)
   ├─ 🆕 Balance (/reportes/balance)
   └─ 🆕 Validación (/reportes/validacion)

📧 Comunicaciones
   └─ 🆕 Inbox Proveedores (/comunicaciones/inbox)

🌐 Traductor (/traductor)

📝 CMS (/cms)
```

---

## 🎨 Características Principales por Página

### Dashboard (/)
- **KPIs**: Total ventas, saldo pendiente, margen, CO2
- **Alertas**: Ventas sin cliente, pagos vencidos
- **Gráficos**: Ventas por estado, top clientes
- **Pendientes**: Liquidaciones y facturas

### Liquidaciones (/erp/liquidaciones)
- **Filtros**: Por estado (PEN/PAR/PAG)
- **Búsqueda**: Por proveedor, venta, localizador
- **Acciones**:
  - Botón verde: Marcar como pagada
  - Botón azul: Registrar pago parcial

### Pasaportes OCR (/erp/pasaportes)
- **Upload**: Botón azul "Subir Pasaporte"
- **Filtros**: Todos / Sin Cliente / Baja Confianza
- **Acciones**:
  - Ver imagen original
  - Verificar manualmente
  - Crear cliente automáticamente

### Auditoría (/erp/auditoria)
- **Estadísticas**: Total registros, por acción, por modelo
- **Timeline**: Buscar por ID de venta
- **Filtros**: Por acción, modelo, búsqueda libre

### Libro Diario (/reportes/libro-diario)
- **Filtros**: Rango de fechas
- **Vista**: Asientos con debe/haber
- **Exportar**: Botón para descargar Excel

### Balance (/reportes/balance)
- **Filtro**: Fecha de corte
- **Vista**: Sumas y saldos por cuenta
- **Indicador**: Diferencia debe/haber

### Validación (/reportes/validacion)
- **Auto-validación**: Al cargar la página
- **Alertas**: Verde (OK) / Roja (problemas)
- **Detalle**: Lista de asientos descuadrados

### Comunicaciones (/comunicaciones/inbox)
- **Resumen**: Por categorías
- **Búsqueda**: En asunto, remitente, contenido
- **Vista**: Tarjetas con detalle completo

### Ventas (/erp/ventas)
- **Nuevo**: Botón azul "Voucher" en cada fila
- **Acción**: Descarga PDF automáticamente

---

## 🔑 Credenciales de Prueba

Usa las credenciales de tu superusuario creado con:
```bash
python manage.py createsuperuser
```

---

## 🐛 Solución de Problemas

### Error: "Cannot connect to backend"
✅ Verificar que el backend esté corriendo en `http://localhost:8000`

### Error: "401 Unauthorized"
✅ Cerrar sesión y volver a iniciar sesión

### Página en blanco
✅ Abrir consola del navegador (F12) para ver errores
✅ Verificar que el frontend esté corriendo en `http://localhost:3000`

### Datos no aparecen
✅ Verificar que existan datos en el backend
✅ Revisar consola del navegador para errores de API

---

## 📊 Flujo de Trabajo Recomendado

### Para Gestionar una Venta Completa:

1. **Dashboard** → Ver estado general
2. **ERP → Ventas** → Crear/editar venta
3. **ERP → Ventas** → Generar voucher (botón azul)
4. **ERP → Liquidaciones** → Gestionar pago a proveedor
5. **ERP → Auditoría** → Verificar historial de cambios
6. **Reportes → Validación** → Verificar cuadre contable

### Para Procesar un Pasaporte:

1. **ERP → Pasaportes OCR** → Subir imagen
2. Sistema extrae datos automáticamente
3. Revisar confianza OCR (%)
4. **Verificar manualmente** (si es necesario)
5. **Crear cliente** con un click

### Para Revisar Contabilidad:

1. **Reportes → Validación** → Verificar cuadre
2. **Reportes → Libro Diario** → Ver asientos
3. **Reportes → Balance** → Ver sumas y saldos
4. **Reportes → Libro Diario** → Exportar Excel

---

## 📞 Soporte

Si encuentras algún problema:
1. Revisar la consola del navegador (F12)
2. Revisar logs del backend
3. Verificar que todos los servicios estén corriendo
4. Consultar la documentación en `NUEVAS_FUNCIONALIDADES_FRONTEND.md`

---

## 🎉 ¡Listo para Usar!

Todas las funcionalidades están implementadas y listas para usar.
Explora el menú lateral para descubrir todas las nuevas características.

**Versión**: 2.0  
**Fecha**: Enero 2025  
**Estado**: ✅ Producción
