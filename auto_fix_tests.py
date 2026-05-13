import os
import re

TEST_DIRS = ['tests', 'core/tests']

# Mapeo de namespaces
URL_NAMESPACES = {
    # Bookings
    r'core:api_boleto_upload': r'bookings:api_boleto_upload',
    r'core:api_boleto_delete': r'bookings:api_boleto_delete',
    r'core:api_boletos_mass_action': r'bookings:api_boletos_mass_action',
    r'core:api_boleto_retry': r'bookings:api_boleto_retry',
    r'core:api_boleto_audit': r'bookings:api_boleto_audit',
    r'core:api_venta_double_invoice': r'bookings:api_venta_double_invoice',
    r'core:upload_boleto': r'bookings:upload_boleto',
    r'core:revisar_boleto': r'bookings:revisar_boleto',
    r'core:desasociar_venta': r'bookings:desasociar_venta',
    r'core:eliminar_boleto_hard': r'bookings:eliminar_boleto_hard',
    r'core:boletos_dashboard': r'bookings:boletos_dashboard',
    r'core:boletos_busqueda': r'bookings:boletos_busqueda',
    r'core:boletos_reportes': r'bookings:boletos_reportes',
    r'core:boletos_reportes_exportar': r'bookings:boletos_reportes_exportar',
    r'core:boletos_anulaciones': r'bookings:boletos_anulaciones',
    r'core:boletos_importar': r'bookings:boletos_importar',
    r'core:boletos_manual': r'bookings:boletos_manual',
    r'core:actualizar_item_boleto': r'bookings:actualizar_item_boleto',
    r'core:boletos_sin_venta': r'bookings:boletos_sin_venta',
    r'core:reintentar_parseo': r'bookings:reintentar_parseo',
    r'core:crear_venta_desde_boleto': r'bookings:crear_venta_desde_boleto',
    r'core:boletos_dashboard_stats': r'bookings:boletos_dashboard_stats',
    r'core:boletos_buscar': r'bookings:boletos_buscar',
    r'core:boletos_reporte_comisiones': r'bookings:boletos_reporte_comisiones',
    r'core:boletos_solicitar_anulacion': r'bookings:boletos_solicitar_anulacion',
    r'core:boletos_detalle': r'bookings:boletos_detalle',
    r'core:boletos_eliminar': r'bookings:boletos_eliminar',

    # Common / Setup
    r'core:catalogos_center': r'common:catalogos_center',
    r'core:aerolineas_list': r'common:aerolineas_list',
    r'core:productos_list': r'common:productos_list',
    r'core:geografia_list': r'common:geografia_list',
    r'core:catalogo_terrestre': r'common:catalogo_terrestre',
    r'core:producto_terrestre_create': r'common:producto_terrestre_create',
    r'core:proveedores_list': r'common:proveedores_list',
    r'core:proveedores_nuevo': r'common:proveedores_nuevo',
    r'core:proveedores_editar': r'common:proveedores_editar',
    r'core:proveedores_eliminar': r'common:proveedores_eliminar',
    r'core:comisiones_list': r'common:comisiones_list',
    r'core:comisiones_nuevo': r'common:comisiones_nuevo',
    r'core:comisiones_editar': r'common:comisiones_editar',
    r'core:comisiones_eliminar': r'common:comisiones_eliminar',
    r'core:tasas_list': r'common:tasas_list',
    r'core:tasas_nuevo': r'common:tasas_nuevo',
    r'core:tasas_sincronizar': r'common:tasas_sincronizar',

    # Finance
    r'core:conciliacion_proveedores_ui': r'finance:conciliacion_proveedores_ui',
    r'core:api_conciliar_proveedor': r'finance:api_conciliar_proveedor',
    r'core:factura_consolidada_list': r'finance:factura_consolidada_list',
    r'core:factura_consolidada_create': r'finance:factura_consolidada_create',
    r'core:factura_consolidada_detail': r'finance:factura_consolidada_detail',
    r'core:factura_consolidada_pdf': r'finance:factura_consolidada_pdf',
    r'core:factura_consolidada_mark_paid': r'finance:factura_consolidada_mark_paid',
    r'core:factura_consolidada_send_email': r'finance:factura_consolidada_send_email',
}

# Mapeo de imports
IMPORT_REPLACEMENTS = {
    r'from core\.views\.facturacion_views import': r'from apps.finance.views.facturacion_views import',
    r'from core\.views\.catalogos_views import': r'from apps.common.views.catalogos_views import',
    r'from core\.views\.boleto_views import': r'from apps.bookings.views.boleto_views import',
    r'from core\.models_catalogos import': r'from apps.common.models.catalogos import',
    r'from core\.models\.productos_terrestres import': r'from apps.common.models.productos_terrestres import',
    r'from core\.models\.cruceros import': r'from apps.common.models.cruceros import',
    r'from core\.models\.contabilidad import': r'from apps.finance.models.contabilidad import',
}

def main():
    files_modified = 0
    for test_dir in TEST_DIRS:
        for root, _dirs, files in os.walk(test_dir):
            for file in files:
                if file.endswith('.py'):
                    path = os.path.join(root, file)
                    try:
                        with open(path, encoding='utf-8') as f:
                            content = f.read()
                        
                        original_content = content
                        
                        # Reemplazar URLs
                        for old_url, new_url in URL_NAMESPACES.items():
                            content = content.replace(old_url, new_url)
                            
                        # Reemplazar Imports
                        for old_imp, new_imp in IMPORT_REPLACEMENTS.items():
                            content = re.sub(old_imp, new_imp, content)
                            
                        if content != original_content:
                            with open(path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            print(f"[OK] Corregido: {path}")
                            files_modified += 1
                    except Exception as e:
                        print(f"[ERROR] {path}: {e}")
                        
    print(f"\nFinalizado. Archivos modificados: {files_modified}")

if __name__ == '__main__':
    main()
