from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .planner import create_personalized_itinerary


class ItineraryGeneratorView(APIView):
    """
    Endpoint para generar un itinerario personalizado a partir de una consulta en lenguaje natural.
    """
    def post(self, request, *args, **kwargs):
        user_query = request.data.get('query')

        if not user_query:
            return Response({"error": "El campo 'query' es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        # Llamamos a la función principal del planner
        itinerary_result = create_personalized_itinerary(user_query)

        if "error" in itinerary_result or "Lo sentimos" in itinerary_result:
            # Si hubo un error conocido en el proceso
            return Response({"error": itinerary_result}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"itinerary": itinerary_result}, status=status.HTTP_200_OK)
