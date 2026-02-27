import os

search_content = """{% extends "base_modern.html" %}
{% load static %}
{% load humanize %}
{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="bg-indigo-600 rounded-xl p-8 mb-8 text-white relative overflow-hidden shadow-lg">
        <div class="absolute inset-0 opacity-20 bg-[url('https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?ixlib=rb-1.2.1&auto=format&fit=crop&w=1500&q=80')] bg-cover bg-center"></div>
        <div class="relative z-10"><h1 class="text-3xl font-bold mb-4">Encuentra el Alojamiento Perfecto</h1><form method="get" class="bg-white p-2 rounded-lg flex flex-col md:flex-row gap-2 shadow-xl items-center"><div class="flex-1 px-4 py-2 border-r border-gray-100 w-full"><label class="block text-xs font-bold text-gray-500 uppercase">Destino</label><input type="text" name="q" value="{{ request.GET.q }}" placeholder="¿A dónde vas?" class="w-full text-gray-800 font-semibold focus:outline-none placeholder-gray-300"></div><button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-8 rounded-lg flex items-center gap-2"><i data-lucide="search" class="w-5 h-5"></i> Buscar</button></form></div>
    </div>
    <div class="flex flex-col lg:flex-row gap-8">
        <aside class="w-full lg:w-1/4 space-y-6">
            <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100 sticky top-4">
                <div class="flex justify-between items-center mb-4"><h3 class="font-bold text-gray-800">Filtros</h3>{% if request.GET %}<a href="{% url 'core:hotel_search' %}" class="text-xs text-indigo-600 hover:underline">Limpiar</a>{% endif %}</div>
                <div class="mb-6"><h4 class="text-sm font-semibold text-gray-600 mb-2">Destinos Populares</h4><div class="space-y-2">{% for dest in destinos %}<a href="?destino={{ dest }}" class="block text-sm text-gray-600 hover:text-indigo-600 {% if request.GET.destino == dest %}font-bold text-indigo-600{% endif %}">{{ dest }}</a>{% endfor %}</div></div>
                <div class="mb-6"><h4 class="text-sm font-semibold text-gray-600 mb-2">Categoría</h4><div class="space-y-2">{% for val, label in categorias %}<label class="flex items-center space-x-2 cursor-pointer"><input type="radio" name="categoria" value="{{ val }}" {% if request.GET.categoria == val|stringformat:"i" %}checked{% endif %} data-filter-url="?categoria={{ val }}" class="category-filter text-indigo-600 focus:ring-indigo-500"><span class="text-sm text-gray-600">{{ label }}</span></label>{% endfor %}</div></div>
            </div>
        </aside>
        <div class="w-full lg:w-3/4">
            <div class="flex justify-between items-center mb-6"><h2 class="text-xl font-bold text-gray-800">{{ page_obj.paginator.count }} Alojamientos encontrados</h2></div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                {% for hotel in hoteles %}
                <a href="{% url 'core:hotel_detail' hotel.slug %}" class="group bg-white rounded-xl shadow-sm hover:shadow-xl transition duration-300 border border-gray-100 overflow-hidden flex flex-col h-full"><div class="relative h-48 overflow-hidden">{% if hotel.imagen_principal %}<img src="{{ hotel.imagen_principal.url }}" class="w-full h-full object-cover transform group-hover:scale-110 transition duration-500" alt="{{ hotel.nombre }}">{% else %}<div class="w-full h-full bg-gray-200 flex items-center justify-center text-gray-400"><i data-lucide="image" class="w-12 h-12 text-gray-400"></i></div>{% endif %}</div><div class="p-5 flex-1 flex flex-col"><h3 class="font-bold text-gray-800 text-lg group-hover:text-indigo-600 transition">{{ hotel.nombre }}</h3><p class="text-sm text-gray-500 flex items-center gap-1 mb-2"><i data-lucide="map-pin" class="w-3 h-3"></i> {{ hotel.destino }}</p><p class="text-gray-600 text-sm mb-4 line-clamp-3">{{ hotel.descripcion_larga|striptags|truncatechars:150 }}</p><div class="border-t pt-4 flex justify-between items-center mt-auto"><div class="text-xs text-gray-500 bg-green-50 text-green-700 px-2 py-1 rounded-full border border-green-100">{{ hotel.get_categoria_display }}</div><span class="text-indigo-600 text-sm font-semibold group-hover:underline">Ver Tarifas &rarr;</span></div></div></a>
                {% empty %}<div class="col-span-full py-12 text-center bg-gray-50 rounded-xl border border-dashed border-gray-300"><i data-lucide="search-x" class="w-12 h-12 text-gray-400 mx-auto mb-4"></i><h3 class="text-lg font-medium text-gray-900">No encontramos resultados</h3></div>{% endfor %}
            </div>
        </div>
    </div>
</div>
<script nonce="{{ request.csp_nonce }}">document.addEventListener('DOMContentLoaded', function() { document.querySelectorAll('.category-filter').forEach(input => { input.addEventListener('change', function() { if (this.checked) { window.location.href = this.getAttribute('data-filter-url'); } }); }); });</script>
{% endblock %}"""

