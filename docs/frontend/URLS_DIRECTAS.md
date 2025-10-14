# 🔗 URLs Directas - Acceso Rápido

## 📋 Todas las URLs del Sistema

### 🏠 Principal
- **Dashboard**: http://localhost:3000/

### 👥 CRM
- **Clientes**: http://localhost:3000/crm/clientes
- **Proveedores**: http://localhost:3000/crm/proveedores

### 📦 ERP
- **Ventas**: http://localhost:3000/erp/ventas
- **Nueva Venta**: http://localhost:3000/erp/ventas/nueva
- **Boletos Importados**: http://localhost:3000/erp/boletos-importados
- **Facturas de Clientes**: http://localhost:3000/erp/facturas-clientes
- **Cotizaciones**: http://localhost:3000/erp/cotizaciones
- **🆕 Liquidaciones**: http://localhost:3000/erp/liquidaciones
- **🆕 Pasaportes OCR**: http://localhost:3000/erp/pasaportes
- **🆕 Auditoría**: http://localhost:3000/erp/auditoria

### 📊 Reportes
- **🆕 Libro Diario**: http://localhost:3000/reportes/libro-diario
- **🆕 Balance de Comprobación**: http://localhost:3000/reportes/balance
- **🆕 Validación de Cuadre**: http://localhost:3000/reportes/validacion

### 📧 Comunicaciones
- **🆕 Inbox Proveedores**: http://localhost:3000/comunicaciones/inbox

### 🌐 Otros
- **Traductor**: http://localhost:3000/traductor
- **CMS**: http://localhost:3000/cms
- **Login**: http://localhost:3000/login

---

## 🔌 Endpoints del Backend

### Dashboard
```
GET  http://localhost:8000/api/dashboard/metricas/
GET  http://localhost:8000/api/dashboard/alertas/
```

### Liquidaciones
```
GET    http://localhost:8000/api/liquidaciones/
POST   http://localhost:8000/api/liquidaciones/
GET    http://localhost:8000/api/liquidaciones/{id}/
PUT    http://localhost:8000/api/liquidaciones/{id}/
DELETE http://localhost:8000/api/liquidaciones/{id}/
POST   http://localhost:8000/api/liquidaciones/{id}/marcar_pagada/
POST   http://localhost:8000/api/liquidaciones/{id}/registrar_pago_parcial/
GET    http://localhost:8000/api/liquidaciones/pendientes/
GET    http://localhost:8000/api/liquidaciones/por_proveedor/?proveedor_id={id}
```

### Pasaportes
```
GET    http://localhost:8000/api/pasaportes/
POST   http://localhost:8000/api/pasaportes/
GET    http://localhost:8000/api/pasaportes/{id}/
PUT    http://localhost:8000/api/pasaportes/{id}/
DELETE http://localhost:8000/api/pasaportes/{id}/
POST   http://localhost:8000/api/pasaportes/{id}/verificar/
POST   http://localhost:8000/api/pasaportes/{id}/crear_cliente/
GET    http://localhost:8000/api/pasaportes/pendientes/
GET    http://localhost:8000/api/pasaportes/baja_confianza/?umbral=0.7
```

### Auditoría
```
GET http://localhost:8000/api/auditoria/venta/{id}/
GET http://localhost:8000/api/auditoria/estadisticas/
GET http://localhost:8000/api/audit-logs/
```

### Reportes
```
GET http://localhost:8000/api/reportes/libro-diario/?fecha_desde=YYYY-MM-DD&fecha_hasta=YYYY-MM-DD
GET http://localhost:8000/api/reportes/balance-comprobacion/?fecha_hasta=YYYY-MM-DD
GET http://localhost:8000/api/reportes/validar-cuadre/
GET http://localhost:8000/api/reportes/exportar-excel/?fecha_desde=YYYY-MM-DD&fecha_hasta=YYYY-MM-DD
```

### Comunicaciones
```
GET http://localhost:8000/api/comunicaciones/
GET http://localhost:8000/api/comunicaciones/por_categoria/
GET http://localhost:8000/api/comunicaciones/recientes/
```

### Vouchers
```
POST http://localhost:8000/api/ventas/{id}/generar-voucher/
```

### Boletos
```
GET  http://localhost:8000/api/boletos/sin-venta/
POST http://localhost:8000/api/boletos/{id}/reintentar-parseo/
POST http://localhost:8000/api/boletos/{id}/crear-venta/
```

---

## 📚 Documentación API

### Swagger UI (Interactivo)
```
http://localhost:8000/api/docs/
```

### ReDoc (Estático)
```
http://localhost:8000/api/redoc/
```

### Schema JSON
```
http://localhost:8000/api/schema/
```

---

## 🔐 Autenticación

### Obtener Token JWT
```bash
curl -X POST http://localhost:8000/api/auth/jwt/obtain/ \
  -H "Content-Type: application/json" \
  -d '{"username": "tu_usuario", "password": "tu_password"}'
```

