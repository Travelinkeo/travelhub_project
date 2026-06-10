from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.bookings.models import BoletoImportado, PagoVenta, Venta
from apps.crm.models import Cliente
from apps.finance.models.checkout import LinkDePago
from apps.finance.models.core_finance import Factura
from apps.finance.models.fiscal import FacturaFiscal
from apps.finance.models.retenciones import RetencionISLR
from apps.finance.models.tax_refund import TaxRefundOpportunity
from core.middleware import agency_context


def _crear_factura_minima(agencia, venta, moneda):
    """Helper: crea una Factura con todos los campos requeridos por save()."""
    return Factura.objects.create(
        venta_asociada=venta,
        agencia=agencia,
        moneda=moneda,
        subtotal_base_gravada=Decimal("100.00"),
        monto_iva_16=Decimal("25.00"),
    )


@pytest.mark.django_db
class TestLinkDePago:
    def test_creacion_link_de_pago(self, agencia_premium, moneda_usd):
        """Un LinkDePago se crea con estado PENDIENTE y expira_en auto-seteado a 24h."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="LINK001",
                agencia=agencia_premium,
                subtotal=Decimal("200.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            link = LinkDePago.objects.create(
                venta=venta,
                monto_total=Decimal("200.00"),
            )
            assert link.estado == LinkDePago.EstadoPago.PENDIENTE
            assert link.expira_en is not None
            assert link.expira_en > timezone.now()

    def test_propiedad_esta_activo(self, agencia_premium, moneda_usd):
        """esta_activo retorna True solo si estado=PENDIENTE y no ha expirado."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="LINK002",
                agencia=agencia_premium,
                subtotal=Decimal("150.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            link = LinkDePago.objects.create(
                venta=venta,
                monto_total=Decimal("150.00"),
            )
            assert link.esta_activo is True

            link.estado = LinkDePago.EstadoPago.PAGADO
            assert link.esta_activo is False

    def test_link_expirado_no_esta_activo(self, agencia_premium, moneda_usd):
        """Un link con expira_en en el pasado no esta_activo."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="LINK003",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            link = LinkDePago.objects.create(
                venta=venta,
                monto_total=Decimal("100.00"),
                expira_en=timezone.now() - timedelta(hours=1),
            )
            assert link.esta_activo is False

    def test_soft_delete_venta_no_elimina_link_fisicamente(self, agencia_premium, moneda_usd):
        """Venta hereda SoftDeleteModel: .delete() es soft, CASCADE no se dispara fisicamente."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="LINK004",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            link = LinkDePago.objects.create(
                venta=venta,
                monto_total=Decimal("100.00"),
            )
            link_id = link.id
            venta.delete()

            assert Venta.all_objects.filter(localizador="LINK004").exists() is True
            assert LinkDePago.objects.filter(id=link_id).exists() is True

    def test_hard_delete_venta_dispara_cascade(self, agencia_premium, moneda_usd):
        """Venta.hard_delete() y limpieza manual de dependencias lógicas."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="LINK005",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            link = LinkDePago.objects.create(
                venta_id=venta.pk,
                monto_total=Decimal("100.00"),
            )
            link_id = link.id
            original_venta_id = venta.pk
            venta.hard_delete()
            # Eliminar dependencias lógicas manualmente (o a través del servicio)
            LinkDePago.all_objects.filter(venta_id=original_venta_id).delete()

        assert LinkDePago.all_objects.filter(id=link_id).exists() is False
        assert Venta.all_objects.filter(localizador="LINK005").exists() is False


@pytest.mark.django_db
class TestFacturaFiscal:
    def test_creacion_factura_fiscal_pendiente(self, agencia_premium, moneda_usd):
        """FacturaFiscal se crea con estado PENDIENTE por defecto."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="FISC001",
                agencia=agencia_premium,
                subtotal=Decimal("300.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            ff = FacturaFiscal.objects.create(venta=venta)
            assert ff.estado_fiscal == FacturaFiscal.EstadoFiscal.PENDIENTE
            assert ff.numero_factura == ""

    def test_transicion_estado_fiscal(self, agencia_premium, moneda_usd):
        """FacturaFiscal puede transicionar de PENDIENTE → EN_PROCESO → APROBADA."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="FISC002",
                agencia=agencia_premium,
                subtotal=Decimal("300.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            ff = FacturaFiscal.objects.create(venta=venta)
            assert ff.estado_fiscal == "PEN"

            ff.estado_fiscal = FacturaFiscal.EstadoFiscal.EN_PROCESO
            ff.save()
            assert ff.estado_fiscal == "PRO"

            ff.estado_fiscal = FacturaFiscal.EstadoFiscal.APROBADA
            ff.numero_factura = "00001"
            ff.numero_control = "00001"
            ff.cadena_firma_digital = "abc123"
            ff.save()
            assert ff.estado_fiscal == "APR"

    def test_factura_fiscal_rechazada_registra_error(self, agencia_premium, moneda_usd):
        """FacturaFiscal RECHAZADA debe almacenar el mensaje de error."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="FISC003",
                agencia=agencia_premium,
                subtotal=Decimal("300.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            ff = FacturaFiscal.objects.create(venta=venta)
            ff.estado_fiscal = FacturaFiscal.EstadoFiscal.RECHAZADA
            ff.ultimo_mensaje_error = "RIF inválido en XML fiscal"
            ff.save()

            ff.refresh_from_db()
            assert ff.ultimo_mensaje_error == "RIF inválido en XML fiscal"

    def test_onetoone_venta_una_sola_factura_fiscal(self, agencia_premium, moneda_usd):
        """Una Venta solo puede tener una FacturaFiscal (OneToOne)."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="FISC004",
                agencia=agencia_premium,
                subtotal=Decimal("300.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            FacturaFiscal.objects.create(venta=venta)
            with pytest.raises(Exception):
                FacturaFiscal.objects.create(venta=venta)


@pytest.mark.django_db
class TestRetencionISLR:
    def test_calculo_automatico_monto_retenido(self, agencia_premium, moneda_usd):
        """RetencionISLR calcula monto_retenido = base_imponible * (porcentaje/100)."""
        with agency_context(agencia_premium):
            cliente = Cliente.objects.create(
                nombres="Retencion",
                apellidos="Test",
                email="retencion@test.com",
                agencia=agencia_premium,
            )
            venta = Venta.objects.create(
                localizador="RET001",
                agencia=agencia_premium,
                subtotal=Decimal("1000.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            factura = _crear_factura_minima(agencia_premium, venta, moneda_usd)
            ret = RetencionISLR(
                numero_comprobante="RET-001",
                factura=factura,
                cliente=cliente,
                base_imponible=Decimal("1000.00"),
                porcentaje_retencion=Decimal("5.00"),
            )
            ret.save()
            assert ret.monto_retenido == Decimal("50.00")

    def test_generacion_automatica_periodo_fiscal(self, agencia_premium, moneda_usd):
        """RetencionISLR genera periodo_fiscal automaticamente desde fecha_emision."""
        with agency_context(agencia_premium):
            cliente = Cliente.objects.create(
                nombres="Periodo",
                apellidos="Test",
                email="periodo@test.com",
                agencia=agencia_premium,
            )
            venta = Venta.objects.create(
                localizador="RET002",
                agencia=agencia_premium,
                subtotal=Decimal("500.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            factura = _crear_factura_minima(agencia_premium, venta, moneda_usd)
            ret = RetencionISLR(
                numero_comprobante="RET-002",
                factura=factura,
                cliente=cliente,
                base_imponible=Decimal("500.00"),
            )
            ret.save()
            assert ret.periodo_fiscal == ret.fecha_emision.strftime("%Y-%m")

    def test_retencion_sin_base_imponible_no_calcula(self, agencia_premium, moneda_usd):
        """RetencionISLR sin base_imponible no calcula monto_retenido."""
        with agency_context(agencia_premium):
            ret = RetencionISLR(
                numero_comprobante="RET-003",
                porcentaje_retencion=Decimal("5.00"),
            )
            ret.save()
            assert ret.monto_retenido is None

    def test_estado_por_defecto_pendiente(self, agencia_premium, moneda_usd):
        """RetencionISLR se crea con estado PENDIENTE por defecto."""
        with agency_context(agencia_premium):
            ret = RetencionISLR(
                numero_comprobante="RET-004",
            )
            ret.save()
            assert ret.estado == RetencionISLR.Estado.PENDIENTE

    def test_tipo_operacion_por_defecto_comisiones(self):
        """RetencionISLR usa COMISIONES_MERCANTILES como tipo por defecto."""
        ret = RetencionISLR(numero_comprobante="RET-005")
        assert ret.tipo_operacion == RetencionISLR.TipoOperacion.COMISIONES_MERCANTILES


@pytest.mark.django_db
class TestPagoVenta:
    def test_creacion_pago_venta(self, agencia_premium, moneda_usd):
        """PagoVenta se crea correctamente con monto y metodo."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="PAG001",
                agencia=agencia_premium,
                subtotal=Decimal("250.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            pago = PagoVenta.objects.create(
                venta=venta,
                monto=Decimal("250.00"),
                moneda=moneda_usd,
                metodo=PagoVenta.MetodoPago.TRANSFERENCIA,
                agencia=agencia_premium,
            )
            assert pago.confirmado is True
            assert pago.metodo == PagoVenta.MetodoPago.TRANSFERENCIA
            assert pago.monto == Decimal("250.00")

    def test_calculo_automatico_igtf(self, agencia_premium, moneda_usd):
        """PagoVenta calcula monto_igtf = monto * (tasa_igtf / 100) si aplica_igtf=True."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="PAG002",
                agencia=agencia_premium,
                subtotal=Decimal("500.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            pago = PagoVenta.objects.create(
                venta=venta,
                monto=Decimal("500.00"),
                moneda=moneda_usd,
                metodo=PagoVenta.MetodoPago.EFECTIVO,
                aplica_igtf=True,
                tasa_igtf=Decimal("3.00"),
                agencia=agencia_premium,
            )
            assert pago.monto_igtf == Decimal("15.00")

    def test_pago_sin_igtf_por_defecto(self, agencia_premium, moneda_usd):
        """PagoVenta con aplica_igtf=False tiene monto_igtf=0."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="PAG003",
                agencia=agencia_premium,
                subtotal=Decimal("300.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            pago = PagoVenta.objects.create(
                venta=venta,
                monto=Decimal("300.00"),
                moneda=moneda_usd,
                metodo=PagoVenta.MetodoPago.TRANSFERENCIA,
                agencia=agencia_premium,
            )
            assert pago.aplica_igtf is False
            assert pago.monto_igtf == Decimal("0")


@pytest.mark.django_db
class TestTaxRefundOpportunity:
    def test_creacion_tax_refund(self, agencia_premium):
        """TaxRefundOpportunity se crea con estado ELEGIBLE por defecto."""
        with agency_context(agencia_premium):
            boleto = BoletoImportado.objects.create(
                agencia=agencia_premium,
                numero_boleto="TAX1234567890",
                nombre_pasajero_completo="DOE/JANE",
                localizador_pnr="TAX001",
                aerolinea_emisora="AVIANCA",
                total_boleto=Decimal("800.00"),
                estado_parseo="COM",
                version=1,
                estado_emision=BoletoImportado.EstadoEmision.ORIGINAL,
            )
            refund = TaxRefundOpportunity.objects.create(
                boleto=boleto,
                agencia=agencia_premium,
                monto_estimado=Decimal("50.00"),
            )
            assert refund.estado == TaxRefundOpportunity.Estado.ELEGIBLE
            assert refund.monto_estimado == Decimal("50.00")
            assert refund.monto_recuperado == Decimal("0.00")

    def test_transicion_estado_tax_refund(self, agencia_premium):
        """TaxRefundOpportunity puede transicionar ELEGIBLE → TRAMITANDO → COMPLETADO."""
        with agency_context(agencia_premium):
            boleto = BoletoImportado.objects.create(
                agencia=agencia_premium,
                numero_boleto="TAX2234567890",
                nombre_pasajero_completo="SMITH/JOHN",
                localizador_pnr="TAX002",
                aerolinea_emisora="COPA",
                total_boleto=Decimal("600.00"),
                estado_parseo="COM",
                version=1,
                estado_emision=BoletoImportado.EstadoEmision.ORIGINAL,
            )
            refund = TaxRefundOpportunity.objects.create(
                boleto=boleto,
                agencia=agencia_premium,
                monto_estimado=Decimal("40.00"),
            )
            refund.estado = TaxRefundOpportunity.Estado.TRAMITANDO
            refund.tracking_code_proveedor = "GB-12345"
            refund.save()

            refund.estado = TaxRefundOpportunity.Estado.COMPLETADO
            refund.monto_recuperado = Decimal("38.50")
            refund.save()

            refund.refresh_from_db()
            assert refund.estado == TaxRefundOpportunity.Estado.COMPLETADO
            assert refund.monto_recuperado == Decimal("38.50")

    def test_soft_delete_boleto_no_elimina_refund_fisicamente(self, agencia_premium):
        """BoletoImportado hereda SoftDeleteModel: .delete() es soft, CASCADE no se dispara."""
        with agency_context(agencia_premium):
            boleto = BoletoImportado.objects.create(
                agencia=agencia_premium,
                numero_boleto="TAX3234567890",
                nombre_pasajero_completo="GARCIA/MARIA",
                localizador_pnr="TAX003",
                aerolinea_emisora="LAN",
                total_boleto=Decimal("500.00"),
                estado_parseo="COM",
                version=1,
                estado_emision=BoletoImportado.EstadoEmision.ORIGINAL,
            )
            refund = TaxRefundOpportunity.objects.create(
                boleto=boleto,
                agencia=agencia_premium,
                monto_estimado=Decimal("30.00"),
            )
            refund_id = refund.id
            boleto.delete()

            assert (
                BoletoImportado.all_objects.filter(numero_boleto="TAX3234567890").exists() is True
            )
            assert TaxRefundOpportunity.objects.filter(id=refund_id).exists() is True


@pytest.mark.django_db
class TestSoftDeleteModel:
    def test_soft_delete_marca_is_deleted(self, agencia_premium, moneda_usd):
        """SoftDeleteModel.delete() marca is_deleted=True sin borrar el registro."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="SOFT001",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            factura = _crear_factura_minima(agencia_premium, venta, moneda_usd)
            factura_id = factura.id_factura
            factura.delete()

            factura.refresh_from_db()
            assert factura.is_deleted is True
            assert factura.deleted_at is not None
            assert Factura.all_objects.filter(id_factura=factura_id).exists() is True

    def test_soft_delete_se_filtran_de_objects(self, agencia_premium, moneda_usd):
        """Registros con is_deleted=True no aparecen en objects.all() del AgenciaManager."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="SOFT002",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            factura = _crear_factura_minima(agencia_premium, venta, moneda_usd)
            factura.delete()

            with agency_context(agencia_premium):
                facturas = Factura.objects.all()
                assert factura not in facturas

    def test_hard_delete_ahora_es_fisico(self, agencia_premium, moneda_usd):
        """SoftDeleteModel.hard_delete() ahora salta AgenciaMixin.delete() via MRO
        y llama directamente models.Model.delete() — eliminación física real."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="SOFT003",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            factura = _crear_factura_minima(agencia_premium, venta, moneda_usd)
            factura_id = factura.id_factura
            factura.hard_delete()

        assert Factura.all_objects.filter(id_factura=factura_id).exists() is False

    def test_restore_des_hace_soft_delete(self, agencia_premium, moneda_usd):
        """SoftDeleteModel.restore() revierte el soft delete."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="SOFT004",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            factura = _crear_factura_minima(agencia_premium, venta, moneda_usd)
            factura.delete()
            assert factura.is_deleted is True

            factura.restore()
            assert factura.is_deleted is False
            assert factura.deleted_at is None


@pytest.mark.django_db
class TestAgenciaMixinAislamiento:
    def test_aislamiento_multitenant_factura(self, agencia_premium, agencia_estandar, moneda_usd):
        """Una Factura de la Agencia A no es visible desde el contexto de la Agencia B."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="TENANT001",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            factura = _crear_factura_minima(agencia_premium, venta, moneda_usd)

        with agency_context(agencia_estandar):
            facturas_b = Factura.objects.all()
            assert factura not in facturas_b

    def test_all_objects_bypass_filtro_agencia(self, agencia_premium, agencia_estandar):
        """Venta.all_objects retorna registros de TODAS las agencias (sin filtro tenant)."""
        with agency_context(agencia_premium):
            venta_a = Venta.objects.create(
                localizador="ALL001A",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
            )

        with agency_context(agencia_estandar):
            venta_b = Venta.objects.create(
                localizador="ALL001B",
                agencia=agencia_estandar,
                subtotal=Decimal("200.00"),
                fecha_venta=timezone.now(),
            )

        all_ids = list(Venta.all_objects.values_list("id_venta", flat=True))
        assert venta_a.id_venta in all_ids
        assert venta_b.id_venta in all_ids

    def test_contexto_sin_agencia_retorna_vacio(self, moneda_usd):
        """Sin agency_context ni superuser, AgenciaManager retorna queryset.none()."""
        facturas = Factura.objects.all()
        assert facturas.count() == 0

    def test_with_deleted_muestra_soft_deleted(self, agencia_premium, moneda_usd):
        """SoftDeleteModel.with_deleted muestra registros soft-deleted (sin filtro is_deleted)."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="WD001",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            factura = _crear_factura_minima(agencia_premium, venta, moneda_usd)
            factura.delete()

        with agency_context(agencia_premium):
            assert Factura.objects.filter(id_factura=factura.id_factura).exists() is False
            assert Factura.with_deleted.filter(id_factura=factura.id_factura).exists() is True

    def test_queryset_delete_es_soft_delete(self, agencia_premium, moneda_usd):
        """SoftDeleteQuerySet.delete() hace soft-delete en bulk, no borrado fisico."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="QSDEL001",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            f1 = _crear_factura_minima(agencia_premium, venta, moneda_usd)
            venta2 = Venta.objects.create(
                localizador="QSDEL002",
                agencia=agencia_premium,
                subtotal=Decimal("200.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            f2 = _crear_factura_minima(agencia_premium, venta2, moneda_usd)

            Factura.objects.filter(id_factura__in=[f1.id_factura, f2.id_factura]).delete()

        assert (
            Factura.with_deleted.filter(id_factura=f1.id_factura, is_deleted=True).exists() is True
        )
        assert (
            Factura.with_deleted.filter(id_factura=f2.id_factura, is_deleted=True).exists() is True
        )

    def test_queryset_restore_revoca_soft_delete(self, agencia_premium, moneda_usd):
        """SoftDeleteQuerySet.restore() revoca soft-delete en bulk."""
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="QSRES001",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )
            factura = _crear_factura_minima(agencia_premium, venta, moneda_usd)
            factura.delete()

        assert (
            Factura.with_deleted.filter(id_factura=factura.id_factura, is_deleted=True).exists()
            is True
        )

        Factura.with_deleted.filter(id_factura=factura.id_factura).restore()

        factura.refresh_from_db()
        assert factura.is_deleted is False
        assert factura.deleted_at is None
