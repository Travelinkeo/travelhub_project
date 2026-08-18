from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.crm.models import Cliente, Pasajero
from apps.crm.views.pasajeros_views import CRMBaseMixin


class PasajeroConvertToClienteView(CRMBaseMixin, View):
    """
    Convierte un Pasajero a Cliente o actualiza/sincroniza los datos del Cliente existente.
    """

    def post(self, request, pk, *args, **kwargs):
        """post."""
        pasajero = get_object_or_404(Pasajero, pk=pk)

        # 1. Buscar si ya tiene un cliente asociado directamente
        cliente = pasajero.clientes_asociados.filter(is_deleted=False).first()

        # 2. Si no tiene vínculo directo, buscar si ya existe un cliente con el mismo documento
        if not cliente:
            q_doc = Q()
            if pasajero.cedula_identidad:
                q_doc |= Q(cedula_identidad__iexact=pasajero.cedula_identidad)
            if pasajero.numero_pasaporte:
                q_doc |= Q(numero_pasaporte__iexact=pasajero.numero_pasaporte)
            if pasajero.documento_hash:
                q_doc |= Q(documento_hash=pasajero.documento_hash)

            if q_doc:
                cliente = Cliente.objects.filter(agencia=pasajero.agencia).filter(q_doc).first()

        # CASO A: El cliente ya existe -> ACTUALIZAR / SINCRONIZAR SUS DATOS
        if cliente:
            if pasajero.nombres:
                cliente.nombres = pasajero.nombres
            if pasajero.apellidos:
                cliente.apellidos = pasajero.apellidos
            if pasajero.numero_pasaporte:
                cliente.numero_pasaporte = pasajero.numero_pasaporte
            if pasajero.cedula_identidad:
                cliente.cedula_identidad = pasajero.cedula_identidad
            if pasajero.fecha_nacimiento:
                cliente.fecha_nacimiento = pasajero.fecha_nacimiento
            if pasajero.nacionalidad:
                cliente.nacionalidad = pasajero.nacionalidad
            if pasajero.email and not cliente.email:
                cliente.email = pasajero.email
            if pasajero.telefono and not cliente.telefono_principal:
                cliente.telefono_principal = pasajero.telefono
            if pasajero.foto_perfil:
                cliente.foto_perfil = pasajero.foto_perfil

            cliente.save()
            if pasajero not in cliente.pasajeros.all():
                cliente.pasajeros.add(pasajero)

            messages.success(
                request,
                f"Los datos del Cliente #{cliente.pk} ({cliente.get_nombre_completo()}) fueron actualizados y sincronizados desde el pasaporte exitosamente.",
            )
            return redirect("crm:cliente_detail", pk=cliente.pk)

        # CASO B: No existe -> CREAR NUEVO CLIENTE
        try:
            nuevo_cliente = Cliente.objects.create(
                nombres=pasajero.nombres,
                apellidos=pasajero.apellidos or "",
                numero_pasaporte=pasajero.numero_pasaporte,
                cedula_identidad=pasajero.cedula_identidad,
                fecha_nacimiento=pasajero.fecha_nacimiento,
                nacionalidad=pasajero.nacionalidad,
                email=pasajero.email or "",
                telefono_principal=pasajero.telefono or "",
                foto_perfil=pasajero.foto_perfil,
                agencia=pasajero.agencia,
                tipo_cliente="IND",
            )
            nuevo_cliente.pasajeros.add(pasajero)
            messages.success(
                request,
                f"El pasajero {pasajero.get_nombre_completo()} fue convertido a Cliente exitosamente.",
            )
            return redirect("crm:cliente_detail", pk=nuevo_cliente.pk)
        except IntegrityError:
            messages.error(
                request,
                f"Error: Ya existe un Cliente registrado con este documento ({pasajero.cedula_identidad or pasajero.numero_pasaporte}).",
            )
            return redirect("crm:pasajero_detail", pk=pk)
        except Exception as e:
            messages.error(
                request,
                f"No se pudo crear el cliente: {str(e)}",
            )
            return redirect("crm:pasajero_detail", pk=pk)


class PasajeroSearchView(CRMBaseMixin, View):
    """PasajeroSearchView: Búsqueda dinámica y flexible de pasajeros."""

    def get(self, request, *args, **kwargs):
        """get."""
        q = request.GET.get("q", "").strip()
        cliente_id = request.GET.get("cliente_id")

        if len(q) < 2:
            return HttpResponse(
                '<p class="text-text-muted text-sm text-center py-4">Escribe al menos 2 letras para buscar...</p>'
            )

        qs = Pasajero.objects.all()

        # Búsqueda por múltiples palabras (tokens: ej. 'Josue Rosales Moreno')
        words = q.split()
        for word in words:
            qs = qs.filter(
                Q(nombres__icontains=word)
                | Q(apellidos__icontains=word)
                | Q(numero_pasaporte__icontains=word)
                | Q(cedula_identidad__icontains=word)
            )

        if cliente_id:
            qs = qs.exclude(clientes_asociados__pk=cliente_id)

        pasajeros = qs.order_by("apellidos", "nombres")[:15]

        return render(
            request,
            "crm/partials/pasajero_search_results.html",
            {"pasajeros": pasajeros, "cliente_id": cliente_id},
        )


class VincularPasajeroActionView(CRMBaseMixin, View):
    """VincularPasajeroActionView."""

    def post(self, request, pk, *args, **kwargs):
        """post."""
        cliente = get_object_or_404(Cliente, pk=pk)
        pasajero_id = request.POST.get("pasajero_id")
        if pasajero_id:
            pasajero = get_object_or_404(Pasajero, pk=pasajero_id)
            cliente.pasajeros.add(pasajero)
            messages.success(request, f"Pasajero {pasajero.get_nombre_completo()} vinculado.")
        return HttpResponse(status=204, headers={"HX-Refresh": "true"})
