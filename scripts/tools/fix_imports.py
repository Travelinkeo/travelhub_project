import os
import re

MAPPING = {
    'bookings': [
        'Venta', 'ItemVenta', 'AlojamientoReserva', 'AlquilerAutoReserva', 
        'ServicioAdicionalDetalle', 'SegmentoVuelo', 'TrasladoServicio', 
        'ActividadServicio', 'BoletoImportado', 'PagoVenta', 'FeeVenta',
        'SolicitudAnulacion', 'VentaParseMetadata', 'PaqueteAereo',
        'CircuitoTuristico', 'CircuitoDia'
    ],
    'crm': ['Cliente', 'Pasajero'],
    'finance': ['Factura', 'ItemFactura', 'GastoOperativo', 'ReporteProveedor', 'ItemReporte', 'DiferenciaFinanciera'],
    'cotizaciones': ['Cotizacion', 'ItemCotizacion']
}

# Invert mapping for easier lookup
MODEL_TO_APP = {m: app for app, models in MAPPING.items() for m in models}

def fix_imports(content):
    # Match lines like: from core.models import Venta, Cliente, Agencia
    # Also handle multiline imports by searching for ( and )
    pattern = r'from core\.models import\s+(\(?[^\)\n]+\)?)'
    
    def replacer(match):
        items_str = match.group(1).strip('()')
        items = [i.strip() for i in items_str.replace('\n', ' ').split(',')]
        
        new_groups = {}
        core_items = []
        
        for item in items:
            if not item: continue
            # Handle 'Item as Alias'
            clean_item = item.split(' as ')[0].strip()
            
            if clean_item in MODEL_TO_APP:
                app = MODEL_TO_APP[clean_item]
                if app not in new_groups: new_groups[app] = []
                new_groups[app].append(item)
            else:
                core_items.append(item)
        
        new_lines = []
        if core_items:
            new_lines.append(f"from core.models import {', '.join(core_items)}")
        
        for app, items in new_groups.items():
            line_start = f"from apps.{app}.models import " if app != 'cotizaciones' else "from apps.cotizaciones.models import "
            new_lines.append(f"{line_start}{', '.join(items)}")
        
        return '\n'.join(new_lines)

    return re.sub(pattern, replacer, content)

def process_directory(path):
    for root, dirs, files in os.walk(path):
        if any(x in root for x in ['venv', '.git', '__pycache__', '.next', 'node_modules']):
            continue
        for file in files:
            if file.endswith('.py') and file != 'fix_imports.py':
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = fix_imports(content)
                    
                    if content != new_content:
                        print(f"Fixing: {full_path}")
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                except Exception as e:
                    print(f"Error processing {full_path}: {e}")

if __name__ == "__main__":
    print("🚀 Starting import refactor...")
    process_directory('.')
    print("✅ Refactor complete.")
