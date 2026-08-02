#!/usr/bin/env bash
# Build and zip Drawing Coach binary for Linux or macOS.
set -euo pipefail

PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')"
VERSION="$(python scripts/build_version.py | sed -n 's/^Version set to: //p')"

echo "Building Drawing Coach ${VERSION} for ${PLATFORM}..."

pyinstaller --clean --noconfirm drawing_coach.spec

DIST_DIR="dist/drawing-coach"
ZIP_NAME="drawing-coach-${VERSION}-${PLATFORM}.zip"

if [[ "${PLATFORM}" == "darwin" ]]; then
    DIST_DIR="dist/Drawing Coach.app"
    ZIP_NAME="drawing-coach-${VERSION}-macos.zip"
    cd dist
    zip -r "../${ZIP_NAME}" "Drawing Coach.app"
    cd ..
else
    cd dist
    zip -r "../${ZIP_NAME}" drawing-coach
    cd ..
fi

echo "Created ${ZIP_NAME}"
