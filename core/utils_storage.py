"""
Utilidades para storage y manejo de archivos
"""
import os
from django.utils.text import get_valid_filename


def truncate_filename(filename, max_length=100):
    """
    Trunca el nombre del archivo para que no exceda max_length.
    Preserva la extensión del archivo.
    """
    if not filename:
        return filename
    
    # Separar nombre y extensión
    name, ext = os.path.splitext(filename)
    
    # Si la extensión es muy larga, truncarla también
    if len(ext) > 10:
        ext = ext[:10]
    
    # Calcular espacio disponible para el nombre
    available_length = max_length - len(ext)
    
    # Truncar el nombre si es necesario
    if len(name) > available_length:
        name = name[:available_length]
    
    # Reconstruir el nombre del archivo
    return f"{name}{ext}"