### Refresh Token
```bash
curl -X POST http://localhost:8000/api/auth/jwt/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "tu_refresh_token"}'
```

### Usar Token en Requests
```bash
curl -X GET http://localhost:8000/api/ventas/ \
  -H "Authorization: Bearer tu_access_token"
```

---

## 🧪 URLs de Prueba con Datos

### Dashboard con Filtros
```
http://localhost:3000/?fecha_desde=2025-01-01&fecha_hasta=2025-01-31
```

### Liquidaciones Filtradas
```
http://localhost:3000/erp/liquidaciones?estado=PEN
http://localhost:3000/erp/liquidaciones?search=proveedor
```

### Pasaportes Filtrados
```
http://localhost:3000/erp/pasaportes?filtro=pendientes
http://localhost:3000/erp/pasaportes?filtro=baja_confianza
```

### Auditoría con Filtros
```
http://localhost:3000/erp/auditoria?accion=CREATE
http://localhost:3000/erp/auditoria?modelo=Venta
```

### Libro Diario con Fechas
```
http://localhost:3000/reportes/libro-diario?fecha_desde=2025-01-01&fecha_hasta=2025-01-31
```

---

## 🚀 Acceso Rápido desde Terminal

### Windows (PowerShell)
```powershell
# Abrir Dashboard
start http://localhost:3000/

# Abrir Liquidaciones
start http://localhost:3000/erp/liquidaciones

# Abrir Pasaportes
start http://localhost:3000/erp/pasaportes

# Abrir Auditoría
start http://localhost:3000/erp/auditoria

# Abrir Reportes
start http://localhost:3000/reportes/libro-diario

# Abrir Comunicaciones
start http://localhost:3000/comunicaciones/inbox

# Abrir Swagger
start http://localhost:8000/api/docs/
```

### Linux/Mac
```bash
# Abrir Dashboard
xdg-open http://localhost:3000/

# Abrir Liquidaciones
xdg-open http://localhost:3000/erp/liquidaciones

# Abrir Pasaportes
xdg-open http://localhost:3000/erp/pasaportes
```

---

## 📱 Bookmarks Recomendados

Guarda estos bookmarks en tu navegador para acceso rápido:

1. **Dashboard**: http://localhost:3000/
2. **Ventas**: http://localhost:3000/erp/ventas
3. **Liquidaciones**: http://localhost:3000/erp/liquidaciones
4. **Pasaportes**: http://localhost:3000/erp/pasaportes
5. **Auditoría**: http://localhost:3000/erp/auditoria
6. **Libro Diario**: http://localhost:3000/reportes/libro-diario
7. **Comunicaciones**: http://localhost:3000/comunicaciones/inbox
8. **API Docs**: http://localhost:8000/api/docs/

---

## 🔍 Búsquedas Rápidas

### Buscar Venta por Localizador
```
http://localhost:3000/erp/ventas?search=ABC123
```

### Buscar Cliente
```
http://localhost:3000/crm/clientes?search=Juan
```

### Buscar Liquidación
```
http://localhost:3000/erp/liquidaciones?search=proveedor
```

### Buscar Comunicación
```
http://localhost:3000/comunicaciones/inbox?search=reserva
```

---

## 📊 Exportaciones Directas

### Exportar Libro Diario a Excel
```
http://localhost:8000/api/reportes/exportar-excel/?fecha_desde=2025-01-01&fecha_hasta=2025-01-31
```

### Descargar Voucher
```
http://localhost:8000/api/ventas/{id}/generar-voucher/
```

---

## 🎯 Flujos de Trabajo con URLs

### Flujo: Gestionar Venta Completa
1. http://localhost:3000/ (ver dashboard)
2. http://localhost:3000/erp/ventas (crear/editar)
3. http://localhost:3000/erp/ventas (generar voucher)
4. http://localhost:3000/erp/liquidaciones (pagar proveedor)
5. http://localhost:3000/erp/auditoria (verificar cambios)

### Flujo: Procesar Pasaporte
1. http://localhost:3000/erp/pasaportes (subir imagen)
2. http://localhost:3000/erp/pasaportes (verificar OCR)
3. http://localhost:3000/erp/pasaportes (crear cliente)
4. http://localhost:3000/crm/clientes (ver cliente creado)

### Flujo: Revisar Contabilidad
1. http://localhost:3000/reportes/validacion (verificar cuadre)
2. http://localhost:3000/reportes/libro-diario (ver asientos)
3. http://localhost:3000/reportes/balance (ver saldos)
4. http://localhost:8000/api/reportes/exportar-excel/ (exportar)

---

## 💡 Tips de Navegación

### Atajos de Teclado (en desarrollo)
- `Ctrl + K`: Búsqueda rápida
- `Ctrl + B`: Toggle sidebar
- `Ctrl + H`: Ir a home

### Navegación por Menú
- Todas las páginas están accesibles desde el menú lateral
- El menú se colapsa automáticamente en móviles
- Click en el logo para volver al dashboard

---

**Última Actualización**: Enero 2025  
**Versión**: 2.0
