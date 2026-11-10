#!/bin/zsh
# Publica la versión que dice ghl.py: tag + release en GitHub con el zip, y luego version.json
# (que es lo que leen las instalaciones para saber que hay versión nueva). Solo para quien mantiene el repo.
set -e
cd "$(dirname "$0")/.."
REPO=ervin-mo/ghl-marketing-agentico
N=ghl-marketing-agentico
V=$(python3 -c "import re;print(re.search(r'VERSION = \"([^\"]+)\"', open('ghl.py').read()).group(1))")
[[ -n "$(git status --porcelain)" ]] && { echo "⛔ Hay cambios sin commitear. Commitea primero."; exit 1; }
gh release view "v$V" -R $REPO >/dev/null 2>&1 && { echo "⛔ La v$V ya está publicada. Sube VERSION en ghl.py."; exit 1; }
grep -q "^## $V " CHANGELOG.md || { echo "⛔ Falta la sección «## $V » en CHANGELOG.md."; exit 1; }
# notas = la sección de esta versión en el CHANGELOG
NOTAS=$(python3 - "$V" <<'PY'
import re, sys
t = open("CHANGELOG.md", encoding="utf-8").read()
m = re.search(r"^## " + re.escape(sys.argv[1]) + r" .*?\n(.*?)(?=^## |\Z)", t, re.S | re.M)
print(m.group(1).strip())
PY
)
zsh scripts/empaquetar.sh
SHA=$(shasum -a 256 dist/$N-$V.zip | cut -d' ' -f1)
git tag -a "v$V" -m "v$V"
git push origin main "v$V"
gh release create "v$V" -R $REPO --title "v$V" --notes "$NOTAS" "dist/$N-$V.zip" "dist/$N.zip"
python3 - "$V" "$SHA" "$NOTAS" <<'PY'
import json, sys, datetime
v, sha, notas = sys.argv[1:4]
json.dump({"version": v, "publicada": datetime.date.today().isoformat(),
           "zip": f"https://github.com/ervin-mo/ghl-marketing-agentico/releases/download/v{v}/ghl-marketing-agentico-{v}.zip",
           "sha256": sha, "notas": notas}, open("version.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
PY
git add version.json
git commit -q -m "Publica v$V"
git push origin main
echo "✅ v$V publicada. Las instalaciones la verán en su próxima revisión (máximo 24 h, o al momento con: ghl.py actualizar)."
