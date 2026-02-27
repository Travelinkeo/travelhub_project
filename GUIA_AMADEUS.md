    # Guía de Integración: API de Amadeus para TravelHub

Esta guía te explica paso a paso qué es Amadeus, cómo registrarte y qué haremos para conectarlo a TravelHub.

## 1. ¿Qué es Amadeus Self-Service API?
Es una plataforma que permite a desarrolladores y startups acceder al inventario de vuelos mundial (GDS) de forma sencilla.
*   **Costo:** Tiene un plan **Gratuito (Test)** con límite de consultas mensuales (unas 2,000 aprox), ideal para desarrollo. Luego se paga por uso en Producción.
*   **Qué nos permite:** Buscar vuelos, ver precios en tiempo real, horarios y aerolíneas desde tu Bot de Telegram o el Dashboard.

## 2. Tu Tarea: Obtener las Credenciales (API Keys)
Para que TravelHub pueda "hablar" con Amadeus, necesitas crear una cuenta y una "App".

### Paso A: Registro
1. Ve a [Amadeus for Developers](https://developers.amadeus.com/).
2. Haz clic en "Register" / "Sign Up".
3. Crea tu cuenta (es gratis).

### Paso B: Crear la App de TravelHub
1. Una vez dentro, ve a **"My Apps"** (en tu perfil).
2. Haz clic en **"Create New App"**.
3. **Name:** Ponle `TravelHub_Vzla` (o similar).
4. **Description:** `Sistema de gestión para agencia de viajes`.
5. **API Category:** Selecciona **"Self-Service"**.
6. Dale a **Create**.

### Paso C: Copiar las Llaves
Al crear la app, verás dos códigos muy importantes. **No los compartas con nadie más**:
*   **API Key** (o Client ID)
*   **API Secret** (o Client Secret)

Estos son los códigos que me tendrás que dar para ponerlos en el archivo `.env`.

## 3. Mi Tarea: Integración Técnica
Una vez me des las llaves, yo haré lo siguiente:

1.  **Instalar Librería:** Instalaré el SDK oficial `amadeus` en Python.
2.  **Conexión:** Configuraré TravelHub para autenticarse con tus llaves.
3.  **Crear Comando de Búsqueda:**
    *   Programaré la función interna `buscar_vuelos(origen, destino, fecha)`.
4.  **Conectar al Bot:**
    *   Habilitaré el comando `/vuelo` en Telegram.
    *   Ejemplo: `Tu: /vuelo CCS MAD 2024-12-01` -> `Bot: Oferta AirEuropa $800...`.

## 4. ¿Qué datos necesito de ti?
Solo necesito que me confirmes cuando tengas:
1.  **API Key**
2.  **API Secret**

*(Puedes pegarlos aquí en el chat cuando los tengas, o si prefieres mayor seguridad, te indico cómo ponerlos directo en el archivo .env tu mismo).*
