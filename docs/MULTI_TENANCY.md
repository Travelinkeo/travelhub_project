# TravelHub Multi-tenancy Architecture 🏢

TravelHub utiliza un modelo de **Aislamiento Lógico (Shared Database, Isolated Rows)** para gestionar múltiples agencias en una sola instancia.

## 1. Identificación del Inquilino (Tenant)
El modelo central es `Agencia`. Cada agencia tiene un `subdominio_slug` único (ej. `vargasviajes`) que se utiliza para:
- Filtrar datos.
- Personalizar la interfaz (Logos, Colores).
- Gestionar límites de suscripción.

## 2. El Mecanismo: `AgenciaMixin`
Casi todos los modelos operativos (`Venta`, `Boleto`, `Cliente`, `Pago`) heredan de `AgenciaMixin`.

### Cómo funciona:
- **Campo Automático:** Añade una `ForeignKey` obligatoria a `Agencia`.
- **QuerySet Manager:** Sobreescribe el método `get_queryset()` para que, por defecto, cualquier consulta (`Model.objects.all()`) aplique un filtro automático basado en la agencia del usuario actual.
- **Validación de Guardado:** Asegura que no se puedan guardar registros cruzados entre agencias.

## 3. Gestión de Contexto: `ThreadLocalContextMiddleware`
Para evitar pasar la agencia manualmente en cada función, el middleware captura la agencia del usuario logueado en cada petición HTTP y la almacena en el hilo de ejecución (`thread-local storage`).
- La función `core.utils.get_current_agencia()` permite recuperar la agencia activa en cualquier parte del código (Servicios, Tareas, Modelos).

## 4. Seguridad de Usuarios
Los usuarios se vinculan a agencias a través del modelo `UsuarioAgencia`, donde se definen roles (**Admin, Gerente, Vendedor**). Un usuario puede pertenecer a múltiples agencias pero solo opera en una a la vez (agencia activa).

## 5. Escalabilidad
Este modelo permite:
- **Costos Bajos:** Una sola base de datos y un solo servidor para cientos de agencias.
- **Facilidad de Mantenimiento:** Una sola migración actualiza a todos los clientes.
- **Rendimiento:** Índices optimizados por `agencia_id` aseguran consultas rápidas incluso con millones de registros.
