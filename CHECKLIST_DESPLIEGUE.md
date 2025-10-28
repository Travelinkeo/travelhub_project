# ✅ Checklist de Despliegue - TravelHub

**Fecha**: Antes de cada despliegue  
**Tiempo estimado**: 15 minutos

---

## 🔴 CRÍTICO (Hacer SIEMPRE)

### 1. Backup Completo
```bash
.\batch_scripts\backup_completo.bat
```
- [ ] Backup de base de datos creado
- [ ] Backup de media creado
- [ ] Backup de .env creado
- [ ] Archivos guardados en lugar seguro (Drive/Dropbox)

### 2. Verificación de Seguridad
```bash
.\batch_scripts\verificar_seguridad.bat
```
- [ ] .env NO está en git
- [ ] SECRET_KEY tiene más de 40 caracteres
- [ ] DEBUG=False en producción
- [ ] ALLOWED_HOSTS configurado correctamente

### 3. Variables de Entorno en Producción
- [ ] SECRET_KEY único y seguro (50+ caracteres)
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS=*.railway.app (o tu dominio)
- [ ] DATABASE_URL configurada
- [ ] REDIS_URL configurada (si usas)
- [ ] GEMINI_API_KEY configurada
- [ ] EMAIL_HOST_USER y PASSWORD configurados
- [ ] STRIPE_SECRET_KEY (modo LIVE, no test)

---

## 🟡 IMPORTANTE (Verificar)

### 4. Base de Datos
```bash
python manage.py check --deploy
python manage.py migrate --check
```
- [ ] Sin errores en check
- [ ] Migraciones aplicadas

### 5. Archivos Estáticos
```bash
python manage.py collectstatic --noinput
```
- [ ] Archivos estáticos recopilados

### 6. Tests Básicos
```bash
pytest tests/test_core.py -v
```
- [ ] Tests principales pasando

---

## 🟢 OPCIONAL (Recomendado)

### 7. Limpieza
- [ ] Sin archivos .next/ en git
- [ ] Sin node_modules/ en git
- [ ] Sin archivos de prueba en raíz

### 8. Documentación
- [ ] README.md actualizado
- [ ] Variables de entorno documentadas
- [ ] Contactos de emergencia actualizados

---

## 🚀 DESPLIEGUE

### Railway.app
1. [ ] Push a GitHub
2. [ ] Railway detecta cambios y despliega automáticamente
3. [ ] Verificar logs: `railway logs --tail`
4. [ ] Probar URL: https://tu-app.railway.app

### Render.com
1. [ ] Push a GitHub
2. [ ] Render detecta cambios y despliega
3. [ ] Verificar logs en dashboard
4. [ ] Probar URL: https://tu-app.onrender.com

---

## 🆘 PLAN DE EMERGENCIA

### Si algo falla:

#### Opción 1: Rollback (Railway/Render)
- Railway: Dashboard → Deployments → Click en versión anterior → Redeploy
- Render: Dashboard → Deployments → Rollback

#### Opción 2: Restaurar Backup
```bash
# Restaurar base de datos
python manage.py loaddata backups\backup_db_YYYYMMDD_HHMMSS.json

# Restaurar media
tar -xzf backups\backup_media_YYYYMMDD_HHMMSS.tar.gz
```

#### Opción 3: Contactar Soporte
- **Amazon Q**: Disponible 24/7 para ayuda
- **Railway Discord**: https://discord.gg/railway
- **Render Community**: https://community.render.com

---

## 📊 POST-DESPLIEGUE

### Verificar que todo funciona:
- [ ] Login en admin: https://tu-app/admin/
- [ ] Crear venta de prueba
- [ ] Subir boleto de prueba
- [ ] Generar factura de prueba
- [ ] Verificar emails (si configurado)
- [ ] Verificar WhatsApp (si configurado)

### Monitoreo (primeras 24 horas):
- [ ] Revisar logs cada 2 horas
- [ ] Verificar errores en Sentry (si configurado)
- [ ] Probar funcionalidades críticas

---

## 📝 Notas

**Última verificación**: _____________  
**Desplegado por**: _____________  
**Versión**: _____________  
**Problemas encontrados**: _____________

---

## 🎯 Comandos Rápidos

```bash
# Backup
.\batch_scripts\backup_completo.bat

# Verificar seguridad
.\batch_scripts\verificar_seguridad.bat

# Ver logs (Railway)
railway logs --tail

# Ver logs (Render)
# Dashboard → Logs

# Rollback (Railway)
railway rollback

# Check Django
python manage.py check --deploy
```

---

**IMPORTANTE**: Guarda este checklist y úsalo CADA VEZ que despliegues.
