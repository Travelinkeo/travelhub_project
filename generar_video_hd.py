import os
import subprocess

ffmpeg_path = r"C:\Users\ARMANDO\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"
capturas_dir = r"c:\Users\ARMANDO\travelhub_project\capturas_promocionales"
output_video = r"C:\Users\ARMANDO\Downloads\TravelHub_Video_Promocional_HD.mp4"

# 6 scenes of 5 seconds each = 30 seconds total
scenes = [
    "1_landing_page.png",
    "2_dashboard_operaciones.png",
    "3_analizador_gds.png",
    "4_asistente_brain_ia.png",
    "5_wiki_gds.png",
    "6_configuracion_agencia.png"
]

scene_files = []

for idx, img_name in enumerate(scenes, 1):
    img_path = os.path.join(capturas_dir, img_name)
    scene_out = os.path.join(capturas_dir, f"scene_{idx}.mp4")
    
    # Scale screenshot cleanly into 1920x1080 HD frame with dark background
    vf_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0f172a"
    
    cmd = [
        ffmpeg_path, "-y",
        "-loop", "1",
        "-i", img_path,
        "-vf", vf_filter,
        "-t", "5",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        scene_out
    ]
    
    print(f"Rendering scene {idx}: {img_name}...")
    subprocess.run(cmd, check=True)
    scene_files.append(scene_out)

# Concatenate all 6 scenes into 1 final 30-second video
list_file = os.path.join(capturas_dir, "concat_list.txt")
with open(list_file, "w", encoding="utf-8") as f:
    for s in scene_files:
        f.write(f"file '{s}'\n")

concat_cmd = [
    ffmpeg_path, "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", list_file,
    "-c", "copy",
    output_video
]

print("Concatenating scenes into final MP4 video...")
subprocess.run(concat_cmd, check=True)

print(f"FINAL VIDEO GENERATED AT: {output_video}")
