"""
Script para agregar teléfonos a clientes existentes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from personas.models import Cliente

def agregar_telefonos():
    """Agrega teléfonos a clientes que no los tienen"""
    
    print("=== Agregar Teléfonos a Clientes ===\n")
    
    # Buscar clientes sin teléfono
    clientes_sin_telefono = Cliente.objects.filter(
        telefono_principal__isnull=True
    ) | Cliente.objects.filter(telefono_principal='')
    
    total = clientes_sin_telefono.count()
    print(f"Clientes sin teléfono: {total}\n")
    
    if total == 0:
        print("✓ Todos los clientes tienen teléfono configurado")
        return
    
    print("Opciones:")
    print("1. Agregar teléfonos manualmente")
    print("2. Listar clientes sin teléfono")
    print("3. Salir")
    
    opcion = input("\nSelecciona una opción (1-3): ").strip()
    
    if opcion == '1':
        agregar_manual(clientes_sin_telefono)
    elif opcion == '2':
        listar_clientes(clientes_sin_telefono)
    else:
        print("Saliendo...")

def agregar_manual(clientes):
    """Permite agregar teléfonos manualmente"""
    print("\n=== Agregar Teléfonos Manualmente ===")
    print("Formato: +584121234567 (incluye + y código de país)")
    print("Escribe 'salir' para terminar\n")
    
    for cliente in clientes:
        print(f"\nCliente: {cliente.get_nombre_completo()}")
        print(f"Email: {cliente.email or 'Sin email'}")
        print(f"ID: {cliente.id_cliente}")
        
        telefono = input("Teléfono (o Enter para omitir): ").strip()
        
        if telefono.lower() == 'salir':
            break
        
        if telefono:
            if not telefono.startswith('+'):
                print("⚠️  Advertencia: El teléfono debe empezar con + y código de país")
                confirmar = input("¿Continuar de todos modos? (s/n): ").strip().lower()
                if confirmar != 's':
                    continue
            
            cliente.telefono_principal = telefono
            cliente.save()
            print(f"✓ Teléfono agregado: {telefono}")
        else:
            print("⊘ Omitido")
    
    print("\n✓ Proceso completado")

def listar_clientes(clientes):
    """Lista todos los clientes sin teléfono"""
    print("\n=== Clientes sin Teléfono ===\n")
    
    for i, cliente in enumerate(clientes, 1):
        print(f"{i}. {cliente.get_nombre_completo()}")
        print(f"   Email: {cliente.email or 'Sin email'}")
        print(f"   ID: {cliente.id_cliente}")
        print()
    
    print(f"Total: {clientes.count()} clientes")

if __name__ == '__main__':
    agregar_telefonos()
