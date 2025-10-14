# Configurar Task Scheduler para Recordatorios Automáticos

## Pasos para Windows

### 1. Abrir Programador de Tareas
- Presiona `Win + R`
- Escribe: `taskschd.msc`
- Presiona Enter

### 2. Crear Nueva Tarea
1. En el panel derecho, clic en **"Crear tarea básica..."**
2. Nombre: `TravelHub - Recordatorios de Pago`
3. Descripción: `Envía recordatorios automáticos de pago pendiente`
4. Clic en **Siguiente**

### 3. Configurar Desencadenador
1. Selecciona: **Diariamente**
2. Clic en **Siguiente**
3. Hora de inicio: `09:00:00` (9:00 AM)
4. Repetir cada: `1` días
5. Clic en **Siguiente**

### 4. Configurar Acción
1. Selecciona: **Iniciar un programa**
2. Clic en **Siguiente**
3. Programa o script:
   ```
   C:\Users\ARMANDO\travelhub_project\enviar_recordatorios.bat
   ```
4. Iniciar en (opcional):
   ```
   C:\Users\ARMANDO\travelhub_project
   ```
5. Clic en **Siguiente**

### 5. Finalizar
1. Marca: **Abrir el cuadro de diálogo Propiedades al hacer clic en Finalizar**
2. Clic en **Finalizar**

### 6. Configuración Avanzada (Opcional)
En la ventana de Propiedades:

**Pestaña General:**
- ✅ Ejecutar tanto si el usuario inició sesión como si no
- ✅ Ejecutar con los privilegios más altos

**Pestaña Desencadenadores:**
- Editar el desencadenador
- ✅ Habilitar
- Configurar repetición si deseas (ej: cada 12 horas)

**Pestaña Condiciones:**
- ❌ Iniciar la tarea solo si el equipo está conectado a la corriente alterna
- ✅ Activar la tarea si el equipo funciona con batería

**Pestaña Configuración:**
- ✅ Permitir que la tarea se ejecute a petición
- ✅ Ejecutar la tarea lo antes posible después de perder una ejecución programada
- Si la tarea en ejecución no finaliza cuando se solicita: **Detener la tarea existente**

### 7. Probar la Tarea
1. En la lista de tareas, busca: `TravelHub - Recordatorios de Pago`
2. Clic derecho → **Ejecutar**
3. Verifica que se ejecute correctamente
4. Revisa el archivo: `C:\Users\ARMANDO\travelhub_project\logs\recordatorios.log`

---

## Verificar que Funciona

### Ver Historial de Ejecuciones
1. Clic derecho en la tarea → **Propiedades**
2. Pestaña **Historial**
3. Verás todas las ejecuciones con su resultado

### Ver Logs
```bash
type C:\Users\ARMANDO\travelhub_project\logs\recordatorios.log
```

---

## Modificar Configuración

### Cambiar Hora de Ejecución
1. Clic derecho en la tarea → **Propiedades**
2. Pestaña **Desencadenadores**
3. Doble clic en el desencadenador
4. Cambiar hora
5. **Aceptar**

### Cambiar Días de Recordatorio
Edita el archivo: `enviar_recordatorios.bat`
```batch
python manage.py enviar_recordatorios_pago --dias=7
```

### Deshabilitar Temporalmente
1. Clic derecho en la tarea → **Deshabilitar**

### Eliminar Tarea
1. Clic derecho en la tarea → **Eliminar**

---

## Troubleshooting

### La tarea no se ejecuta
- Verifica que el usuario tenga permisos
- Verifica que la ruta del .bat sea correcta
- Ejecuta manualmente el .bat para ver errores

### No se envían emails/WhatsApp
- Verifica que el servidor esté corriendo (no es necesario)
- Verifica las credenciales en `.env`
- Revisa los logs de Django

### Ver errores
Modifica `enviar_recordatorios.bat`:
```batch
python manage.py enviar_recordatorios_pago --dias=3 >> logs\recordatorios.log 2>&1
```

---

## Alternativa: Ejecutar Cada 12 Horas

En **Desencadenadores**, edita y configura:
- Repetir la tarea cada: `12 horas`
- Durante: `Indefinidamente`

Esto enviará recordatorios a las 9:00 AM y 9:00 PM.
