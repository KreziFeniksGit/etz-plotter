#!/bin/sh
# Install FreeCAD 1.0.2 without root (Linux x86_64, also cloud sessions where pip/apt are blocked):
# downloads the AppImage from GitHub releases and extracts it to ~/tools/freecad. Then ./fcpy works.
set -e
mkdir -p "$HOME/tools/freecad" && cd "$HOME/tools/freecad"
URL=$(curl -sL -A "Mozilla/5.0" https://api.github.com/repos/FreeCAD/FreeCAD/releases/tags/1.0.2 \
      | grep -o '"browser_download_url": *"[^"]*Linux-x86_64[^"]*\.AppImage"' | head -1 | sed 's/.*"\(http[^"]*\)"/\1/')
[ -n "$URL" ] || { echo "Could not find the AppImage URL; download FreeCAD 1.0.2 Linux x86_64 AppImage by hand into $PWD"; exit 1; }
curl -L -A "Mozilla/5.0" -o FreeCAD.AppImage "$URL"
chmod +x FreeCAD.AppImage && ./FreeCAD.AppImage --appimage-extract >/dev/null
echo "FreeCAD extracted to $PWD/squashfs-root/usr"
