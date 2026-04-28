

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
import json
import logging
import asyncio
from asgiref.sync import sync_to_async, async_to_sync
from django.conf import settings

logger = logging.getLogger(__name__)

@xframe_options_exempt
def flyer_mini_app_view(request):
    """
    Renderiza la Mini App de Telegram para diseñar Flyers.
    El decorador @xframe_options_exempt es necesario para permitir
    que Telegram cargue la página dentro de su iframe/webview web.
    """
    return render(request, 'telegram/flyer_app.html')

@csrf_exempt
def generate_flyer_api(request):
    """
    API endpoint para generar flyers desde la Mini App vía AJAX/Fetch.
    Recibe JSON: {user_id, destination, price, airline}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        destination = data.get('destination')
        price = data.get('price')
        airline = data.get('airline')
        
        if not user_id or not destination or not price:
             return JsonResponse({'error': 'Faltan datos requeridos'}, status=400)
             
        # Resolver Agencia y Logo (SaaS)
        from core.models.agencia import UsuarioAgencia
        agency_logo_path = None
        try:
            # Buscar usuario de agencia con este ID de Telegram
            usuario_agencia = UsuarioAgencia.objects.filter(telegram_chat_id=str(user_id)).first()
            if usuario_agencia:
                agencia = usuario_agencia.agencia
                # Priorizar logo oscuro para flyers (Estética Obsidian)
                if agencia.logo_dark:
                    agency_logo_path = agencia.logo_dark.path
                elif agencia.logo:
                    agency_logo_path = agencia.logo.path
        except Exception as e:
            logger.error(f"Error resolviendo logo de agencia: {e}")

        # Generar Flyer
        from core.services.flash_marketing_service import FlashMarketingService
        service = FlashMarketingService()
        image_buffer = service.generate_flyer(destination, price, airline, agency_logo_path=agency_logo_path)
        
        if not image_buffer:
             return JsonResponse({'error': 'Error generando imagen'}, status=500)
             
        # Enviar resultado a Telegram
        # Usamos asyncio.run o async_to_sync para llamar al bot async
        async def send_photo():
            from telegram import Bot
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            caption = (
                    f"🔥 **¡OFERTA FLASH: {destination.upper()}!** 🔥\n\n"
                    f"✈️ Vuela desde **{price}**\n"
                    f"{f'🏢 Con {airline}' if airline else ''}\n\n"
                    f"📲 Reserva YA. Cupos limitados.\n"
                    f"#Oferta #Viajes #TravelHub #{destination}"
                )
            await bot.send_photo(
                chat_id=user_id,
                photo=image_buffer,
                caption=caption,
                parse_mode='Markdown'
            )
            
        async_to_sync(send_photo)()
        
        return JsonResponse({'status': 'ok', 'message': 'Flyer enviado al chat'})

    except Exception as e:
        logger.error(f"Error en generate_flyer_api: {e}")
        return JsonResponse({'error': str(e)}, status=500)
