#!/bin/sh
set -eu
if [ "$#" != 2 ]; then
    echo "Usage: $0 SOURCE_DIRECTORY OUTPUT_DIRECTORY" >&2
    exit 2
fi
source=$(cd "$1" && pwd)
mkdir -p "$2"
output=$(cd "$2" && pwd)
root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
docker build -t synaxe-deb-builder "$root"
docker run --rm -v "$source:/source:ro" -v "$output:/output" synaxe-deb-builder sh -ec '
    cp -a /source/. /build/package
    cd /build/package
    chmod +x debian/rules
    dpkg-buildpackage --no-sign -b
    lintian --fail-on error ../*.changes
    cp ../*.deb ../*.changes ../*.buildinfo /output/
'
