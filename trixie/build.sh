#!/usr/bin/env bash
# Build the flowy-trixie image on the ARM build server (FLOW-358/354).
#
# Stages three things into a source dir on the build server and runs the
# upstream rpi-image-gen there:
#   1. this directory's config + layer + overlay      (flowy-os/trixie)
#   2. the API server source                          (../flowy-app/server)
#   3. the built device-app + companion bundles       (../flowy-app/device-app/dist)
#
# Usage: trixie/build.sh [--skip-frontend]
set -euo pipefail

SERVER="${FLOWY_BUILDER:-builder@95.217.1.178}"
PASS="${FLOWY_BUILDER_PASS:-demo}"
HERE="$(cd "$(dirname "$0")" && pwd)"
APP_REPO="${FLOWY_APP_REPO:-$HERE/../../flowy-app}"

SSH=(sshpass -p "$PASS" ssh -o ConnectTimeout=10 "$SERVER")

log() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }

if [ "${1:-}" != "--skip-frontend" ]; then
  log "frontend build (device-app)"
  (cd "$APP_REPO/device-app" && npm run build >/dev/null)
fi

log "stage payloads"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/payload"
rsync -a --exclude .venv --exclude __pycache__ --exclude tests --exclude .pytest_cache \
  "$APP_REPO/server/" "$STAGE/payload/server/"
rsync -a "$APP_REPO/device-app/dist/" "$STAGE/payload/companion/"
rsync -a "$APP_REPO/device-app/dist/" "$STAGE/payload/kiosk/"
rsync -a "$HERE/flowy-trixie.yaml" "$HERE/layer" "$HERE/overlay" "$HERE/keys" "$HERE/raspotify.sources" "$STAGE/"

log "sync to build server"
tar --no-xattrs -C "$STAGE" -czf - . | "${SSH[@]}" 'rm -rf ~/flowy-image && mkdir -p ~/flowy-image && tar -mxzf - -C ~/flowy-image'

log "apt-keys naar rpi-image-gen keydir (work/keys wordt daaruit gevuld)"
"${SSH[@]}" 'mkdir -p ~/rpi-image-gen/keydir' 
tar --no-xattrs -C "$HERE/keys" -czf - . | "${SSH[@]}" 'tar -mxzf - -C ~/rpi-image-gen/keydir'

log "build image (rpi-image-gen, detached — overleeft ssh-drops)"
"${SSH[@]}" 'export PATH=/usr/sbin:/sbin:$PATH; cd ~/rpi-image-gen && rm -f ~/flowy-build.log ~/flowy-build.exit && setsid nohup sh -c "./rpi-image-gen build -S ~/flowy-image -c ~/flowy-image/flowy-trixie.yaml; echo \$? > ~/flowy-build.exit" > ~/flowy-build.log 2>&1 < /dev/null & echo build-gestart'

log "volgen tot afronding"
while ! "${SSH[@]}" 'test -f ~/flowy-build.exit' 2>/dev/null; do
  sleep 30
  "${SSH[@]}" 'tail -1 ~/flowy-build.log' 2>/dev/null || true
done
EXIT_CODE="$("${SSH[@]}" 'cat ~/flowy-build.exit')"
"${SSH[@]}" 'tail -5 ~/flowy-build.log'
[ "$EXIT_CODE" = "0" ] || { echo "BUILD FAILED ($EXIT_CODE) — zie ~/flowy-build.log op de server"; exit 1; }

log "artefact"
"${SSH[@]}" 'ls -lh ~/rpi-image-gen/work/*/flowy-trixie* 2>/dev/null || find ~/rpi-image-gen/work -name "*.img" -exec ls -lh {} \;'
echo "Download: scp $SERVER:<pad hierboven> ."
