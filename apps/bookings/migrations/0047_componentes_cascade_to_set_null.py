# Generated for R1 hardening (CASCADE → SET_NULL) on 2026-07-13.

"""Cambiar on_delete=CASCADE a on_delete=SET_NULL en todos los FKs venta/item_venta
de los modelos de componentes bookings.

Razon: si una Venta se borra físicamente (hard_delete, no soft-delete), los
componentes asociados (alojamientos, traslados, actividades, segmentos de vuelo,
alquileres, eventos, circuitos, paquetes aéreos, cruceros, servicios
adicionales) deben preservarse como huérfanos para auditoría contable/forense.

Soft-delete (default) no dispara on_delete; el CASCADE solo se activaba en
hard_delete accidental o gestionado, perdiendo histórico de costos.
"""

from django.db import migrations, models


def _fk(to, related_name, verbose_name=None):
    # _fk:  fk. Args: según implementación. Returns: según implementación.
    field_kwargs = {
        "blank": True,
        "null": True,
        "on_delete": models.SET_NULL,
        "related_name": related_name,
        "to": to,
    }
    if verbose_name:
        field_kwargs["verbose_name"] = verbose_name
    return models.ForeignKey(**field_kwargs)


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("bookings", "0046_alter_ventaparsemetadata_options_and_more"),
    ]

    operations = [
        # AlojamientoReserva
        migrations.AlterField(
            model_name="alojamientoreserva",
            name="venta",
            field=_fk("bookings.venta", "alojamientos", "Venta"),
        ),
        migrations.AlterField(
            model_name="alojamientoreserva",
            name="item_venta",
            field=_fk("bookings.itemventa", "alojamientos_reserva", "Item de Venta Asociado"),
        ),
        # TrasladoServicio
        migrations.AlterField(
            model_name="trasladoservicio",
            name="venta",
            field=_fk("bookings.venta", "traslados", "Venta"),
        ),
        migrations.AlterField(
            model_name="trasladoservicio",
            name="item_venta",
            field=_fk("bookings.itemventa", "traslados_reserva", "Item de Venta Asociado"),
        ),
        # ActividadServicio
        migrations.AlterField(
            model_name="actividadservicio",
            name="venta",
            field=_fk("bookings.venta", "actividades", "Venta"),
        ),
        migrations.AlterField(
            model_name="actividadservicio",
            name="item_venta",
            field=_fk("bookings.itemventa", "actividades_reserva", "Item de Venta Asociado"),
        ),
        # SegmentoVuelo
        migrations.AlterField(
            model_name="segmentovuelo",
            name="venta",
            field=_fk("bookings.venta", "segmentos_vuelo", "Venta"),
        ),
        migrations.AlterField(
            model_name="segmentovuelo",
            name="item_venta",
            field=_fk("bookings.itemventa", "segmentos_reserva", "Item de Venta Asociado"),
        ),
        # AlquilerAutoReserva
        migrations.AlterField(
            model_name="alquilerautoreserva",
            name="venta",
            field=_fk("bookings.venta", "alquileres_autos", "Venta"),
        ),
        migrations.AlterField(
            model_name="alquilerautoreserva",
            name="item_venta",
            field=_fk("bookings.itemventa", "alquileres_reserva", "Item de Venta Asociado"),
        ),
        # EventoServicio
        migrations.AlterField(
            model_name="eventoservicio",
            name="venta",
            field=_fk("bookings.venta", "eventos_servicios", "Venta"),
        ),
        migrations.AlterField(
            model_name="eventoservicio",
            name="item_venta",
            field=_fk("bookings.itemventa", "eventos_reserva", "Item de Venta Asociado"),
        ),
        # CircuitoTuristico
        migrations.AlterField(
            model_name="circuitoturistico",
            name="venta",
            field=_fk("bookings.venta", "circuitos_turisticos", "Venta"),
        ),
        migrations.AlterField(
            model_name="circuitoturistico",
            name="item_venta",
            field=_fk("bookings.itemventa", "circuitos_reserva", "Item de Venta Asociado"),
        ),
        # CircuitoDia (su FK 'circuito' también era CASCADE → SET_NULL)
        migrations.AlterField(
            model_name="circuitodia",
            name="circuito",
            field=_fk("bookings.circuitoturistico", "dias", "Circuito"),
        ),
        # PaqueteAereo
        migrations.AlterField(
            model_name="paqueteaereo",
            name="venta",
            field=_fk("bookings.venta", "paquetes_aereos", "Venta"),
        ),
        migrations.AlterField(
            model_name="paqueteaereo",
            name="item_venta",
            field=_fk("bookings.itemventa", "paquetes_reserva", "Item de Venta Asociado"),
        ),
        # CruceroReserva
        migrations.AlterField(
            model_name="cruceroreserva",
            name="venta",
            field=_fk("bookings.venta", "cruceros", "Venta"),
        ),
        migrations.AlterField(
            model_name="cruceroreserva",
            name="item_venta",
            field=_fk("bookings.itemventa", "cruceros_reserva", "Item de Venta Asociado"),
        ),
        # ServicioAdicionalDetalle
        migrations.AlterField(
            model_name="servicioadicionaldetalle",
            name="venta",
            field=_fk("bookings.venta", "servicios_adicionales", "Venta"),
        ),
        migrations.AlterField(
            model_name="servicioadicionaldetalle",
            name="item_venta",
            field=_fk("bookings.itemventa", "detalles_adicionales", "Item de Venta Asociado"),
        ),
    ]
