import json
import logging
import os

from django.core.management.base import BaseCommand
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command."""

    help = "Runs the Telegram Bot for TravelHub. Use --webhook to run in webhook mode."

    def add_arguments(self, parser):
        """add_arguments."""
        parser.add_argument(
            "--webhook",
            type=str,
            default=None,
            help="URL pública para webhook (ej: https://tudominio.com/telegram/webhook/)",
        )
        parser.add_argument(
            "--webhook-port",
            type=int,
            default=8443,
            help="Puerto para el webhook (default: 8443)",
        )

    def handle(self, *args, **options):
        """handle."""
        self.stdout.write(self.style.SUCCESS("Starting TravelHub Telegram Bot..."))

        # Obtener token
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            self.stdout.write(self.style.ERROR("TELEGRAM_BOT_TOKEN not found in .env"))
            return

        # --- Helper SaaS ---
        from asgiref.sync import sync_to_async

        from core.models.agencia import UsuarioAgencia

        @sync_to_async
        def get_agency_context(telegram_user_id):
            """
            Resuelve la agencia basada en el ID de Telegram.
            Retorna (Agencia, Usuario) o (None, None).
            """
            # Buscar UsuarioAgencia activo con ese telegram_chat_id
            ua = (
                UsuarioAgencia.objects.filter(
                    telegram_chat_id=str(telegram_user_id), activo=True, agencia__activa=True
                )
                .select_related("agencia", "usuario")
                .first()
            )

            if ua:
                return ua.agencia, ua.usuario
            return None, None

        # Definir funciones del bot
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Send a message when the command /start is issued."""
            user = update.effective_user
            chat_id = update.effective_chat.id

            agencia, _ = await get_agency_context(user.id)

            msg_bienvenida = (
                rf"👋 ¡Hola {user.mention_html()}! Bienvenid@ a TravelHub Bot."
                "\n\n🆔 <b>Tu ID de Telegram es:</b> <code>{chat_id}</code>"
            )

            if agencia:
                msg_bienvenida += f"\n🏢 <b>Agencia Detectada:</b> {agencia.nombre}"
            else:
                # Check if it's a client
                from apps.crm.models import Cliente

                cliente = await sync_to_async(
                    lambda: Cliente.objects.filter(telegram_chat_id=str(chat_id)).first()
                )()
                if cliente:
                    msg_bienvenida += f"\n👤 <b>Cliente:</b> {cliente.nombres}"
                else:
                    msg_bienvenida += (
                        "\n⚠️ <b>No estás registrado.</b>"
                        "\n• Si eres <b>agente</b>: envía este ID a tu administrador."
                        "\n• Si eres <b>cliente</b>: pide a tu agencia que te vincule."
                    )

            msg_bienvenida += (
                "\n\n💡 <b>Comandos disponibles:</b>"
                "\n🔹 /status - Estado del sistema"
                "\n🔹 /buscar [apellido] - Buscar cliente"
                "\n🔹 /vuelo ORIG DEST FECHA - Buscar vuelo"
                "\n🔹 /flyer DESTINO PRECIO - Crear flyer"
                "\n🔹 /check_visa NAC DEST - Requisitos visa"
            )

            await update.message.reply_html(
                msg_bienvenida,
                reply_markup=ForceReply(selective=True),
            )
            # Log de seguridad
            logger.info(f"Usuario {user.first_name} ({chat_id}) inició el bot.")

        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Send a message when the command /help is issued."""
            help_text = (
                "🤖 <b>Comandos TravelHub:</b>\n\n"
                "👤 <b>Staff / Agentes</b>\n"
                "/buscar [apellido] - Buscar clientes\n"
                "/status - Resumen del sistema\n"
                "/vuelo ORIG DEST FECHA - Buscar vuelo (Amadeus)\n"
                "/flyer DEST PRECIO [AEROLINEA] - Crear flyer promocional\n"
                "/verboleto ID - Ver boleto (PDF)\n"
                "/check_visa NAC DEST - Requisitos de visa\n"
                "/app - Abrir diseñador de flyers\n\n"
                "👤 <b>Clientes</b>\n"
                "/misreservas - Ver tus reservas activas\n"
                "/mivuelo - Estado de tu último vuelo\n"
                "/mivoucher - Descargar tu voucher PDF\n\n"
                "⚙️ <b>General</b>\n"
                "/id - Tu ID de chat\n"
                "/ayuda - Este mensaje"
            )
            await update.message.reply_html(help_text)

        async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """get_id."""
            chat_id = update.effective_chat.id
            await update.message.reply_html(f"🆔 Tu ID es: <code>{chat_id}</code>")

        async def buscar_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Busca clientes por apellido o nombre."""
            query = " ".join(context.args)
            if not query:
                await update.message.reply_text(
                    "⚠️ Por favor escribe un nombre o apellido.\nEjemplo: /buscar Perez"
                )
                return

            from asgiref.sync import sync_to_async
            from django.db.models import Q

            from apps.crm.models import Cliente

            try:
                agencia, _ = await get_agency_context(update.effective_user.id)
                if not agencia:
                    await update.message.reply_text(
                        "🚫 No tienes permiso (Agencia no vinculada). Envía /start para ver tu ID."
                    )
                    return

                # Búsqueda asíncrona
                @sync_to_async
                def query_db():
                    """query_db."""
                    return list(
                        Cliente.objects.filter(
                            agencia=agencia  # SaaS Filter
                        ).filter(
                            Q(nombres__icontains=query)
                            | Q(apellidos__icontains=query)
                            | Q(nombre_empresa__icontains=query)
                        )[:5]
                    )  # Limit to 5 results

                clientes = await query_db()

                if not clientes:
                    await update.message.reply_text(f"❌ No encontré clientes con: '{query}'")
                    return

                msg = f"🔍 **Resultados para '{query}':**\n\n"
                for c in clientes:
                    nombre = c.nombre_empresa if c.nombre_empresa else f"{c.nombres} {c.apellidos}"
                    msg += f"👤 **{nombre}**\n"
                    msg += f"   📧 {c.email or 'Sin email'}\n"
                    msg += f"   📱 {c.telefono_principal or 'Sin tlf'}\n\n"

                await update.message.reply_markdown(msg)

            except Exception as e:
                logger.error(f"Error buscando cliente: {e}")
                await update.message.reply_text("💥 Error en la búsqueda.")

        async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Check system status."""
            from apps.bookings.models import Venta
            from apps.crm.models import Cliente

            try:
                agencia, _ = await get_agency_context(update.effective_user.id)
                if not agencia:
                    await update.message.reply_text("🚫 Sin acceso. Agencia no detectada.")
                    return

                # Consulta simple a DB para verificar conexión
                from asgiref.sync import sync_to_async

                count_clientes = await sync_to_async(
                    Cliente.objects.filter(agencia=agencia).count
                )()
                count_ventas = await sync_to_async(Venta.objects.filter(agencia=agencia).count)()

                msg = (
                    "✅ **Sistema Operativo**\n"
                    f"👥 Clientes: `{count_clientes}`\n"
                    f"💰 Ventas Registradas: `{count_ventas}`\n"
                    "🟢 Base de Datos: Conectada"
                )
                await update.message.reply_markdown(msg)
            except Exception as e:
                logger.error(f"Error en status: {e}")
                await update.message.reply_text("⚠️ Error verificando estado del sistema.")

        async def process_natural_language(
            update: Update, context: ContextTypes.DEFAULT_TYPE
        ) -> None:
            """Procesa mensajes de texto con Linkeo Agent (Gemini)."""
            user_msg = update.message.text
            user = update.effective_user

            # Feedback visual
            user_msg = update.message.text
            # print(f"DEBUG: Mensaje recibido: '{user_msg}'") # REMOVED: Unsafe for Windows Console
            logger.info(f"DEBUG_LOGGER: Mensaje recibido: '{user_msg}'")

            await update.message.reply_chat_action("typing")

            from asgiref.sync import sync_to_async

            from apps.automation.services.linkeo_service import LinkeoService

            try:
                agencia, _ = await get_agency_context(user.id)

                @sync_to_async
                def ask_linkeo():
                    """ask_linkeo."""
                    # print("DEBUG: Llamando a LinkeoService...")
                    # Pasamos contexto básico del usuario y AGENCIA
                    return LinkeoService.process_message(user_msg, user_id=user.id, agencia=agencia)

                response = await ask_linkeo()
                # print(f"DEBUG: Respuesta generada: {response[:50]}...")
                await update.message.reply_html(response)

            except Exception as e:
                import traceback

                # Usar logger en lugar de print para evitar UnicodeEncodeError en Windows
                logger.error(f"ERROR LINKEO:\n{traceback.format_exc()}")
                await update.message.reply_text(f"😵 Tuve un cortocircuito: {str(e)}")

        # Iniciar aplicación con timeouts aumentados
        application = (
            Application.builder()
            .token(token)
            .read_timeout(30)
            .write_timeout(30)
            .connect_timeout(30)
            .pool_timeout(30)
            .build()
        )

        async def flyer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """
            Genera un flyer promocional.
            Uso: /flyer [Destino] [Precio] [Aerolinea - Opcional]
            Ejemplo: /flyer Madrid 850 AirEuropa
            """
            if not context.args or len(context.args) < 2:
                await update.message.reply_text(
                    "🎨 **Modo Diseñador Flash**\n\n"
                    "Uso: `/flyer [Destino] [Precio]`\n"
                    "Ejemplo: `/flyer Madrid 850`\n"
                    "Opcional: `/flyer Madrid 850 AirEuropa`",
                    parse_mode="Markdown",
                )
                return

            # Buscar cuál argumento es el precio (el primero que tenga números)
            price_index = -1
            for i, arg in enumerate(context.args):
                if any(char.isdigit() for char in arg):
                    price_index = i
                    break

            if price_index == -1 or price_index == 0:
                # No se encontró precio o es el primer argumento (sin destino)
                await update.message.reply_text(
                    "⚠️ No pude identificar el precio.\n"
                    "Asegúrate de incluir el destino y luego el precio (con números).\n"
                    "Ejemplo: `/flyer New York 650`",
                    parse_mode="Markdown",
                )
                return

            destination = " ".join(context.args[:price_index])
            price = context.args[price_index]
            airline = (
                " ".join(context.args[price_index + 1 :])
                if len(context.args) > price_index + 1
                else None
            )

            # Limpieza básica de precio (redundante pero segura)
            if not any(char.isdigit() for char in price):
                await update.message.reply_text("⚠️ El precio debe contener números.")
                return

            await update.message.reply_chat_action("upload_photo")

            try:
                # Ejecutar generación en hilo aparte para no bloquear el bot
                from asgiref.sync import sync_to_async

                from apps.marketing.services.flash_marketing_service import FlashMarketingService

                service = FlashMarketingService()

                @sync_to_async
                def generate():
                    """generate."""
                    return service.generate_flyer(destination, price, airline)

                img_buffer = await generate()

                caption = (
                    f"🔥 **¡OFERTA FLASH: {destination.upper()}!** 🔥\n\n"
                    f"✈️ Vuela desde **{price}**\n"
                    f"{f'🏢 Con {airline}' if airline else ''}\n\n"
                    f"📲 Reserva YA. Cupos limitados.\n"
                    f"#Oferta #Viajes #TravelHub #{destination}"
                )

                await update.message.reply_photo(
                    photo=img_buffer, caption=caption, parse_mode="Markdown"
                )

            except Exception as e:
                logger.error(f"Error generando flyer: {e}")
                await update.message.reply_text("❌ Error generando la imagen. Revisa los logs.")

        async def buscar_vuelo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """
            Busca vuelos usando Amadeus.
            Uso: /vuelo [origen] [destino] [fecha YYYY-MM-DD]
            Ejemplo: /vuelo CCS MAD 2025-11-20
            """
            usage_msg = (
                "✈️ **Uso:** `/vuelo [ORIGEN] [DESTINO] [FECHA]`\nEj: `/vuelo CCS MAD 2025-11-15`"
            )

            if len(context.args) < 3:
                await update.message.reply_markdown(usage_msg)
                return

            origin = context.args[0].upper()
            destination = context.args[1].upper()
            date = context.args[2]

            # Validación básica de fecha
            if len(date) != 10 or date.count("-") != 2:
                await update.message.reply_text("⚠️ Formato de fecha inválido. Usa AAAA-MM-DD.")
                return

            await update.message.reply_text(
                f"🔎 Buscando ofertas {origin} ➡️ {destination} ({date})..."
            )

            # Ejecutar búsqueda en hilo aparte (porque Amadeus SDK es síncrono/bloqueante)
            from asgiref.sync import sync_to_async

            from apps.automation.services.amadeus_service import AmadeusService

            try:

                @sync_to_async
                def search():
                    """search."""
                    service = AmadeusService()
                    return service.buscar_vuelos(origin, destination, date)

                resultados = await search()

                if isinstance(resultados, dict) and "error" in resultados:
                    await update.message.reply_text(f"❌ Error: {resultados['error']}")
                    return

                if not resultados:
                    await update.message.reply_text(
                        "🤷‍♂️ No encontré vuelos disponibles para esa fecha."
                    )
                    return

                msg = f"✈️ **Resultados {origin}-{destination}**\n\n"
                for i, r in enumerate(resultados[:5], 1):
                    msg += f"{i}. 💰 **{r['precio']}** | {r['aerolinea']}\n"
                    msg += f"   🔄 {r['ruta']}\n\n"

                msg += "⚠️ *Precios referenciales sujetos a cambio.*"
                await update.message.reply_markdown(msg)

            except Exception as e:
                logger.error(f"Error en comando vuelo: {e}")
                await update.message.reply_text("💥 Ocurrió un error buscando los vuelos.")

        async def check_visa_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """
            Consulta rápida de requisitos de visa.
            Uso: /check_visa [Nacionalidad] [Destino]
            Ejemplo: /check_visa VEN ESP
            """
            if len(context.args) < 2:
                await update.message.reply_text(
                    "🛂 **Consulta de Visas**\n\n"
                    "Uso: `/check_visa [Nacionalidad] [Destino]`\n"
                    "Ejemplo: `/check_visa VEN ESP` (Códigos de 3 letras)\n"
                    "Ejemplo: `/check_visa Venezuela España`",
                    parse_mode="Markdown",
                )
                return

            nationality = context.args[0].upper()
            destination = context.args[1].upper()

            # Mapeo básico de nombres a códigos si el usuario no usa ISO (MVP)
            # Idealmente esto se mejoraría con un servicio de normalización de países
            # Por ahora, confiamos en que intenten usar ISO o pasamos el nombre a Gemini

            await update.message.reply_chat_action("typing")

            from asgiref.sync import sync_to_async

            from apps.automation.services.migration_checker_service import MigrationCheckerService

            try:

                @sync_to_async
                def perform_check():
                    """perform_check."""
                    service = MigrationCheckerService()
                    # Si el input es largo (>3 chars), prob. es nombre completo.
                    # El servicio (quick_check) espera códigos ISO para cache/reglas locales,
                    # pero Gemini entiende nombres.
                    # Para el MVP, pasamos lo que el usuario escriba.
                    return service.quick_check(nationality, destination)

                result = await perform_check()

                # Construir respuesta
                emoji_status = "white_check_mark"
                if result.alert_level == "RED":
                    emoji_status = "no_entry"
                elif result.alert_level == "YELLOW":
                    emoji_status = "warning"
                elif result.alert_level == "GREEN":
                    emoji_status = "white_check_mark"

                msg = f":{emoji_status}: **Resultado para {nationality} ➡️ {destination}**\n\n"

                if result.visa_required:
                    msg += "🛂 **Visa Requerida:** Sí\n"
                    msg += f"📝 **Tipo:** {result.visa_type}\n"
                else:
                    msg += "✅ **Visa:** No requerida\n"

                msg += f"📘 **Pasaporte:** {result.passport_min_months} meses validez mín.\n"

                if result.vaccination_required:
                    msg += f"💉 **Vacunas:** {', '.join(result.vaccination_required)}\n"

                msg += f"\nℹ️ {result.summary}"

                await update.message.reply_markdown(msg)

            except Exception as e:
                logger.error(f"Error en /check_visa: {e}")
                await update.message.reply_text(
                    "❌ Error consultando requisitos. Intenta con códigos ISO (ej: VEN, USA)."
                )

        async def ver_boleto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """
            Recupera un boleto desde la nube de Telegram.
            Uso: /verboleto [ID_Boleto]
            """
            if not context.args:
                await update.message.reply_text(
                    "⚠️ Uso: `/verboleto [ID]` (Ej: `/verboleto 123`)", parse_mode="Markdown"
                )
                return

            try:
                boleto_id = context.args[0]
                from asgiref.sync import sync_to_async

                from apps.bookings.models import BoletoImportado

                agencia, _ = await get_agency_context(update.effective_user.id)
                if not agencia:
                    await update.message.reply_text("🚫 Acceso denegado.")
                    return

                # Buscar boleto (sync wrapper)
                @sync_to_async
                def get_boleto_data(pk):
                    """get_boleto_data."""
                    try:
                        # SaaS Filter: Solo boletos de mi agencia
                        b = BoletoImportado.objects.get(pk=pk, agencia=agencia)
                        return (
                            b.telegram_file_id,
                            b.archivo_pdf_generado.name if b.archivo_pdf_generado else "boleto.pdf",
                        )
                    except BoletoImportado.DoesNotExist:
                        return None, None

                file_id, filename = await get_boleto_data(boleto_id)

                if file_id:
                    # Si tiene ID de Telegram, es instantáneo (reenvío)
                    await update.message.reply_document(
                        document=file_id, caption=f"🎫 Boleto #{boleto_id} (Desde Nube Telegram)"
                    )
                else:
                    await update.message.reply_text(
                        f"❌ El boleto #{boleto_id} no tiene respaldo en Telegram o no existe."
                    )

            except Exception as e:
                logger.error(f"Error en /verboleto: {e}")
                await update.message.reply_text("❌ Error recuperando boleto.")

        async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Maneja notas de voz recibidas"""
            # Solo permitir en privado o si es reply al bot (para no saturar grupos)
            # Por ahora, permitimos todo para facilitar pruebas.

            user = update.message.from_user
            await update.message.reply_chat_action("typing")  # Feedback visual "escribiendo..."

            # Descargar archivo
            voice_file = await update.message.voice.get_file()

            # Guardar temporalmente
            import os
            import tempfile

            from asgiref.sync import sync_to_async

            from apps.automation.services.audio_service import AudioTranscriptionService

            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                temp_path = tmp.name

            try:
                await voice_file.download_to_drive(temp_path)
                await update.message.reply_text(f"🎧 Escuchando audio de {user.first_name}...")

                # Procesar con Gemini (Sync wrapper)
                @sync_to_async
                def process_audio(path):
                    """process_audio."""
                    service = AudioTranscriptionService()
                    return service.transcribe_and_extract(path)

                result = await process_audio(temp_path)

                if result.get("error"):
                    await update.message.reply_text(f"⚠️ Error procesando audio: {result['error']}")
                else:
                    transcription = result.get("transcription", "")
                    data = result.get("travel_data")

                    response_msg = f"🗣️ **Transcripción:**\n_{transcription}_\n\n"

                    if data:
                        response_msg += "📋 **Datos Extraídos:**\n"
                        response_msg += f"🛫 **Origen:** {data.get('origin', 'N/A')}\n"
                        response_msg += f"🛬 **Destino:** {data.get('destination', 'N/A')}\n"
                        response_msg += f"📅 **Salida:** {data.get('departure_date', 'N/A')}\n"
                        if data.get("return_date"):
                            response_msg += f"📅 **Retorno:** {data.get('return_date')}\n"
                        response_msg += f"👥 **Pax:** {data.get('passengers', 'N/A')}\n"

                        # Botón sugerido (Futuro: Buscar vuelo directo)
                        # await update.message.reply_text(response_msg, parse_mode='Markdown')

                        # Si tenemos datos básicos, sugerir comando de búsqueda
                        if (
                            data.get("origin")
                            and data.get("destination")
                            and data.get("departure_date")
                        ):
                            cmd_sugerido = f"/vuelo {data['origin']} {data['destination']} {data['departure_date']}"
                            response_msg += f"\n💡 **Prueba:** `{cmd_sugerido}`"

                    await update.message.reply_markdown(response_msg)

            except Exception as e:
                logger.error(f"Error handling voice: {e}")
                await update.message.reply_text("❌ Error inexperado con el audio.")
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Maneja los datos recibidos desde la Mini App"""
            # Esta función queda como fallback por si se usa sendData en el futuro
            try:
                data = json.loads(update.effective_message.web_app_data.data)

                if data.get("action") == "generate_flyer":
                    destination = data.get("destination")
                    price = data.get("price")
                    airline = data.get("airline")

                    await update.message.reply_chat_action("upload_photo")
                    await update.message.reply_text(
                        f"🎨 Generando Flyer para {destination} (${price})..."
                    )

                    # Generar Flyer (Sync wrapper)
                    from asgiref.sync import sync_to_async

                    from apps.marketing.services.flash_marketing_service import (
                        FlashMarketingService,
                    )

                    @sync_to_async
                    def create_flyer():
                        """create_flyer."""
                        service = FlashMarketingService()
                        return service.generate_flyer(destination, price, airline)

                    image_buffer = await create_flyer()

                    if image_buffer:
                        await update.message.reply_photo(
                            photo=image_buffer, caption=f"✈️ ¡Vamonos a {destination}!"
                        )
                    else:
                        await update.message.reply_text(
                            "❌ Error generando la imagen: Buffer vacío."
                        )
                else:
                    await update.message.reply_text(f"Acción desconocida: {data.get('action')}")

            except Exception as e:
                logger.error(f"Error Web App Data: {e}")
                await update.message.reply_text(f"⚠️ Error procesando datos: {str(e)}")

        async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Envía el botón para abrir la Mini App"""
            # URL pública del servidor (Debe ser HTTPS real, ngrok o hosting)
            # Como fallback local, usamos una variable de entorno o hardcode para test
            web_app_url = os.getenv("WEB_APP_URL", "https://travelhub.cc/telegram/flyer-app/")

            # Inject UID into URL (Fallback for "UID: 0" issue)
            user_id = update.effective_user.id
            separator = "&" if "?" in web_app_url else "?"
            final_url = f"{web_app_url}{separator}uid={user_id}"

            from telegram import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

            kb = [[KeyboardButton("🎨 Diseñar Flyer", web_app=WebAppInfo(url=final_url))]]
            await update.message.reply_text(
                f"👇 Pulsa el botón para Diseñar Flyer (ID: {user_id}):",
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
            )

        # ============================================================================
        # CLIENT SELF-SERVICE COMMANDS
        # ============================================================================

        @sync_to_async
        def get_cliente_by_telegram(telegram_user_id):
            """Busca un cliente registrado con ese chat_id de Telegram."""
            from apps.crm.models import Cliente

            cliente = Cliente.objects.filter(telegram_chat_id=str(telegram_user_id)).first()
            return cliente

        async def mis_reservas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Muestra las reservas activas del cliente."""
            user_id = update.effective_user.id
            cliente = await get_cliente_by_telegram(user_id)
            if not cliente:
                await update.message.reply_text(
                    "❌ No estás registrado como cliente.\n"
                    "Solicita a tu agencia que vincule tu Telegram para usar este comando."
                )
                return

            from apps.bookings.models.venta import Venta

            ventas = await sync_to_async(list)(
                Venta.objects.filter(cliente=cliente, activa=True)
                .order_by("-fecha_creacion")[:5]
                .values("id", "total", "estado", "fecha_creacion")
            )

            if not ventas:
                await update.message.reply_text("📭 No tienes reservas activas.")
                return

            msg = "📋 <b>Mis Reservas</b>\n\n"
            for v in ventas:
                fecha = v["fecha_creacion"].strftime("%d/%m/%Y") if v["fecha_creacion"] else ""
                msg += f"🔹 #{v['id']} — ${v['total']:.2f} — <b>{v['estado']}</b> — {fecha}\n"
            msg += "\nUsa /misreservas para ver de nuevo."
            await update.message.reply_text(msg, parse_mode="HTML")

        async def mi_vuelo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Muestra el estado del vuelo más reciente del cliente."""
            user_id = update.effective_user.id
            cliente = await get_cliente_by_telegram(user_id)
            if not cliente:
                await update.message.reply_text(
                    "❌ No estás registrado como cliente.\n"
                    "Solicita a tu agencia que vincule tu Telegram."
                )
                return

            from apps.bookings.models import BoletoImportado

            boleto = await sync_to_async(
                lambda: BoletoImportado.objects.filter(venta__cliente=cliente)
                .order_by("-creado_en")
                .select_related("venta")
                .first()
            )()

            if not boleto:
                await update.message.reply_text("📭 No tienes vuelos registrados.")
                return

            msg = (
                f"✈️ <b>Tu Último Vuelo</b>\n\n"
                f"📍 <b>Ruta:</b> {boleto.origen or '?'} → {boleto.destino or '?'}\n"
                f"📅 <b>Fecha:</b> {boleto.fecha_vuelo or 'Pendiente'}\n"
                f"🔖 <b>Estado:</b> {boleto.estado or 'Procesando'}\n"
                f"📋 <b>Reserva:</b> #{boleto.venta_id}\n\n"
                f"Usa /mivoucher para descargar tu boleto."
            )
            await update.message.reply_text(msg, parse_mode="HTML")

        async def mi_voucher_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Envía el voucher PDF de la reserva al cliente."""
            user_id = update.effective_user.id
            cliente = await get_cliente_by_telegram(user_id)
            if not cliente:
                await update.message.reply_text(
                    "❌ No estás registrado como cliente.\n"
                    "Solicita a tu agencia que vincule tu Telegram."
                )
                return

            from apps.bookings.models import BoletoImportado

            boleto = await sync_to_async(
                lambda: BoletoImportado.objects.filter(venta__cliente=cliente)
                .order_by("-creado_en")
                .first()
            )()

            if not boleto or not boleto.telegram_file_id:
                await update.message.reply_text("📭 No tienes vouchers disponibles todavía.")
                return

            await update.message.reply_document(
                document=boleto.telegram_file_id,
                caption=f"🎫 Voucher #{boleto.venta_id} — {boleto.origen} → {boleto.destino}",
                parse_mode="HTML",
            )

        # Registrar handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("ayuda", help_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("id", get_id))
        application.add_handler(CommandHandler("buscar", buscar_cliente))
        application.add_handler(CommandHandler("vuelo", buscar_vuelo_command))
        application.add_handler(CommandHandler("flyer", flyer_command))
        application.add_handler(CommandHandler("verboleto", ver_boleto_command))
        application.add_handler(CommandHandler("check_visa", check_visa_command))
        application.add_handler(CommandHandler("app", app_command))  # Comando para abrir Mini App

        # Cliente self-service
        application.add_handler(CommandHandler("misreservas", mis_reservas_command))
        application.add_handler(CommandHandler("mivuelo", mi_vuelo_command))
        application.add_handler(CommandHandler("mivoucher", mi_voucher_command))

        # Handler de Voz (Gemini)
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))

        # Handler de Web App Data (JSON) - Legacy support
        application.add_handler(
            MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler)
        )

        # On non command i.e message
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_natural_language)
        )

        # Run the bot
        webhook_url = options.get("webhook")
        if webhook_url:
            webhook_port = options.get("webhook_port", 8443)
            self.stdout.write(
                self.style.SUCCESS(f"Starting in WEBHOOK mode on port {webhook_port}")
            )
            application.run_webhook(
                listen="0.0.0.0",  # noqa: S104
                port=webhook_port,
                url_path=token,
                webhook_url=f"{webhook_url}{token}",
                allowed_updates=Update.ALL_TYPES,
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("Bot running in POLLING mode. Press Ctrl-C to stop.")
            )
            application.run_polling(allowed_updates=Update.ALL_TYPES)
