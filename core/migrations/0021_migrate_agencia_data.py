from django.db import migrations

def migrate_agencia_data(apps, schema_editor):
    Agencia = apps.get_model('core', 'Agencia')
    AgenciaBranding = apps.get_model('core', 'AgenciaBranding')
    AgenciaConfiguracion = apps.get_model('core', 'AgenciaConfiguracion')

    for agencia in Agencia.objects.all():
        # Crear Branding
        branding = AgenciaBranding.objects.create(
            agencia=agencia,
            logo=agencia.logo,
            logo_light=agencia.logo_light,
            logo_dark=agencia.logo_dark,
            logo_secundario=agencia.logo_secundario,
            logo_base64=agencia.logo_base64,
            logo_pdf_base64=agencia.logo_pdf_base64,
            logo_pdf_dark_base64=agencia.logo_pdf_dark_base64,
            color_primario=agencia.color_primario,
            color_secundario=agencia.color_secundario,
            color_amadeus=agencia.color_amadeus,
            color_kiu=agencia.color_kiu,
            color_copa=agencia.color_copa,
            color_tk_connect=agencia.color_tk_connect,
            color_wingo=agencia.color_wingo,
            color_travelport=agencia.color_travelport,
            logo_telegram_id=agencia.logo_telegram_id,
            logo_telegram_url=agencia.logo_telegram_url,
            eslogan=agencia.eslogan,
            pie_pagina=agencia.pie_pagina,
            terminos_condiciones=agencia.terminos_condiciones,
            ui_theme=agencia.ui_theme,
            plantilla_boletos=agencia.plantilla_boletos,
            plantilla_vouchers=agencia.plantilla_vouchers,
            plantilla_facturas=agencia.plantilla_facturas,
        )
        agencia.branding = branding

        # Crear Configuracion
        configuracion = AgenciaConfiguracion.objects.create(
            agencia=agencia,
            moneda_principal=agencia.moneda_principal,
            zona_horaria=agencia.zona_horaria,
            idioma=agencia.idioma,
            configuracion_correo=agencia.configuracion_correo,
            configuracion_api=agencia.configuracion_api,
            configuracion_contable=agencia.configuracion_contable,
            correo_emisiones=agencia.correo_emisiones,
            password_app_correo=agencia.password_app_correo,
            telegram_bot_token=agencia.telegram_bot_token,
            telegram_chat_id=agencia.telegram_chat_id,
            email_monitor_user=agencia.email_monitor_user,
            email_monitor_password=agencia.email_monitor_password,
            email_monitor_active=agencia.email_monitor_active,
            email_monitor_last_check=agencia.email_monitor_last_check,
            imprenta_digital_nombre=agencia.imprenta_digital_nombre,
            imprenta_digital_rif=agencia.imprenta_digital_rif,
            imprenta_digital_providencia=agencia.imprenta_digital_providencia,
            es_sujeto_pasivo_especial=agencia.es_sujeto_pasivo_especial,
            esta_inscrita_rtn=agencia.esta_inscrita_rtn,
            plan=agencia.plan,
            limite_mensual_boletos=agencia.limite_mensual_boletos,
            limite_usuarios=agencia.limite_usuarios,
            limite_ventas_mes=agencia.limite_ventas_mes,
            ventas_mes_actual=agencia.ventas_mes_actual,
            plan_status=agencia.plan_status,
            subscription_end_date=agencia.subscription_end_date,
            fecha_inicio_plan=agencia.fecha_inicio_plan,
            fecha_fin_trial=agencia.fecha_fin_trial,
            stripe_customer_id=agencia.stripe_customer_id,
            stripe_subscription_id=agencia.stripe_subscription_id,
            subdominio_slug=agencia.subdominio_slug,
            es_demo=agencia.es_demo,
            bi_insights=agencia.bi_insights,
        )
        agencia.configuracion = configuracion
        agencia.save()

def reverse_migrate_agencia_data(apps, schema_editor):
    pass # No es necesario revertir para este caso, o se puede implementar si se desea

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_agenciabranding_agencia_branding_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_agencia_data, reverse_migrate_agencia_data),
    ]
