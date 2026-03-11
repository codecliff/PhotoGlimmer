#!/bin/bash
set -e

echo "🚀 Initializing PhotoGlimmer AppImage Build..."

# 1. Ensure Python 3.12 and VENV are present on the host
# if ! command -v python3.12 &> /dev/null; then
#     echo "🐍 Python 3.12 not found. Installing via deadsnakes PPA..."
#     exit 1 #TODO: only for local system!
#     sudo add-apt-repository -y ppa:deadsnakes/ppa
#     sudo apt-get update
#     sudo apt-get install -y python3.12 python3.12-venv python3.12-dev
# else
#     # On Ubuntu 24.04, the binary might exist but the venv module might be missing
#     if ! python3.12 -m venv --help &> /dev/null; then
#         echo "📦 Python 3.12 found but venv module is missing. Installing..."
#         sudo apt-get update && sudo apt-get install -y python3.12-venv
#     fi
# fi

# # 2. Ensure GDK Pixbuf tools are present (required for the Fedora SVG fix)
# if ! command -v gdk-pixbuf-query-loaders &> /dev/null; then
#     echo "🖼️  Installing GDK Pixbuf development tools..."
#     sudo apt-get update && sudo apt-get install -y libgdk-pixbuf2.0-dev
# fi

# 3. Version Extraction (Synchronized with Python source)
# Looking for APP_VERSION in Interfaces.py
APP_VER=$(sed -n 's/^APP_VERSION.*=.*["'\'']\([^"'\'']*\)["'\''].*/\1/p' ../photoglimmer/backend/Interfaces.py)
echo "📌 Target Version: $APP_VER"
export APP_VERSION=$APP_VER 

# 4. Virtual Environment Setup

if [ ! -d "appimage_venv" ]; then
    echo "🛠️ Creating virtual environment using Python 3.12..."
    # Use -m venv with the current python3.12
    python3.12 -m venv appimage_venv
fi

# if [ ! -d "appimage_venv" ]; then
#     echo "🛠️  Creating virtual environment using Python 3.12..."
#     python3.12 -m venv appimage_venv
# fi
source appimage_venv/bin/activate

# 5. Build Tooling Setup (Strict Versioning to avoid Ubuntu string crash)

pip install --quiet --upgrade pip
echo "📥 Installing AppImage build dependencies..."
pip install --quiet appimage-builder
# Force reinstall of packaging 20.9 to handle '1.21.1ubuntu2' versions
pip install --quiet --force-reinstall packaging==20.9
pip install --quiet pipdeptree==2.13.0

# 6. Execute Build
echo "🏗️  Starting appimage-builder..."
appimage-builder --recipe AppImageBuilder.yml

echo "✨ Success! Build finished."
