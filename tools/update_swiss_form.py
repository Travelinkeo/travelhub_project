import re
import os

html_path = r'C:\Users\ARMANDO\travelhub_project\core\templates\core\erp\cotizaciones\crear_cotizacion_swiss.html'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update <style>
style_fixes = """/* Custom overrides for Swiss Light */
.shadow-swiss { box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important; }
.dark .bg-surface-dark { background-color: #1b2127; }
.dark .bg-background-dark { background-color: #101922; }
.dark .border-border-dark { border-color: #283039; }
/* Input Fixes to match design */
input[type="text"], input[type="number"], input[type="date"], select, textarea { 
    width: 100%; border-radius: 0.25rem; border: 1px solid #e2e8f0; height: 3rem; padding-left: 1rem; padding-right: 1rem; 
    background-color: #f8fafc; color: #0f172a; outline: none; transition: border-color 0.2s;
}
input[type="text"]:focus, input[type="number"]:focus, input[type="date"]:focus, select:focus, textarea:focus {
    border-color: #258cf4;
}
textarea { height: auto; padding-top: 0.5rem; padding-bottom: 0.5rem; }
.dark input[type="text"], .dark input[type="number"], .dark input[type="date"], .dark select, .dark textarea { 
    border-color: #283039; background-color: #151a1f; color: white; 
}
"""
html = re.sub(r'/\* Custom overrides for Swiss Light \*/.*?</style>', style_fixes + '</style>', html, flags=re.DOTALL)

# 2. Update Client Information
client_section_old = """<label class="flex flex-col gap-2">
<span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Company Name</span>
<input class="form-input w-full rounded border border-slate-200 dark:border-border-dark bg-white dark:bg-surface-dark h-12 px-4 text-slate-900 dark:text-white placeholder:text-slate-400 focus:border-primary focus:ring-1 focus:ring-primary transition-colors text-base" placeholder="Enter company name" type="text"/>
</label>
<label class="flex flex-col gap-2">
<span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Project / Cost Center</span>
<input class="form-input w-full rounded border border-slate-200 dark:border-border-dark bg-white dark:bg-surface-dark h-12 px-4 text-slate-900 dark:text-white placeholder:text-slate-400 focus:border-primary focus:ring-1 focus:ring-primary transition-colors text-base" placeholder="e.g. Q3 Marketing Summit" type="text"/>
</label>"""

client_section_new = """<label class="flex flex-col gap-2">
<span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Cliente / Empresa</span>
{{ form.cliente }}
<span class="text-xs text-slate-500 mt-1">O Cliente Manual (Prospecto)</span>
{{ form.nombre_cliente_manual }}
</label>
<label class="flex flex-col gap-2">
<span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Descripción Breve</span>
{{ form.descripcion_general }}
</label>"""
html = html.replace(client_section_old, client_section_new)

contact_section_old = """<label class="flex flex-col gap-2 md:col-span-2">
<span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Contact Person</span>
<input class="form-input w-full rounded border border-slate-200 dark:border-border-dark bg-white dark:bg-surface-dark h-12 px-4 text-slate-900 dark:text-white placeholder:text-slate-400 focus:border-primary focus:ring-1 focus:ring-primary transition-colors text-base" placeholder="Full Name" type="text"/>
</label>
<label class="flex flex-col gap-2">
<span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Currency</span>
<div class="relative">
<select class="form-select w-full rounded border border-slate-200 dark:border-border-dark bg-white dark:bg-surface-dark h-12 px-4 text-slate-900 dark:text-white focus:border-primary focus:ring-1 focus:ring-primary transition-colors text-base appearance-none">
<option>CHF (Swiss Franc)</option>
<option>USD (US Dollar)</option>
<option>EUR (Euro)</option>
</select>
</div>
</label>"""

contact_section_new = """<label class="flex flex-col gap-2">
<span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Destino</span>
{{ form.destino }}
</label>
<label class="flex flex-col gap-2 relative">
<span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Moneda</span>
{{ form.moneda }}
</label>
<label class="flex flex-col gap-2">
<span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Válida Hasta</span>
{{ form.fecha_validez }}
</label>"""
html = html.replace(contact_section_old, contact_section_new)

# 3. Update Itinerary/Items Section
items_section_old = re.search(r'<section class="flex flex-col gap-6">\s*<div class="flex items-center gap-3 pb-2 border-b border-dashed.*?Add Return Flight or Hotel *?</button>\s*</section>', html, re.DOTALL)

