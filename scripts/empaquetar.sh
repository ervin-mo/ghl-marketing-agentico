#!/bin/zsh
# Arma dist/ghl-marketing-agentico-<versión>.zip con SOLO lo que va a los clientes (sin .git, sin informes ni exportes).
set -e
cd "$(dirname "$0")/.."
V=$(python3 -c "import re;print(re.search(r'VERSION = \"([^\"]+)\"', open('ghl.py').read()).group(1))")
N=ghl-marketing-agentico
rm -rf dist && mkdir -p dist/$N
git ls-files -z | xargs -0 -I{} rsync -aR {} dist/$N/
rm -rf dist/$N/scripts dist/$N/version.json
# Revisión de seguridad: ningún token dentro del paquete
if grep -rIlE "pit-[A-Za-z0-9-]{20,}|Bearer [A-Za-z0-9._-]{20,}" dist/$N; then echo "⛔ hay un token en el paquete"; exit 1; fi
(cd dist && zip -qr -X $N-$V.zip $N && cp $N-$V.zip $N.zip)
echo "✅ dist/$N-$V.zip  ($(du -h dist/$N-$V.zip | cut -f1))  · copia sin versión: dist/$N.zip"
