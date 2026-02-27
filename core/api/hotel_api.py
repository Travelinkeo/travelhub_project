from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
from datetime import timedelta
from decimal import Decimal
from core.models import TipoHabitacion, TarifaHabitacion

class HotelQuoteAPI(APIView):
    def get(self, request):
        try:
            # 1. Inputs
            room_id = request.GET.get('room_type_id')
            check_in_str = request.GET.get('check_in')
            check_out_str = request.GET.get('check_out')
            adults = int(request.GET.get('adults', 2))
            children = int(request.GET.get('children', 0))

            if not all([room_id, check_in_str, check_out_str]):
                return Response({'error': 'Faltan datos obligatorios'}, status=400)

            check_in = parse_date(check_in_str)
            check_out = parse_date(check_out_str)
            
            if not check_in or not check_out:
                return Response({'error': 'Fechas inválidas'}, status=400)
                
            if check_in >= check_out:
                return Response({'error': 'Fecha de salida debe ser posterior a la entrada'}, status=400)

            # 2. Get Room
            room = TipoHabitacion.objects.get(pk=room_id)
            
            # Validation Capacity
            if adults + children > room.capacidad_total:
                return Response({'error': f'Excede capacidad máxima ({room.capacidad_total})'}, status=400)

            # 3. Calculate Day by Day
            total_amount = Decimal('0.00')
            currency = 'USD' # Default
            breakdown = []
            
            current_date = check_in
            nights = (check_out - check_in).days
            
            while current_date < check_out:
                # Find Rate for this specific date
                rate_obj = TarifaHabitacion.objects.filter(
                    tipo_habitacion=room,
                    fecha_inicio__lte=current_date,
                    fecha_fin__gte=current_date
                ).first()
                
                day_cost = Decimal('0.00')
                note = ""

                if rate_obj:
                    currency = rate_obj.moneda
                    
                    # Logic based on Occupancy
                    base_rate = Decimal('0.00')
                    
                    if rate_obj.tipo_tarifa == 'POR_HABITACION':
                        # Simple flat rate
                        # We assume 'tarifa_dbl' is the standard base for room rate if specific field missing
                        # Or define logic: SGL=1pax, DBL=2pax...
                        if adults == 1 and rate_obj.tarifa_sgl:
                            base_rate = rate_obj.tarifa_sgl
                        elif adults == 2 and rate_obj.tarifa_dbl:
                            base_rate = rate_obj.tarifa_dbl
                        elif adults == 3 and rate_obj.tarifa_tpl:
                            base_rate = rate_obj.tarifa_tpl
                        elif adults == 4 and rate_obj.tarifa_cpl:
                            base_rate = rate_obj.tarifa_cpl
                        else:
                            # Fallback
                            base_rate = rate_obj.tarifa_dbl or rate_obj.tarifa_sgl or 0
                            
                        day_cost = base_rate
                        note = f"Tarifa Habitación ({adults} pax)"
                        
                    else: # POR_PERSONA
                        adult_rate = Decimal('0.00')
                        if adults == 1 and rate_obj.tarifa_sgl:
                            adult_rate = rate_obj.tarifa_sgl
                        elif adults == 2 and rate_obj.tarifa_dbl:
                            adult_rate = rate_obj.tarifa_dbl
                        elif adults == 3 and rate_obj.tarifa_tpl:
                            adult_rate = rate_obj.tarifa_tpl
                        elif adults == 4 and rate_obj.tarifa_cpl:
                            adult_rate = rate_obj.tarifa_cpl
                        else:
                             # Fallback or error
                            adult_rate = rate_obj.tarifa_dbl or Decimal('0.00')

                        day_cost += (adult_rate * adults)
                        
                        # Children
                        if children > 0 and rate_obj.tarifa_nino:
                             day_cost += (rate_obj.tarifa_nino * children)
                             
                        note = f"Tarifa x Persona ({adults} Adt + {children} Chd)"

                else:
                    note = "Sin tarifa cargada"
                    # Handle missing rate? For now 0
                
                breakdown.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'cost': float(day_cost),
                    'note': note
                })
                
                total_amount += day_cost
                current_date += timedelta(days=1)

            # 4. Response
            return Response({
                'success': True,
                'total': float(total_amount),
                'currency': currency,
                'nights': nights,
                'breakdown': breakdown
            })

        except TipoHabitacion.DoesNotExist:
             return Response({'error': 'Habitación no encontrada'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