items_section_new = """<!-- Section: Items Formset -->
<section class="flex flex-col gap-6">
<div class="flex items-center gap-3 pb-2 border-b border-dashed border-slate-200 dark:border-slate-800">
<span class="bg-primary/10 text-primary p-2 rounded-full">
<span class="material-symbols-outlined text-[20px]">inventory_2</span>
</span>
<h3 class="text-slate-900 dark:text-white text-lg font-bold">Servicios / Productos Cotizados</h3>
</div>

{{ items_formset.management_form }}

<div id="items-container" class="flex flex-col gap-6">
    {% for item_form in items_formset %}
    <div class="item-row bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark rounded p-6 shadow-swiss flex flex-col gap-6 relative group">
        {% for hidden in item_form.hidden_fields %}{{ hidden }}{% endfor %}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Servicio Base</span>
                {{ item_form.producto_servicio }}
            </label>
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Descripción Personalizada</span>
                {{ item_form.descripcion_personalizada }}
            </label>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 relative">
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Cant.</span>
                {{ item_form.cantidad }}
            </label>
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Precio Unit.</span>
                {{ item_form.precio_unitario }}
            </label>
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Impuestos</span>
                {{ item_form.impuestos_item }}
            </label>
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Total Est.</span>
                <input type="text" readonly class="total-display text-lg font-bold text-right text-primary cursor-not-allowed bg-slate-50 dark:bg-[#151a1f]" value="0.00" style="height: 3rem; padding: 0 1rem; border-radius: 0.25rem; border: 1px solid #e2e8f0;"/>
            </label>
        </div>
        {% if items_formset.can_delete %}
        <div class="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2">
            <span class="text-xs text-red-500 font-bold uppercase hover:text-red-700 cursor-pointer">Eliminar</span>
            {{ item_form.DELETE }}
        </div>
        {% endif %}
    </div>
    {% endfor %}
</div>

<!-- Empty template for dynamic JS appending -->
<div id="empty-form" class="hidden">
    <div class="item-row bg-white dark:bg-surface-dark border border-slate-200 dark:border-border-dark rounded p-6 shadow-swiss flex flex-col gap-6 relative group">
        {% for hidden in items_formset.empty_form.hidden_fields %}{{ hidden }}{% endfor %}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Servicio Base</span>
                {{ items_formset.empty_form.producto_servicio }}
            </label>
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Descripción Personalizada</span>
                {{ items_formset.empty_form.descripcion_personalizada }}
            </label>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 relative">
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Cant.</span>
                {{ items_formset.empty_form.cantidad }}
            </label>
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Precio Unit.</span>
                {{ items_formset.empty_form.precio_unitario }}
            </label>
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Impuestos</span>
                {{ items_formset.empty_form.impuestos_item }}
            </label>
            <label class="flex flex-col gap-2">
                <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Total Est.</span>
                <input type="text" readonly class="total-display text-lg font-bold text-right text-primary cursor-not-allowed bg-slate-50 dark:bg-[#151a1f]" value="0.00" style="height: 3rem; padding: 0 1rem; border-radius: 0.25rem; border: 1px solid #e2e8f0;"/>
            </label>
        </div>
        <div class="absolute top-4 right-4 flex items-center gap-2">
            <span class="text-xs text-red-500 font-bold uppercase  hover:text-red-700 cursor-pointer">Eliminar</span>
            {{ items_formset.empty_form.DELETE }}
        </div>
    </div>
</div>

<button type="button" id="add-item" class="flex items-center justify-center gap-2 w-full py-4 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded text-slate-500 dark:text-slate-400 hover:border-primary hover:text-primary transition-all font-semibold">
<span class="material-symbols-outlined">add</span> Añadir Servicio
</button>
</section>"""
if items_section_old:
    html = html.replace(items_section_old.group(0), items_section_new)

# 4. Services (Condiciones/Notas)
services_section_old = re.search(r'<!-- Section: Services -->.*?</section>', html, re.DOTALL)
services_section_new = """<!-- Section: Notas -->
<section class="flex flex-col gap-6 mb-10">
<div class="flex items-center gap-3 pb-2 border-b border-dashed border-slate-200 dark:border-slate-800">
<span class="bg-primary/10 text-primary p-2 rounded-full">
<span class="material-symbols-outlined text-[20px]">description</span>
</span>
<h3 class="text-slate-900 dark:text-white text-lg font-bold">Condiciones y Notas</h3>
</div>
<div class="grid grid-cols-1 gap-6">
    <label class="flex flex-col gap-2">
        <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Condiciones Comerciales</span>
        {{ form.condiciones_comerciales }}
    </label>
    <label class="flex flex-col gap-2">
        <span class="text-slate-700 dark:text-slate-300 text-sm font-bold uppercase tracking-wider">Notas Internas (No visibles en PDF)</span>
        {{ form.notas_internas }}
    </label>
</div>
</section>"""
if services_section_old:
    html = html.replace(services_section_old.group(0), services_section_new)

# 5. Connect Cost Breakdown & Generate Button
boton_generar = """<button type="submit" class="w-full mt-6 bg-primary hover:bg-blue-600 text-white font-bold py-3 px-4 rounded transition-colors flex justify-center items-center gap-2">
                                Guardar Cotización
                                <span class="material-symbols-outlined text-[18px]">save</span>
</button>"""
html = re.search(r'(<button class="w-full mt-6 bg-primary hover:bg-blue-600 text-white font-bold py-3 px-4 rounded transition-colors flex justify-center items-center gap-2">\s*Review &amp; Send\s*<span class="material-symbols-outlined text-\[18px\]">arrow_forward</span>\s*</button>)', html)
if html:
    html_str = html.string.replace(html.group(1), boton_generar)
