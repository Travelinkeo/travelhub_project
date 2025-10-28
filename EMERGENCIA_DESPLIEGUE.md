# 🆘 GUÍA DE EMERGENCIA - Despliegue TravelHub

**Si algo falla en producción, sigue estos pasos:**

---

## 🔴 PROBLEMA: Sitio caído / Error 500

### Solución Rápida (2 minutos)

#### Railway.app
1. Ir a: https://railway.app/dashboard
2. Click en tu proyecto
3. Tab "Deployments"
4. Click en el deployment anterior (que funcionaba)
5. Click "Redeploy"
6. Esperar 1-2 minutos

#### Render.com
1. Ir a: https://dashboard.render.com
2. Click en tu servicio
3. Tab "Events"
4. Click "Rollback" en el deployment anterior
5. Esperar 2-3 minutos

### Verificar
```
https://tu-app.railway.app/admin/
```
Si carga → ✅ Problema resuelto

---

## 🔴 PROBLEMA: Base de datos corrupta

### Solución (5 minutos)

1. **Detener el servicio** (Railway/Render dashboard)

2. **Restaurar backup**:
```bash
# Ir a carpeta del proyecto
cd c:\Users\ARMANDO\travelhub_project

# Activar entorno
.\venv\Scripts\activate

# Restaurar (usar el backup más reciente)
python manage.py loaddata backups\backup_db_YYYYMMDD_HHMMSS.json
```

3. **Reiniciar servicio** (Railway/Render dashboard)

---

## 🔴 PROBLEMA: Migraciones fallan

### Error típico:
```
django.db.migrations.exceptions.InconsistentMigrationHistory
```

### Solución (3 minutos)

#### Opción 1: Fake migrations
```bash
python manage.py migrate --fake
```

#### Opción 2: Rollback de migración
```bash
# Ver migraciones
python manage.py showmigrations

# Rollback a migración anterior
python manage.py migrate core 0020  # Número de la migración anterior
```

---

## 🔴 PROBLEMA: No puedo hacer login

### Solución (2 minutos)

```bash
# Crear nuevo superusuario
python manage.py createsuperuser

# Usuario: admin
# Email: tu@email.com
# Password: (tu password segura)
```

---

## 🔴 PROBLEMA: Archivos media perdidos

### Solución (5 minutos)

```bash
# Restaurar desde backup
tar -xzf backups\backup_media_YYYYMMDD_HHMMSS.tar.gz

# O copiar manualmente carpeta media desde backup
```

---

## 🔴 PROBLEMA: Variables de entorno incorrectas

### Solución (3 minutos)

#### Railway.app
1. Dashboard → Tu proyecto
2. Tab "Variables"
3. Verificar/corregir:
   - `SECRET_KEY`
   - `DEBUG=False`
   - `ALLOWED_HOSTS`
   - `DATABASE_URL`

#### Render.com
1. Dashboard → Tu servicio
2. "Environment" → "Environment Variables"
3. Verificar/corregir las mismas variables

---

## 🔴 PROBLEMA: Sitio muy lento

### Diagnóstico (1 minuto)

```bash
# Ver logs en tiempo real
railway logs --tail  # Railway
# O ver en dashboard de Render
```

### Soluciones comunes:

1. **Muchas queries**: Optimizar en código
2. **Sin Redis**: Activar caché
3. **Plan gratuito saturado**: Upgrade a plan pagado

---

## 🔴 PROBLEMA: Emails no se envían

### Verificar (2 minutos)

```bash
# Probar envío
python manage.py shell

>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Mensaje', 'from@email.com', ['to@email.com'])
```

### Soluciones:
1. Verificar `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD`
2. Verificar que Gmail permite "apps menos seguras"
3. Usar App Password de Gmail (no password normal)

---

## 📞 CONTACTOS DE EMERGENCIA

### Soporte Técnico
- **Amazon Q**: Disponible 24/7 en este chat
- **Railway Discord**: https://discord.gg/railway
- **Render Community**: https://community.render.com

### Documentación
- **Checklist**: `CHECKLIST_DESPLIEGUE.md`
- **Deployment**: `docs/deployment/`
- **Troubleshooting**: `docs_archive/`

---

## 🛠️ COMANDOS ÚTILES

### Ver logs
```bash
# Railway
railway logs --tail

# Render
# Dashboard → Logs tab
```

### Verificar estado
```bash
python manage.py check --deploy
```

### Ejecutar comando en producción
```bash
# Railway
railway run python manage.py <comando>

# Render
# Dashboard → Shell tab
```

---

## 📋 CHECKLIST DE RECUPERACIÓN

Después de resolver el problema:

- [ ] Sitio funciona correctamente
- [ ] Login funciona
- [ ] Crear venta de prueba funciona
- [ ] Emails funcionan (si aplica)
- [ ] Verificar logs por 1 hora
- [ ] Documentar qué falló y cómo se resolvió
- [ ] Actualizar backup

---

## 💡 PREVENCIÓN

Para evitar emergencias futuras:

1. ✅ **Backup antes de cada despliegue**
   ```bash
   .\batch_scripts\backup_completo.bat
   ```

2. ✅ **Verificar seguridad**
   ```bash
   .\batch_scripts\verificar_seguridad.bat
   ```

3. ✅ **Probar en local primero**
   ```bash
   python manage.py runserver
   # Probar todas las funcionalidades
   ```

4. ✅ **Desplegar en horario de bajo tráfico**
   - Mejor: Madrugada o fines de semana

5. ✅ **Monitorear primeras 24 horas**
   - Revisar logs cada 2 horas

---

## 🎯 RECUERDA

> **"Si funciona en local, funcionará en producción"**
> 
> La mayoría de problemas son de configuración (variables de entorno),
> no de código.

---

**Última actualización**: Enero 2025  
**Mantén este archivo a mano durante despliegues**
