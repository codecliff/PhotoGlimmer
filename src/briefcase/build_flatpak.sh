#!/bin/bash
set -e

# 1. Path Logic
# This script is in src/briefcase/, so BRIEFCASE_DIR is $(pwd)
BRIEFCASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# src/ is one level up
SRC_DIR="$(dirname "$BRIEFCASE_DIR")"
# Project root is two levels up
PROJECT_ROOT="$(dirname "$SRC_DIR")"


echo "BRIEFCASE_DIR is $BRIEFCASE_DIR"

echo "SRC_DIR is $SRC_DIR"

echo "PROJECT_ROOT is $PROJECT_ROOT"





echo "📦 Building PhotoGlimmer Builder Image..."
# We use SRC_DIR as the build context so it can see photoglimmer/ and briefcase/
docker build -t photoglimmer-builder -f "$BRIEFCASE_DIR/Dockerfile.flatpak" "$SRC_DIR"

echo "🏗️ Starting containerized Briefcase build..."
# Mount the local 'src/' folder to '/project' inside the container
docker run --rm -it \
    --privileged \
    --device /dev/fuse \
    --cap-add SYS_ADMIN \
    --env HOME=/root \
    --env PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    -v "$SRC_DIR:/project" \
    photoglimmer-builder \
    briefcase package linux flatpak
    

echo "✨ Flatpak build complete! Check src/briefcase/linux/ for the output."

