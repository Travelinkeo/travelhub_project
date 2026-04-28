"""
Script de Prueba: Sistema de Versionado de Boletos
===================================================

Este script verifica que el sistema de versionado de boletos funcione correctamente:
1. Crear un boleto original (versión 1)
2. Crear una re-emisión (versión 2)
3. Verificar que los campos estén correctamente asignados
4. Mostrar el historial de versiones

Uso:
    python scripts/test_ticket_versioning.py
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.core.files.base import ContentFile
from core.models import Agencia
from apps.bookings.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService

def crear_archivo_dummy():
    """Crea un archivo de texto dummy para simular un boleto"""
    contenido = """
    TICKET NUMBER: 1234567890
    PNR: ABC123
    PASSENGER: DOE/JOHN
    AIRLINE: AVIANCA
    TOTAL: 500.00 USD
    ISSUE DATE: 15JAN26
    """
    return ContentFile(contenido.encode('utf-8'), name='test_ticket.txt')

def limpiar_datos_prueba():
    """Limpia boletos de prueba anteriores"""
    print("🧹 Limpiando datos de prueba anteriores...")
    BoletoImportado.objects.filter(numero_boleto='1234567890').delete()
    print("   ✅ Limpieza completada\n")

def crear_boleto_original():
    """Crea el boleto original (versión 1)"""
    print("📝 PASO 1: Creando boleto original (v1)")
    print("-" * 50)
    
    agencia = Agencia.objects.first()
    if not agencia:
        print("   ❌ Error: No hay agencias en la base de datos")
        return None
    
    # Crear el boleto
    boleto = BoletoImportado.objects.create(
        archivo_boleto=crear_archivo_dummy(),
        agencia=agencia,
        numero_boleto='1234567890',
        nombre_pasajero_completo='DOE/JOHN',
        localizador_pnr='ABC123',
        aerolinea_emisora='AVIANCA',
        total_boleto=Decimal('500.00'),
        estado_parseo='COM'
    )
    
    print(f"   ✅ Boleto creado: ID={boleto.id_boleto_importado}")
    print(f"   📊 Versión: {boleto.version}")
    print(f"   📌 Estado emisión: {boleto.estado_emision}")
    print(f"   🔗 Boleto padre: {boleto.boleto_padre}")
    print(f"   🎫 Número: {boleto.numero_boleto}")
    print()
    
    return boleto

def crear_reemision(boleto_original):
    """Crea una re-emisión del boleto (versión 2)"""
    print("📝 PASO 2: Creando re-emisión (v2)")
    print("-" * 50)
    
    # Crear segundo boleto con el mismo número
    boleto_v2 = BoletoImportado.objects.create(
        archivo_boleto=crear_archivo_dummy(),
        agencia=boleto_original.agencia,
        numero_boleto='1234567890',  # Mismo número
        nombre_pasajero_completo='DOE/JOHN',
        localizador_pnr='ABC123',
        aerolinea_emisora='AVIANCA',
        total_boleto=Decimal('550.00'),  # Precio diferente (cambio de tarifa)
        estado_parseo='PEN'
    )
    
    print(f"   ✅ Re-emisión creada: ID={boleto_v2.id_boleto_importado}")
    print(f"   📊 Versión inicial: {boleto_v2.version}")
    print(f"   📌 Estado emisión inicial: {boleto_v2.estado_emision}")
    print()
    
    # Ejecutar la lógica de versionado
    print("   🔄 Ejecutando lógica de versionado...")
    service = TicketParserService()
    service._gestionar_versionado(boleto_v2)
    
    # Recargar desde DB
    boleto_v2.refresh_from_db()
    
    print(f"   ✅ Versionado aplicado")
    print(f"   📊 Versión final: {boleto_v2.version}")
    print(f"   📌 Estado emisión final: {boleto_v2.estado_emision}")
    print(f"   🔗 Boleto padre: {boleto_v2.boleto_padre.id_boleto_importado if boleto_v2.boleto_padre else 'None'}")
    print()
    
    return boleto_v2

def verificar_versionado(boleto_v1, boleto_v2):
    """Verifica que el versionado sea correcto"""
    print("✅ PASO 3: Verificación de versionado")
    print("-" * 50)
    
    errores = []
    
    # Verificar versión 1
    if boleto_v1.version != 1:
        errores.append(f"❌ Boleto v1 tiene versión {boleto_v1.version}, esperado: 1")
    else:
        print(f"   ✅ Boleto v1 tiene versión correcta: {boleto_v1.version}")
    
    # Verificar versión 2
    if boleto_v2.version != 2:
        errores.append(f"❌ Boleto v2 tiene versión {boleto_v2.version}, esperado: 2")
    else:
        print(f"   ✅ Boleto v2 tiene versión correcta: {boleto_v2.version}")
    
    # Verificar estado de emisión v1
    if boleto_v1.estado_emision != BoletoImportado.EstadoEmision.ORIGINAL:
        errores.append(f"❌ Boleto v1 tiene estado {boleto_v1.estado_emision}, esperado: ORIGINAL")
    else:
        print(f"   ✅ Boleto v1 tiene estado correcto: {boleto_v1.get_estado_emision_display()}")
    
    # Verificar estado de emisión v2
    if boleto_v2.estado_emision != BoletoImportado.EstadoEmision.REEMISION:
        errores.append(f"❌ Boleto v2 tiene estado {boleto_v2.estado_emision}, esperado: REEMISION")
    else:
        print(f"   ✅ Boleto v2 tiene estado correcto: {boleto_v2.get_estado_emision_display()}")
    
    # Verificar relación padre-hijo
    if boleto_v2.boleto_padre != boleto_v1:
        errores.append(f"❌ Boleto v2 no apunta al v1 como padre")
    else:
        print(f"   ✅ Boleto v2 apunta correctamente al v1 como padre")
    
    # Verificar que v1 no tenga padre
    if boleto_v1.boleto_padre is not None:
        errores.append(f"❌ Boleto v1 tiene padre (debería ser None)")
    else:
        print(f"   ✅ Boleto v1 no tiene padre (correcto)")
    
    print()
    
    if errores:
        print("❌ ERRORES ENCONTRADOS:")
        for error in errores:
            print(f"   {error}")
        return False
    else:
        print("🎉 TODAS LAS VERIFICACIONES PASARON")
        return True

def mostrar_historial():
    """Muestra el historial completo de versiones"""
    print("\n📚 PASO 4: Historial de versiones")
    print("=" * 50)
    
    boletos = BoletoImportado.objects.filter(
        numero_boleto='1234567890'
    ).order_by('version')
    
    print(f"\n   Total de versiones encontradas: {boletos.count()}\n")
    
    for boleto in boletos:
        print(f"   📄 Versión {boleto.version}")
        print(f"      ID: {boleto.id_boleto_importado}")
        print(f"      Estado: {boleto.get_estado_emision_display()}")
        print(f"      Total: ${boleto.total_boleto}")
        print(f"      Padre: {boleto.boleto_padre.id_boleto_importado if boleto.boleto_padre else 'N/A'}")
        print(f"      Fecha: {boleto.fecha_subida.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Mostrar versiones posteriores
        posteriores = boleto.versiones_posteriores.all()
        if posteriores.exists():
            print(f"      Versiones posteriores: {[v.id_boleto_importado for v in posteriores]}")
        print()

def main():
    """Función principal"""
    print("\n" + "=" * 50)
    print("🧪 TEST: Sistema de Versionado de Boletos")
    print("=" * 50 + "\n")
    
    try:
        # Limpiar datos previos
        limpiar_datos_prueba()
        
        # Crear boleto original
        boleto_v1 = crear_boleto_original()
        if not boleto_v1:
            return
        
        # Crear re-emisión
        boleto_v2 = crear_reemision(boleto_v1)
        
        # Recargar v1 desde DB por si cambió
        boleto_v1.refresh_from_db()
        
        # Verificar
        exito = verificar_versionado(boleto_v1, boleto_v2)
        
        # Mostrar historial
        mostrar_historial()
        
        # Resultado final
        print("=" * 50)
        if exito:
            print("✅ PRUEBA EXITOSA: El sistema de versionado funciona correctamente")
        else:
            print("❌ PRUEBA FALLIDA: Hay problemas con el versionado")
        print("=" * 50 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
