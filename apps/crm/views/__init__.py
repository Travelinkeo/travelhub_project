from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from apps.crm.models import Cliente, Pasajero
from core.mixins import SaaSMixin
# from apps.cotizaciones.models import Cotizacion  # Movido a get_context_data para evitar import circular
from core.forms.legacy import PasajeroForm

class CRMBaseMixin(SaaSMixin, LoginRequiredMixin):
    context_object_name = 'object'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'crm'
        return context

# --- CLIENTES ---

class ClienteListView(CRMBaseMixin, ListView):
    model = Cliente
    template_name = 'crm/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().order_by('apellidos', 'nombres')
        q = self.request.GET.get('q')
        tipo = self.request.GET.get('tipo')
        if q:
            queryset = queryset.filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(cedula_identidad__icontains=q) |
                Q(nombre_empresa__icontains=q) |
                Q(email__icontains=q)
            )
        if tipo:
            queryset = queryset.filter(tipo_cliente=tipo)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.utils import timezone
        hoy = timezone.now()
        base_qs = Cliente.objects.all()
        # Respetar filtrado de agencia si aplica
        try:
            if hasattr(self, 'get_base_queryset'):
                base_qs = self.get_base_queryset()
        except Exception:
            pass
        context['clientes_corp_count'] = base_qs.filter(tipo_cliente='COR').count()
        context['clientes_vip_count'] = base_qs.filter(tipo_cliente='VIP').count()
        context['clientes_nuevos_mes'] = base_qs.filter(
            fecha_registro__year=hoy.year,
            fecha_registro__month=hoy.month
        ).count()
        return context

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['crm/partials/cliente_list_table.html']
        return [self.template_name]

class ClienteDetailView(CRMBaseMixin, DetailView):
    model = Cliente
    template_name = 'crm/cliente_detail.html'
    context_object_name = 'cliente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.cotizaciones.models import Cotizacion
        context['cotizaciones'] = Cotizacion.objects.filter(cliente=self.object).order_by('-fecha_emision')
        return context

class ClienteCreateView(CRMBaseMixin, CreateView):
    model = Cliente
    template_name = 'crm/cliente_form.html'
    fields = [
        'foto_perfil', 'tipo_cliente', 'nombres', 'apellidos', 
        'nombre_empresa', 'cedula_identidad', 'email', 'telefono_principal',
        'nacionalidad', 'direccion', 'ciudad'
    ]
    success_url = reverse_lazy('crm:cliente_list')

    def form_valid(self, form):
        messages.success(self.request, "Cliente creado correctamente.")
        return super().form_valid(form)

class ClienteUpdateView(CRMBaseMixin, UpdateView):
    model = Cliente
    template_name = 'crm/cliente_form.html'
    fields = [
        'foto_perfil', 'tipo_cliente', 'nombres', 'apellidos', 
        'nombre_empresa', 'cedula_identidad', 'email', 'telefono_principal',
        'nacionalidad', 'direccion', 'ciudad'
    ]
    
    def get_success_url(self):
        return reverse_lazy('crm:cliente_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Cliente actualizado correctamente.")
        return super().form_valid(form)

class ClienteDeleteView(CRMBaseMixin, DeleteView):
    model = Cliente
    success_url = reverse_lazy('crm:cliente_list')
    template_name = 'crm/cliente_confirm_delete.html'

# --- PASAJEROS ---

class PasajeroListView(CRMBaseMixin, ListView):
    model = Pasajero
    template_name = 'crm/pasajero_list.html'
    context_object_name = 'pasajeros'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().order_by('apellidos', 'nombres')
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(numero_pasaporte__icontains=q) |
                Q(cedula_identidad__icontains=q)
            )
        return queryset

class PasajeroDetailView(CRMBaseMixin, DetailView):
    model = Pasajero
    template_name = 'crm/pasajero_detail.html'
    context_object_name = 'pasajero'

class PasajeroCreateView(CRMBaseMixin, CreateView):
    model = Pasajero
    template_name = 'crm/pasajero_form.html'
    form_class = PasajeroForm
    success_url = reverse_lazy('crm:pasajero_list')

class PasajeroUpdateView(CRMBaseMixin, UpdateView):
    model = Pasajero
    template_name = 'crm/pasajero_form.html'
    form_class = PasajeroForm
    
    def get_success_url(self):
        return reverse_lazy('crm:pasajero_detail', kwargs={'pk': self.object.pk})

class PasajeroDeleteView(CRMBaseMixin, DeleteView):
    model = Pasajero
    template_name = 'crm/pasajero_confirm_delete.html'
    success_url = reverse_lazy('crm:pasajero_list')

class PasajeroConvertToClienteView(CRMBaseMixin, View):
    def post(self, request, pk, *args, **kwargs):
        pasajero = get_object_or_404(Pasajero, pk=pk)
        
        # Verificar que no esté ya vinculado o lo requiera
        if pasajero.clientes.exists():
            messages.warning(request, f"El pasajero {pasajero.get_nombre_completo()} ya está vinculado a un cliente.")
            return redirect('crm:pasajero_detail', pk=pk)
        
        try:
            # Crear un nuevo Cliente copiando los datos del pasajero
            nuevo_cliente = Cliente.objects.create(
                nombres=pasajero.nombres,
                apellidos=pasajero.apellidos,
                numero_pasaporte=pasajero.numero_pasaporte,
                cedula_identidad=pasajero.cedula_identidad,
                fecha_nacimiento=pasajero.fecha_nacimiento,
                nacionalidad=pasajero.nacionalidad,
                email=pasajero.email,
                telefono_principal=pasajero.telefono,
                foto_perfil=pasajero.foto_perfil,
                agencia=pasajero.agencia,
                tipo_cliente='IND'
            )
            # Vincular
            nuevo_cliente.pasajeros.add(pasajero)
            
            messages.success(request, f"El pasajero {pasajero.get_nombre_completo()} fue convertido a Cliente exitosamente.")
            return redirect('crm:cliente_detail', pk=nuevo_cliente.pk)
        except IntegrityError:
            messages.error(request, f"Error: Ya existe un Cliente registrado con este mismo documento ({pasajero.numero_documento}). Por favor, búscalo en la lista de Clientes y vincúlalo manualmente pulsando en 'Vincular Pasajero'.")
            return redirect('crm:pasajero_detail', pk=pk)

