# Guía: Compartir TravelHub en Red Local

## 🎯 Objetivo
Permitir que tu esposa acceda a TravelHub desde su computadora en la misma red WiFi.

---

## 🚀 Configuración Rápida (5 minutos)

### Paso 1: Obtener tu IP Local

**En tu computadora (donde está TravelHub):**

1. Abre CMD (Win + R, escribe `cmd`)
2. Ejecuta:
   ```bash
   ipconfig
   ```
3. Busca "Dirección IPv4" en "Adaptador de LAN inalámbrica Wi-Fi"
4. Anota la IP (ejemplo: `192.168.1.100`)

---

### Paso 2: Configurar Django

**Edita `travelhub/settings.py`:**

Busca la línea:
```python
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
```

Cámbiala por (reemplaza con TU IP):
```python
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '192.168.1.100', '*']
```

**Guarda el archivo.**

---

### Paso 3: Iniciar Servidor en Modo Red

**En tu computadora, ejecuta:**

```bash
cd C:\Users\ARMANDO\travelhub_project
venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
```

**Verás algo como:**
```
Starting development server at http://0.0.0.0:8000/
```

**¡Importante!** Deja esta ventana abierta mientras trabajen.

---

### Paso 4: Acceder desde la Otra Computadora

**En la computadora de tu esposa:**

1. Abre cualquier navegador (Chrome, Edge, Firefox)
2. En la barra de direcciones, escribe (reemplaza con TU IP):
   ```
   http://192.168.1.100:8000
   ```
3. Presiona Enter

**¡Listo!** Verá TravelHub y podrá trabajar normalmente.

---

## 🔐 Crear Usuario para tu Esposa

**En tu computadora, ejecuta:**

```bash
python manage.py createsuperuser
```

Ingresa:
- **Usuario:** (nombre de tu esposa)
- **Email:** (su email)
- **Contraseña:** (una contraseña segura)

Ahora ella puede iniciar sesión con sus propias credenciales.

---

## 📱 Acceso desde Celular/Tablet

El mismo método funciona para celulares y tablets conectados al mismo WiFi:

```
http://192.168.1.100:8000
```

---

## 🔧 Troubleshooting

### Problema: No puede conectarse

**Solución 1: Verificar Firewall**

1. Busca "Firewall de Windows Defender"
2. Clic en "Configuración avanzada"
3. Clic en "Reglas de entrada"
4. Clic en "Nueva regla..."
5. Selecciona "Puerto" → Siguiente
6. TCP, puerto específico: `8000` → Siguiente
7. Permitir la conexión → Siguiente
8. Marcar todas las opciones → Siguiente
9. Nombre: `Django TravelHub` → Finalizar

**Solución 2: Verificar que están en la misma red WiFi**

Ambas computadoras deben estar conectadas al mismo router/WiFi.

**Solución 3: Reiniciar el servidor**

Presiona `Ctrl + C` en la ventana del servidor y vuelve a ejecutar:
```bash
python manage.py runserver 0.0.0.0:8000
```

---

### Problema: La IP cambió

Si tu computadora se reinicia, la IP puede cambiar.

**Solución: IP Estática**

1. Abre "Configuración" → "Red e Internet"
2. Clic en tu WiFi → "Propiedades"
3. En "Configuración de IP", clic en "Editar"
4. Cambia a "Manual"
5. Activa IPv4
6. Ingresa:
   - IP: `192.168.1.100` (o la que prefieras)
   - Máscara: `255.255.255.0`
   - Puerta de enlace: `192.168.1.1` (IP de tu router)
   - DNS: `8.8.8.8`
7. Guardar

---

## 💡 Tips

### Mantener el Servidor Corriendo

**Opción 1: Dejar la ventana abierta**
- Simple pero ocupa una ventana

**Opción 2: Ejecutar como servicio (avanzado)**
- Usar `nssm` (Non-Sucking Service Manager)
- El servidor se inicia automáticamente con Windows

### Acceso Rápido

Crea un acceso directo en el escritorio de tu esposa:
1. Clic derecho → Nuevo → Acceso directo
2. Ubicación: `http://192.168.1.100:8000`
3. Nombre: `TravelHub`

---

## 📊 Ventajas y Limitaciones

### ✅ Ventajas
- Configuración rápida (5 minutos)
- No requiere internet
- Gratis
- Ambos ven los mismos datos en tiempo real
- Funciona en cualquier dispositivo de la red

### ⚠️ Limitaciones
- Tu computadora debe estar encendida
- Solo funciona en la misma red WiFi
- Si tu computadora se apaga, ella no puede acceder

---

## 🌐 Alternativa: Acceso Remoto (Fuera de Casa)

Si necesitan acceder desde diferentes lugares, considera:

### Opción A: ngrok (Temporal - Gratis)
```bash
# Instalar ngrok
# Descargar de: https://ngrok.com/download

# Ejecutar
ngrok http 8000
```

Te da una URL pública temporal como:
```
https://abc123.ngrok.io
```

### Opción B: Deploy en la Nube (Permanente)
- Railway.app (recomendado)
- PythonAnywhere
- Render.com

---

## 📞 Soporte

Si tienes problemas:
1. Verifica que ambas computadoras estén en el mismo WiFi
2. Verifica que el firewall permita el puerto 8000
3. Verifica que la IP sea correcta con `ipconfig`
4. Reinicia el servidor Django

---

**¡Listo para trabajar en equipo!** 🎉
