# Instrucciones para Compartir TravelHub con Ngrok

## Paso 1: Iniciar Todo

Ejecuta el archivo:
```
iniciar_completo_ngrok.bat
```

## Paso 2: Copiar las URLs

Se abrirán **2 ventanas de ngrok**. En cada una verás algo como:

**Ventana 1 (Backend - Django):**
```
Forwarding    https://abc123.ngrok-free.dev -> http://localhost:8000
```

**Ventana 2 (Frontend - Next.js):**
```
Forwarding    https://xyz789.ngrok-free.dev -> http://localhost:3000
```

## Paso 3: Compartir con tu Esposa

Envíale **AMBAS URLs**:

1. **Admin de Django (Backend):**
   ```
   https://abc123.ngrok-free.dev/admin/
   ```
   - Usuario: tu superusuario
   - Contraseña: la que configuraste

2. **Interfaz de Usuario (Frontend):**
   ```
   https://xyz789.ngrok-free.dev
   ```
   - Aquí puede usar la interfaz moderna de TravelHub

## Notas Importantes

- ⚠️ Las URLs cambian cada vez que reinicias (versión gratuita de ngrok)
- ⚠️ Mantén las ventanas abiertas mientras ella trabaje
- ⚠️ La primera vez que acceda, ngrok mostrará una página intermedia con "Visit Site" - solo hacer clic
- ✅ Funciona desde cualquier lugar del mundo
- ✅ No necesitas configurar router ni firewall

## Para Detener

Presiona cualquier tecla en la ventana principal del script.

## Alternativa: Solo Backend

Si solo necesitas compartir el admin de Django, usa:
```
iniciar_con_ngrok.bat
```
