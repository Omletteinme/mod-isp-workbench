#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 "$ROOT_DIR/scripts/build_vercel_site.py"
DEPLOY_DIR=$(mktemp -d "${TMPDIR:-/tmp}/mod-isp-vercel.XXXXXX")
trap 'rm -rf "$DEPLOY_DIR"' EXIT HUP INT TERM
cp -R "$ROOT_DIR/dist/." "$DEPLOY_DIR/"
vercel deploy "$DEPLOY_DIR" --project mod-isp-workbench --prod --yes
