---
name: cloudflare-redirect-loop-fix
description: >
  Guia de diagnostico y solucion para el error ERR_TOO_MANY_REDIRECTS en
  travelhub.cc cuando el sitio funciona en la maquina local pero no en otros
  dispositivos. Aplica a la arquitectura: Cloudflare Tunnel -> Traefik (Docker)
  -> Django (Gunicorn). Usala cuando algun usuario reporte que el sitio no carga
  en moviles, navegadores externos u otros equipos.
---

# Skill: Solucion Bucle de Redireccion Cloudflare + Traefik

## Descripcion del Problema

El sitio `travelhub.cc` muestra **ERR_TOO_MANY_REDIRECTS** en todos los
dispositivos externos (telefonos, otras PCs, etc.) pero carga correctamente
en la maquina local que aloja el servidor.

Esto **no** es un problema del tunnel de Cloudflare en si, ni de Django, ni de
las cookies del navegador. Es un **bucle de redireccion HTTP->HTTPS dentro del
stack de Docker**.

---

## Arquitectura del Stack

```
Usuario (HTTPS) -> Cloudflare CDN -> cloudflared.exe (Windows Service)
    -> Traefik Docker (puerto 80 HTTP) -> travelhub_web:8000 (Django/Gunicorn)
```

Cloudflare **recibe HTTPS del cliente** pero **entrega HTTP al tunnel** (puerto 80
de Traefik). Si Traefik tiene un middleware `redirect-https` en su router HTTP,
responde con un `308 Permanent Redirect` a `https://...`. Cloudflare sigue ese
redirect, vuelve a entregar HTTP al tunnel, Traefik vuelve a redirigir -> bucle infinito.

---

## Diagnostico Rapido (< 2 minutos)

### Paso 1: Verificar que el stack Docker esta corriendo

```powershell
docker ps
```

Deben aparecer: `travelhub_web`, `travelhub_proxy`, `travelhub_nginx`,
`travelhub_worker`, `travelhub_db`, `travelhub_redis_*`.

### Paso 2: Confirmar el bucle de redireccion

```powershell
curl.exe -I -H "Host: travelhub.cc" http://localhost:80/login/
```

**Si el problema esta activo**, veras:
```
HTTP/1.1 308 Permanent Redirect
Location: https://travelhub.cc/login/
```

**Si esta resuelto**, veras:
```
HTTP/1.1 200 OK
```

### Paso 3: Verificar el archivo de configuracion de Traefik

```powershell
Get-Content c:\Users\ARMANDO\travelhub_project\traefik_data\dynamic.yml
```

Busca si el router `travelhub-http` tiene un middleware `redirect-https`:

```yaml
# ESTO CAUSA EL BUCLE - debe eliminarse:
travelhub-http:
  middlewares:
    - redirect-https
```

---

## Solucion (1 archivo + 1 comando)

### Paso 1: Editar `traefik_data/dynamic.yml`

Archivo: `c:\Users\ARMANDO\travelhub_project\traefik_data\dynamic.yml`

El archivo correcto (sin el redirect) debe quedar exactamente asi:

```yaml
http:
  routers:
    travelhub:
      rule: "Host(`travelhub.cc`) || HostRegexp(`{subdomain:[a-z0-9-]+}.travelhub.cc`)"
      entryPoints:
        - websecure
      service: travelhub
      tls:
        certResolver: letsencryptresolver
    # Router HTTP: sirve directamente sin redirigir.
    # Cloudflare Tunnel entrega trafico en HTTP al puerto 80.
    # Cloudflare gestiona el HTTPS con el cliente.
    # Si se anade redirect-https aqui, se crea un bucle infinito.
    travelhub-http:
      rule: "Host(`travelhub.cc`) || HostRegexp(`{subdomain:[a-z0-9-]+}.travelhub.cc`)"
      entryPoints:
        - web
      service: travelhub

  services:
    travelhub:
      loadBalancer:
        servers:
          - url: "http://travelhub_web:8000"
        responseForwarding:
          flushInterval: "100ms"
```

> IMPORTANTE: El router `travelhub-http` NO debe tener `middlewares: [redirect-https]`.
> Eliminar tambien el bloque `middlewares:` con `redirect-https` al final del archivo.

### Paso 2: Reiniciar Traefik

```powershell
docker restart travelhub_proxy
```

### Paso 3: Verificar

```powershell
Start-Sleep -Seconds 5
curl.exe -I -H "Host: travelhub.cc" http://localhost:80/login/
```

Debe devolver `HTTP/1.1 200 OK`. El sitio estara funcional en todos los dispositivos.

---

## Por Que Sucede Esto

El archivo `dynamic.yml` de Traefik se puede modificar accidentalmente al:

- Reconstruir los contenedores con `docker compose up --build`
- Hacer `git pull` sin revisar cambios en `traefik_data/`
- Copiar una configuracion de ejemplo que incluye el redirect

Cloudflare Zero Trust Tunnel siempre entrega trafico al puerto 80 (HTTP) de Traefik.
Traefik sirve el contenido directamente. El HTTPS lo gestiona Cloudflare en el
extremo del cliente, no Traefik. Anadir redirect HTTP->HTTPS en Traefik rompe este modelo.

---

## Diagnostico Adicional

### Ver logs de Traefik
```powershell
docker logs -f travelhub_proxy
```

### Ver logs de Nginx (salud del upstream Django)
```powershell
docker logs --tail 30 travelhub_nginx
```

Si Nginx muestra `connect() failed (111: Connection refused)` al upstream:
```powershell
docker restart travelhub_web
```

### Verificar servicio cloudflared en Windows
```powershell
Get-Service cloudflared
```
Si esta `Stopped`:
```powershell
Start-Service cloudflared
```

### Probar el sitio publico
```powershell
curl.exe -I https://travelhub.cc/login/
```
Debe retornar `HTTP/1.1 200 OK`.

---

## Resumen de Comandos de Emergencia

```powershell
# 1. Confirmar el bucle
curl.exe -I -H "Host: travelhub.cc" http://localhost:80/login/

# 2. Editar config de Traefik (quitar middlewares redirect-https del router HTTP)
notepad c:\Users\ARMANDO\travelhub_project\traefik_data\dynamic.yml

# 3. Reiniciar Traefik
docker restart travelhub_proxy

# 4. Verificar correccion (debe ser 200 OK)
Start-Sleep -Seconds 5; curl.exe -I -H "Host: travelhub.cc" http://localhost:80/login/
```

---

## Notas Importantes

- NUNCA anadir `middleware: redirect-https` al router `travelhub-http` mientras
  se use Cloudflare Tunnel. El redirect solo tiene sentido cuando el servidor esta
  expuesto directamente a internet sin Cloudflare de proxy.
- Si en el futuro se migra a un VPS dedicado sin Cloudflare Tunnel, el
  redirect-https en Traefik SI seria necesario y correcto.
- El archivo `traefik_data/dynamic.yml` esta en Git. Nunca hacer commit con
  el middleware `redirect-https` activo mientras se use Cloudflare Tunnel.