else:
    html_str = html

# Replace header buttons also to act as submit
hdr_btn_old = """<button class="bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:bg-primary dark:hover:bg-primary hover:text-white dark:hover:text-white h-11 px-6 rounded font-bold text-sm transition-colors shadow-sm flex items-center gap-2">
<span class="material-symbols-outlined text-[18px]">send</span>
                    Generate Quote
                </button>"""
hdr_btn_new = """<button type="submit" class="bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:bg-primary dark:hover:bg-primary hover:text-white dark:hover:text-white h-11 px-6 rounded font-bold text-sm transition-colors shadow-sm flex items-center gap-2">
<span class="material-symbols-outlined text-[18px]">save</span> Guardar
</button>"""
html_str = html_str.replace(hdr_btn_old, hdr_btn_new)


# Append JS
js = """
<script>
document.addEventListener('DOMContentLoaded', function () {
    const addItemBtn = document.getElementById('add-item');
    const itemsContainer = document.getElementById('items-container');
    const emptyFormTemplate = document.getElementById('empty-form').innerHTML;
    const totalFormsInput = document.getElementById('id_items_cotizacion-TOTAL_FORMS');

    function calculateTotals() {
        let globalsubtotal = 0;
        let globaltax = 0;

        document.querySelectorAll('.item-row:not(#empty-form .item-row)').forEach(row => {
            const qtyInput = row.querySelector('input[name$="-cantidad"]');
            const priceInput = row.querySelector('input[name$="-precio_unitario"]');
            const taxInput = row.querySelector('input[name$="-impuestos_item"]');
            const totalDisplay = row.querySelector('.total-display');

            if (qtyInput && priceInput && taxInput && totalDisplay) {
                const qty = parseFloat(qtyInput.value) || 0;
                const price = parseFloat(priceInput.value) || 0;
                const tax = parseFloat(taxInput.value) || 0;
                const isDeleted = row.querySelector('input[name$="-DELETE"]')?.checked;

                if (!isDeleted) {
                    const subtotal = qty * price;
                    const taxTotal = tax * qty; // O (tax * qty) dependiendo del modelo de negocio, asumiendo tax = impuesto unitario
                    const total = subtotal + taxTotal;
                    totalDisplay.value = total.toFixed(2);
                    
                    globalsubtotal += subtotal;
                    globaltax += taxTotal;
                } else {
                    totalDisplay.value = '0.00';
                }
            }
        });

        // Update Global UI
        const globalTotal = globalsubtotal + globaltax;
        
        let elSubtotal = document.getElementById('ui-subtotal');
        let elTax = document.getElementById('ui-tax');
        let elTotal = document.getElementById('ui-total');
        
        if(elSubtotal) elSubtotal.innerText = globalsubtotal.toFixed(2);
        if(elTax) elTax.innerText = globaltax.toFixed(2);
        if(elTotal) elTotal.innerText = globalTotal.toFixed(2);
    }

    function attachListeners(row) {
        const inputs = row.querySelectorAll('input, select');
        inputs.forEach(input => {
            input.addEventListener('input', calculateTotals);
            input.addEventListener('change', calculateTotals);
        });
        calculateTotals();
    }

    document.querySelectorAll('.item-row').forEach(row => {
        // don't attach to the template row
        if(row.parentElement.id !== 'empty-form') {
            attachListeners(row);
        }
    });

    if(addItemBtn && itemsContainer && totalFormsInput) {
        addItemBtn.addEventListener('click', function () {
            const formIdx = totalFormsInput.value;
            const newFormHtml = emptyFormTemplate.replace(/__prefix__/g, formIdx);
            
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = newFormHtml;
            const newRow = tempDiv.firstElementChild;
            
            itemsContainer.appendChild(newRow);
            attachListeners(newRow);
            totalFormsInput.value = parseInt(formIdx) + 1;
        });
    }
});
</script>
"""
html_str = html_str.replace("// Placeholder JS for totals", "")
html_str = html_str.replace("</script>", "</script>\n" + js)

# Inject IDs for JS to Sidebar items
html_str = html_str.replace('<span class="font-mono font-medium text-slate-900 dark:text-white">CHF 1,250.00</span>', '<span class="font-mono font-medium text-slate-900 dark:text-white"></span>')
html_str = html_str.replace('<span class="font-mono font-bold text-slate-900 dark:text-white">CHF 1,575.00</span>', '<span class="font-mono font-bold text-slate-900 dark:text-white text-lg" id="ui-subtotal">0.00</span>')
html_str = html_str.replace('<span class="font-mono">CHF 121.28</span>', '<span class="font-mono font-medium" id="ui-tax">0.00</span>')
html_str = html_str.replace('1,696.28', '<span id="ui-total">0.00</span>')
# Remove fake line items
html_str = re.sub(r'<!-- Line Item -->.*?</div>', '', html_str, flags=re.DOTALL)


with open(html_path, 'w', encoding='utf-8') as out:
    out.write(html_str)

print("Template successfully adapted for Django!")
