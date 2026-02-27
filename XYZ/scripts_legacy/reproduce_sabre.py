import re
import datetime

def parse_sabre_line(line):
    # Regex pattern for raw Sabre line
    # 1 AV4816K 03DEC 3 NVABOG*SS1  0825  0925  /DCAV /E
    pattern = r'^\s*\d+\s+([A-Z0-9]{2})(\d+)([A-Z]?)\s+(\d{2}[A-Z]{3})\s+\d\s+([A-Z]{3})([A-Z]{3}).*?(\d{4})\s+(\d{4})'
    
    match = re.search(pattern, line)
    if match:
        airline = match.group(1)
        flight_num = match.group(2)
        booking_class = match.group(3)
        date_str = match.group(4)
        origin = match.group(5)
        dest = match.group(6)
        dep_time = match.group(7)
        arr_time = match.group(8)
        
        # Format times
        dep_time_fmt = f"{dep_time[:2]}:{dep_time[2:]}"
        arr_time_fmt = f"{arr_time[:2]}:{arr_time[2:]}"
        
        return {
            'aerolinea': airline,
            'numero_vuelo': flight_num,
            'clase': booking_class,
            'fecha_salida': date_str,
            'origen': origin,
            'destino': dest,
            'hora_salida': dep_time_fmt,
            'hora_llegada': arr_time_fmt
        }
    return None

lines = [
    "1 AV4816K 03DEC 3 NVABOG*SS1  0825  0925  /DCAV /E",
    "2 AV9464K 03DEC 3 BOGCUC*SS1  1305  1425  /DCAV /E"
]

print("Testing Sabre Line Parsing:")
for line in lines:
    result = parse_sabre_line(line)
    print(f"Line: {line}")
    print(f"Result: {result}")
    print("-" * 20)
