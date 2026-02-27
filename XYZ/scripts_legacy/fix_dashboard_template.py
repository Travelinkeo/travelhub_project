
import os

file_path = r'c:\Users\ARMANDO\travelhub_project\core\templates\core\erp\cotizaciones\dashboard.html'
line_num = 89
# We will read the file, fix the lines, and write back.

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'request.GET.estado==' in line:
        # naive replacement but sufficient for this specific error
        new_line = line.replace("request.GET.estado=='BOR'", "request.GET.estado == 'BOR'") \
                       .replace("request.GET.estado=='ENV'", "request.GET.estado == 'ENV'") \
                       .replace("request.GET.estado=='ACE'", "request.GET.estado == 'ACE'") \
                       .replace("request.GET.estado=='REC'", "request.GET.estado == 'REC'") \
                       .replace("request.GET.estado=='VEN'", "request.GET.estado == 'VEN'") \
                       .replace("request.GET.estado=='CNV'", "request.GET.estado == 'CNV'")
        new_lines.append(new_line)
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed dashboard.html successfully.")
