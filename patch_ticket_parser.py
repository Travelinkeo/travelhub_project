import re
import os

file_path = r'c:\Users\ARMANDO\travelhub_project\core\ticket_parser.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Limpiar los prints de depuración ruidosos
content = re.sub(r'print\("\\n" \+ "!"\*50\)\n', '', content)
content = re.sub(r'print\("!!! EXECUTION REACHED extract_data_from_text !!!"\)\n', '', content)
content = re.sub(r'print\("!"\*50 \+ "\\n"\)\n', '', content)

# 2. Reemplazar el bloque de la IA completo por la versión correcta
new_ai_block = """    # 🚀 MOTOR UNIVERSAL IA (PRIMERA PRIORIDAD)
    # Intentamos parsear semánticamente con Gemini 2.0 Flash
    print("🤖 Iniciando Motor Universal IA (Gemini 2.0 Flash)...")
    try:
        from core.parsers.ai_universal_parser import UniversalAIParser
        ai_parser = UniversalAIParser()
        res_ai = ai_parser.parse(plain_text)
        
        # Validar si la IA tuvo éxito y extrajo datos mandatorios (Usando llaves estandarizadas)
        if res_ai and "error" not in res_ai and res_ai.get("NOMBRE_DEL_PASAJERO"):
            print(f"✅ Éxito con Motor IA (Sistema: {res_ai.get('SOURCE_SYSTEM')})")
            return _apply_universal_schema_filter(res_ai)
        else:
            error_msg = res_ai.get('error') if res_ai else 'Datos incompletos'
            print(f"⚠️ Motor IA no pudo extraer datos clave o falló: {error_msg}")
    except Exception as e:
        print(f"❌ Error fatal en integración con IA: {e}")
"""

# Buscamos desde el comentario de la IA hasta el inicio de los fallbacks
pattern = re.compile(r'    # 🚀 MOTOR UNIVERSAL IA.*?logger\.info\("🔄 Iniciando Motores de Fallback \(RegEx\)\.\.\."\)', re.DOTALL)

if pattern.search(content):
    content = pattern.sub(new_ai_block + '\n    logger.info("🔄 Iniciando Motores de Fallback (RegEx)...")', content)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Parche aplicado con éxito.")
else:
    print("❌ No se encontró el bloque de la IA para parchear.")

# 3. Eliminar importaciones duplicadas si las hay
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

seen_imports = set()
new_lines = []
for line in lines:
    if line.strip().startswith('from core.parsers.ai_universal_parser import UniversalAIParser'):
        if line in seen_imports:
            continue
        seen_imports.add(line)
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