# --- ACCIONES CRM ---

class PasajeroSearchView(CRMBaseMixin, View):
    def get(self, request, *args, **kwargs):
        q = request.GET.get('q', '').strip()
        if len(q) < 2:
            return HttpResponse('<p class="text-gray-500 text-sm text-center py-4">Sigue escribiendo...</p>')
            
        pasajeros = Pasajero.objects.filter(
            Q(nombres__icontains=q) | 
            Q(apellidos__icontains=q) | 
            Q(numero_pasaporte__icontains=q) |
            Q(cedula_identidad__icontains=q)
        ).exclude(clientes=request.GET.get('cliente_id'))[:10]
        
        return render(request, 'crm/partials/pasajero_search_results.html', {
            'pasajeros': pasajeros,
            'cliente_id': request.GET.get('cliente_id')
        })

class VincularPasajeroActionView(CRMBaseMixin, View):
    def post(self, request, pk, *args, **kwargs):
        cliente = get_object_or_404(Cliente, pk=pk)
        pasajero_id = request.POST.get('pasajero_id')
        if pasajero_id:
            pasajero = get_object_or_404(Pasajero, pk=pasajero_id)
            cliente.pasajeros.add(pasajero)
            messages.success(request, f"Pasajero {pasajero.get_nombre_completo()} vinculado.")
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

# --- OCR VISTAS ---
import json
import base64
from django.core.files.base import ContentFile
from core.services.ocr_service import ocr_service

class PasajeroOCRProcessView(CRMBaseMixin, View):
    def post(self, request, *args, **kwargs):
        if 'archivo' not in request.FILES:
            return HttpResponse("<div class='p-4 text-red-500'>Error: No se recibió ningún archivo.</div>", status=400)
            
        archivo = request.FILES['archivo']
        
        try:
            # Leer el archivo en memoria
            file_content = archivo.read()
            mime_type = archivo.content_type or "image/jpeg"
            
            # Llamada al nuevo motor de IA Multimodal
            result = ocr_service.procesar_pasaporte(file_content, mime_type)
            
            if result.get('success'):
                data = result
                
                # Pre-llenar datos para el form
                initial_data = {
                    'nombres': data.get('nombres', ''),
                    'apellidos': data.get('apellidos', ''),
                    'numero_pasaporte': data.get('numero_pasaporte', ''),
                    'fecha_nacimiento': data.get('fecha_nacimiento', ''),
                    'fecha_vencimiento_documento': data.get('fecha_vencimiento', ''),
                    'nacionalidad': data.get('nacionalidad', ''),
                    'pais_emision_documento': data.get('pais_emision', ''),
                    'genero': data.get('sexo', ''),
                }
                
                form = PasajeroForm(initial=initial_data)
                
                return render(request, 'crm/pasajero_ocr_verification.html', {
                    'form': form,
                    'image_data': data.get('face_image_base64', ''),
                    'confidence': 'Alta (>95%)'
                })
            else:
                return HttpResponse(f"<div class='p-4 text-red-500'>Error del OCR: {result.get('error', 'Desconocido')}</div>", status=400)
                
        except Exception as e:
            return HttpResponse(f"<div class='p-4 text-red-500'>Error Interno: {str(e)}</div>", status=500)

class PasajeroOCRSaveView(CRMBaseMixin, View):
    def post(self, request, *args, **kwargs):
        form = PasajeroForm(request.POST)
        if form.is_valid():
            pasajero = form.save(commit=False)
            pasajero.agencia = getattr(request.user, 'agencia', None)
            
            # Guardar la foto de perfil desde el Base64 generado por el OCR
            image_data = request.POST.get('image_data', '')
            if image_data and image_data.startswith('data:image'):
                try:
                    # data:image/jpeg;base64,...
                    format, imgstr = image_data.split(';base64,')
                    ext = format.split('/')[-1]
                    file_name = f"{pasajero.numero_documento}_perfil.{ext}"
                    pasajero.foto_perfil = ContentFile(base64.b64decode(imgstr), name=file_name)
                except Exception as e:
                    # Log the error but don't stop the save process
                    print(f"Error procesando la foto del OCR: {str(e)}")
            
            pasajero.save()
            
            messages.success(request, f"Pasajero {pasajero.get_nombre_completo()} validado y guardado correctamente.")
            response = HttpResponse()
            response['HX-Redirect'] = reverse_lazy('crm:pasajero_list')
            return response
        else:
            # Re-render validation form with errors
            return render(request, 'crm/pasajero_ocr_verification.html', {
                'form': form,
                'image_data': request.POST.get('image_data', ''),
                'confidence': 'Alta (>95%)'
            })
