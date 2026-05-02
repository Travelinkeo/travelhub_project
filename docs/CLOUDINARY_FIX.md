# Fix: Cloudinary no guarda archivos

## Problema
Los PDFs se generan pero no se guardan en Cloudinary. Al intentar abrir el enlace sale "Not Found".

## Solución Implementada

### 1. Configuración Actualizada en `settings.py`

✅ **Agregado**: Configuración directa de cloudinary
✅ **Actualizado**: STORAGES para usar Cloudinary en Django 5
✅ **Agregado**: Logging para diagnóstico

### 2. Logging Mejorado en `factura_pdf_generator.py`

Ahora muestra:
- Storage backend usado
- Tamaño del PDF generado
- Ruta y URL del archivo guardado
- Errores detallados con traceback

### 3. Script de Diagnóstico

Ejecutar para verificar configuración:

```bash
python test_cloudinary_upload.py
```

## Pasos para Verificar

### 1. Ejecutar Script de Diagnóstico

```bash
python test_cloudinary_upload.py
```

**Salida esperada**:
```
✅ Archivo guardado en: test_cloudinary_upload.txt
✅ URL generada: https://res.cloudinary.com/dt2xzykvz/...
✅ Archivo existe: True
✅ Archivo eliminado
```

### 2. Reiniciar Servidor Django

```bash
# Detener servidor (Ctrl+C)
python manage.py runserver
```

Deberías ver en consola:
```
✅ Cloudinary configurado: dt2xzykvz
```

### 3. Importar un Boleto

Al importar un boleto, verás en los logs:

```
INFO Iniciando generación de PDF para boleto 123
INFO Storage backend: MediaCloudinaryStorage
INFO USE_CLOUDINARY: True
INFO Generando PDF para sistema: SABRE
INFO PDF generado exitosamente, tamaño: 45678 bytes
INFO Nombre de archivo generado: Boleto_2357120126507_20250126123456.pdf
INFO ✅ PDF guardado exitosamente
INFO    Ruta: boletos_generados/Boleto_2357120126507_123.pdf
INFO    URL: https://res.cloudinary.com/dt2xzykvz/image/upload/...
INFO    Storage: MediaCloudinaryStorage
```

### 4. Generar una Factura

Al generar un PDF de factura, verás en los logs:

```
INFO Iniciando generación de PDF para factura F-20250126-0001
INFO Storage backend: MediaCloudinaryStorage
INFO USE_CLOUDINARY: True
INFO PDF generado, tamaño: 45678 bytes
INFO Nombre de archivo: factura_F-20250126-0001.pdf
INFO ✅ PDF guardado exitosamente
INFO    Ruta: facturas/2025/01/factura_F-20250126-0001.pdf
INFO    URL: https://res.cloudinary.com/dt2xzykvz/image/upload/...
INFO    Storage: MediaCloudinaryStorage
```

### 5. Verificar en Cloudinary Dashboard

1. Ir a: https://console.cloudinary.com/console/dt2xzykvz/media_library
2. Buscar carpetas:
   - `facturas/2025/01/` - Facturas
   - `boletos_generados/` - Boletos importados
3. Deberías ver los PDFs subidos

## Variables de Entorno Requeridas

### Desarrollo (.env)
```env
USE_CLOUDINARY=True
CLOUDINARY_CLOUD_NAME=dt2xzykvz
CLOUDINARY_API_KEY=235627968316473
CLOUDINARY_API_SECRET=YwKoHKorSFQmvjaDLh1MMnAqSP0
```

### Producción (Render)
Ya están configuradas correctamente ✅

## Troubleshooting

### Error: "No module named 'cloudinary'"

```bash
pip install cloudinary django-cloudinary-storage
```

### Error: "Invalid cloud_name"

Verificar que las variables de entorno estén correctas:
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('CLOUDINARY_CLOUD_NAME'))"
```

### PDFs siguen sin guardarse

1. Verificar logs del servidor Django
2. Ejecutar script de diagnóstico
3. Verificar que `USE_CLOUDINARY=True`
4. Reiniciar servidor

## Archivos Modificados

1. ✅ `travelhub/settings.py` - Configuración de Cloudinary y STORAGES
2. ✅ `core/services/factura_pdf_generator.py` - Logging detallado
3. ✅ `core/views/boleto_views.py` - Logging en importación de boletos
4. ✅ `core/ticket_parser.py` - Logging en generación de PDFs
5. ✅ `test_cloudinary_upload.py` - Script de diagnóstico (nuevo)

## Próximos Pasos

1. Ejecutar script de diagnóstico
2. Reiniciar servidor
3. Generar una factura de prueba
4. Verificar logs
5. Verificar en Cloudinary dashboard

---

**Fecha**: 26 de Enero de 2025  
**Estado**: ✅ Fix implementado, pendiente verificación