detail_content = """{% extends "base_modern.html" %}
{% load static %}
{% load humanize %}
{% block content %}
<div class="bg-gray-50 min-h-screen pb-12">
    <div class="bg-white border-b border-gray-200"><div class="container mx-auto px-4 py-6">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-2 h-96 rounded-2xl overflow-hidden shadow-lg relative group">
                <div class="md:col-span-2 md:row-span-2 relative h-full">{% if hotel.imagen_principal %}<img src="{{ hotel.imagen_principal.url }}" class="w-full h-full object-cover cursor-pointer hover:opacity-95 transition" data-gallery-index="0">{% else %}<div class="w-full h-full bg-gray-200 flex items-center justify-center"><i data-lucide="image" class="w-12 h-12 text-gray-400"></i></div>{% endif %}</div>
                {% for img in hotel.imagenes.all|slice:"1:5" %}<div class="relative h-full hidden md:block"><img src="{{ img.imagen.url }}" class="w-full h-full object-cover cursor-pointer hover:opacity-95 transition" data-gallery-index="{{ forloop.counter }}"></div>{% endfor %}
                <button data-gallery-index="0" class="absolute bottom-4 right-4 bg-white px-4 py-2 rounded-lg text-sm font-bold shadow hover:bg-gray-100 flex items-center gap-2 btn-open-gallery"><i data-lucide="grid" class="w-4 h-4"></i> Ver todas las fotos</button>
            </div></div></div>
    <div class="container mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="lg:col-span-2 space-y-8">
            <div class="flex items-center gap-2 mb-2"><span class="bg-blue-100 text-blue-800 text-xs font-bold px-2 py-1 rounded-full uppercase">{{ hotel.get_categoria_display }}</span><span class="text-gray-500 text-sm flex items-center gap-1"><i data-lucide="map-pin" class="w-3 h-3"></i> {{ hotel.destino }}</span></div>
            <h1 class="text-4xl font-extrabold text-gray-900 mb-4">{{ hotel.nombre }}</h1>
            <div class="flex flex-wrap gap-4 text-sm text-gray-600 border-y py-4">{% for amenidad in hotel.amenidades.all %}<span class="flex items-center gap-1"><i data-lucide="{{ amenidad.icono_lucide }}" class="w-4 h-4 text-green-600"></i> {{ amenidad.nombre }}</span>{% endfor %}</div>
            <div class="prose max-w-none text-gray-700"><h3 class="font-bold text-xl mb-3">Sobre este alojamiento</h3>{{ hotel.descripcion_larga|linebreaks|striptags }}</div>
            <div><h3 class="font-bold text-xl mb-4">Habitaciones Disponibles</h3><div class="space-y-4">{% for hab in hotel.tipos_habitacion.all %}
                    <div class="bg-white border rounded-xl p-4 flex flex-col md:flex-row gap-4 hover:shadow-md transition">
                        <div class="w-full md:w-48 h-32 bg-gray-100 rounded-lg overflow-hidden shrink-0">{% if hab.foto_referencial %}<img src="{{ hab.foto_referencial.url }}" class="w-full h-full object-cover">{% else %}<div class="w-full h-full flex items-center justify-center text-gray-400"><i data-lucide="bed" class="w-8 h-8"></i></div>{% endif %}</div>
                        <div class="flex-1"><h4 class="font-bold text-lg">{{ hab.nombre }}</h4><p class="text-sm text-gray-500 mb-2">Capacidad: {{ hab.capacidad_adultos }} Adultos, {{ hab.capacidad_ninos }} Niños (Max {{ hab.capacidad_total }})</p><p class="text-sm text-gray-600">{{ hab.descripcion }}</p></div>
                        <div class="flex flex-col justify-center items-end min-w-[120px]"><button data-room-id="{{ hab.id }}" data-room-name="{{ hab.nombre }}" class="btn-seleccionar-hab bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-indigo-700 transition w-full">Seleccionar</button></div>
                    </div>{% endfor %}</div></div>
        </div>
        <div class="lg:col-span-1">
            <div class="bg-white rounded-xl shadow-lg border border-gray-100 p-6 sticky top-8"><form id="quoteForm" class="space-y-4"><input type="hidden" id="selectedRoomId" name="room_type_id"><div id="selectedRoomDisplay" class="hidden bg-indigo-50 border border-indigo-100 p-2 rounded-lg mb-2"><p class="text-xs font-bold text-indigo-800 uppercase">Habitación Seleccionada</p><p class="text-sm text-indigo-900 font-medium truncate" id="selectedRoomNameDisplay">--</p></div><div class="grid grid-cols-2 gap-2"><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Entrada</label><input type="date" id="checkInDate" class="w-full border-gray-300 rounded-lg text-sm"></div><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Salida</label><input type="date" id="checkOutDate" class="w-full border-gray-300 rounded-lg text-sm"></div></div>
                    <div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Huéspedes</label><div class="grid grid-cols-2 gap-2"><div><span class="text-xs text-gray-400">Adultos</span><input type="number" id="adultsCount" value="2" min="1" class="w-full border-gray-300 rounded-lg text-sm"></div><div><span class="text-xs text-gray-400">Niños</span><input type="number" id="childrenCount" value="0" min="0" class="w-full border-gray-300 rounded-lg text-sm"></div></div></div>
                    <div class="border-t pt-4 mt-4"><div id="quoteResult" class="opacity-50 transition-opacity"><div class="flex justify-between mb-2 text-sm"><span class="text-gray-600" id="nightsDisplay">x 0 Noches</span><span class="font-medium" id="subtotalDisplay">$ --</span></div><div class="flex justify-between text-lg font-bold text-gray-900 pt-2 border-t"><span>Total Estimado</span><span id="totalDisplay">$ --</span></div><p class="text-xs text-red-500 mt-2 hidden" id="quoteError"></p></div></div><button type="button" id="btnAddToCart" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 rounded-xl transition shadow-lg disabled:opacity-50" disabled>Añadir al Carrito</button><p class="text-center text-xs text-gray-400 mt-2">No se te cobrará nada aún</p></form></div>
        </div>
    </div>
</div>
<div id="galleryModal" class="fixed inset-0 z-50 bg-black/95 hidden flex items-center justify-center p-4"><button id="btnCloseGallery" class="absolute top-4 right-4 text-white hover:text-gray-300"><i data-lucide="x" class="w-8 h-8"></i></button><img id="galleryImage" src="" class="max-h-[90vh] max-w-full rounded shadow-2xl"></div>
<script nonce="{{ request.csp_nonce }}">
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.btn-seleccionar-hab').forEach(button => {
        button.addEventListener('click', function() {
            seleccionarHabitacion(this.getAttribute('data-room-id'), this.getAttribute('data-room-name'));
        });
    });
    ['checkInDate', 'checkOutDate', 'adultsCount', 'childrenCount'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', updateQuote);
    });
    document.querySelectorAll('[data-gallery-index]').forEach(img => {
        img.addEventListener('click', function() {
            openGallery(this.getAttribute('data-gallery-index'));
        });
    });
    const btnClose = document.getElementById('btnCloseGallery');
    if (btnClose) btnClose.addEventListener('click', () => {
        document.getElementById('galleryModal').classList.add('hidden');
    });
    const btnAdd = document.getElementById('btnAddToCart');
    if (btnAdd) btnAdd.addEventListener('click', () => {
        alert("¡Función de Carrito en desarrollo!");
    });
});
function openGallery(index) {
    const modal = document.getElementById('galleryModal');
    const img = document.getElementById('galleryImage');
    {% if hotel.imagen_principal %} img.src = "{{ hotel.imagen_principal.url }}"; {% endif %}
    modal.classList.remove('hidden');
}
function seleccionarHabitacion(id, nombre) {
    document.getElementById('selectedRoomId').value = id;
    document.getElementById('selectedRoomNameDisplay').textContent = nombre;
    document.getElementById('selectedRoomDisplay').classList.remove('hidden');
    document.getElementById('quoteForm').scrollIntoView({ behavior: 'smooth' });
    updateQuote();
}
async function updateQuote() {
    const roomId = document.getElementById('selectedRoomId').value;
    const checkIn = document.getElementById('checkInDate').value;
    const checkOut = document.getElementById('checkOutDate').value;
    const adults = document.getElementById('adultsCount').value;
    const children = document.getElementById('childrenCount').value;
    const btn = document.getElementById('btnAddToCart');
    const errorMsg = document.getElementById('quoteError');
    const resultBox = document.getElementById('quoteResult');
    if (!roomId || !checkIn || !checkOut) return;
    errorMsg.classList.add('hidden');
    btn.disabled = true;
    resultBox.classList.add('opacity-50');
    try {
        const params = new URLSearchParams({ room_type_id: roomId, check_in: checkIn, check_out: checkOut, adults, children });
        const response = await fetch(`{% url 'core:hotel_quote_api' %}?${params}`);
        const data = await response.json();
        if (response.ok) {
            document.getElementById('totalDisplay').textContent = `${data.currency} ${data.total.toFixed(2)}`;
            document.getElementById('subtotalDisplay').innerText = `${data.currency} ${data.total.toFixed(2)}`;
            document.getElementById('nightsDisplay').textContent = `x ${data.nights} Noches`;
            resultBox.classList.remove('opacity-50');
            if (data.total > 0) btn.disabled = false;
        } else {
            throw new Error(data.error || 'Error calculando tarifa');
        }
    } catch (e) {
        console.error(e);
        errorMsg.textContent = e.message;
        errorMsg.classList.remove('hidden');
    }
}
</script>
{% endblock %}"""

def write_file(path, content):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)

write_file(r'c:\\Users\\ARMANDO\\travelhub_project\\core\\templates\\core\\hotels\\search.html', search_content)
write_file(r'c:\\Users\\ARMANDO\\travelhub_project\\core\\templates\\core\\hotels\\detail.html', detail_content)
print("Files rewritten successfully.")
