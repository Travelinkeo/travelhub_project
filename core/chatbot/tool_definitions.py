def _get_genai_types():
    """# Importa y retorna tipos de google.genai."""
    from google.genai import types

    return types


def get_tool_definitions():
    """# Define function declarations para Gemini. Returns: types.Tool."""
    types = _get_genai_types()

    consultar_estado_reserva_func = types.FunctionDeclaration(
        name="consultar_estado_reserva",
        description="Consulta el estado actual de una reserva o venta existente usando su código de reserva (PNR o localizador).",
        parameters={
            "type": "object",
            "properties": {
                "pnr": {
                    "type": "string",
                    "description": "El código de reserva (PNR) o localizador de la venta. Por ejemplo: WPYVSD, VTA-20240909-0001.",
                }
            },
            "required": ["pnr"],
        },
    )

    agregar_servicio_adicional_func = types.FunctionDeclaration(
        name="agregar_servicio_adicional",
        description="Agrega un servicio adicional (como un seguro de viaje, una maleta extra, etc.) a una reserva existente.",
        parameters={
            "type": "object",
            "properties": {
                "pnr": {
                    "type": "string",
                    "description": "El código de reserva (PNR) al que se le agregará el servicio.",
                },
                "id_servicio": {
                    "type": "integer",
                    "description": "El ID numérico del producto/servicio a agregar. El chatbot debe preguntarle al usuario si no lo sabe.",
                },
            },
            "required": ["pnr", "id_servicio"],
        },
    )

    buscar_paquetes_turisticos_func = types.FunctionDeclaration(
        name="buscar_paquetes_turisticos",
        description="Busca paquetes turísticos disponibles según un destino, presupuesto y mes de viaje.",
        parameters={
            "type": "object",
            "properties": {
                "destino": {
                    "type": "string",
                    "description": "La ciudad o país de destino. Por ejemplo: 'París', 'Japón'.",
                },
                "presupuesto": {
                    "type": "number",
                    "description": "El presupuesto máximo por persona en USD.",
                },
                "mes": {
                    "type": "string",
                    "description": "El mes deseado para el viaje. Por ejemplo: 'Diciembre', 'Octubre'.",
                },
            },
            "required": ["destino", "presupuesto", "mes"],
        },
    )

    return types.Tool(
        function_declarations=[
            consultar_estado_reserva_func,
            agregar_servicio_adicional_func,
            buscar_paquetes_turisticos_func,
        ]
    )
