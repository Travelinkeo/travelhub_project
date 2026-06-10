#!/bin/bash
# Script de automatización para compilar Tailwind CSS usando el binario standalone.
# No requiere Node.js ni NPM en el entorno de producción.

set -e

TAILWIND_BIN="./tailwindcss"

# 1. Detectar si el binario standalone de Tailwind existe localmente, si no, descargarlo de forma inteligente.
if [ ! -f "$TAILWIND_BIN" ] && ! command -v tailwindcss &> /dev/null; then
    echo "⚠️  No se encontró el binario standalone 'tailwindcss'."
    
    # Detectar el sistema operativo y arquitectura
    OS="$(uname -s)"
    ARCH="$(uname -m)"
    
    URL=""
    if [ "$OS" = "Linux" ]; then
        if [ "$ARCH" = "x86_64" ]; then
            URL="https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64"
        elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
            URL="https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-arm64"
        fi
    elif [ "$OS" = "Darwin" ]; then
        if [ "$ARCH" = "x86_64" ]; then
            URL="https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-x64"
        elif [ "$ARCH" = "arm64" ]; then
            URL="https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-arm64"
        fi
    fi

    if [ -n "$URL" ]; then
        echo "🚀 Descargando el binario standalone de Tailwind CSS para su arquitectura ($OS-$ARCH)..."
        curl -sL "$URL" -o "$TAILWIND_BIN"
        chmod +x "$TAILWIND_BIN"
        echo "✅ Binario descargado e instalado exitosamente en $TAILWIND_BIN"
    else
        echo "❌ No se pudo determinar el binario adecuado para su sistema ($OS-$ARCH)."
        echo "Por favor, descargue manualmente el binario 'tailwindcss' desde: https://github.com/tailwindlabs/tailwindcss/releases"
        exit 1
    fi
else
    if command -v tailwindcss &> /dev/null; then
        TAILWIND_BIN="tailwindcss"
        echo "✅ Usando el binario global 'tailwindcss' encontrado en el sistema."
    else
        echo "✅ Usando el binario local '$TAILWIND_BIN'."
    fi
fi

# 2. Asegurar la existencia del directorio de salida
mkdir -p ./core/static/core/css

# 3. Compilar, purgar clases no usadas y minificar el CSS final
echo "🎨 Compilando y minificando Tailwind CSS..."
$TAILWIND_BIN -i ./core/static/core/css/input.css -o ./core/static/core/css/tailwind-built.css --minify

echo "✨ ¡Compilación de Tailwind lista!"
