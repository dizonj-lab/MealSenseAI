#!/usr/bin/env bash
# Assemble the self-contained NUS submission from version-controlled files only.
#   ./scripts/make_submission.sh [output-dir]      -> <output-dir>/MealSenseAI-NUS-Submission (+ .zip)
# Excludes: training datasets, virtual environments, caches, .env/credentials, home-server hosting files.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-dist}"; PKG="$OUT/MealSenseAI-NUS-Submission"
rm -rf "$PKG"; mkdir -p "$PKG"
INCLUDE=(backend frontend datasets/nutrition ml/models/exp002 ml/models/yolo11n-seg.onnx ml/export ml/evaluation
         ml/training database docs scripts infrastructure/e2e.Dockerfile docker-compose.yml docker-compose.gpu.yml
         docker-compose.offline.yml docker-compose.test.yml .env.example .gitignore .dockerignore requirements.txt
         requirements-dev.txt README.md)
git ls-files -z -- "${INCLUDE[@]}" | grep -zv -E '^(scripts/make_submission\.sh)$' \
  | xargs -0 -I{} sh -c 'mkdir -p "$1/$(dirname "$2")" && cp -p "$2" "$1/$2"' _ "$PKG" {}
# README for the package (no links to development-only hosting docs)
sed -i '/HOME-SERVER.md/d; s#`0x-\*/` project report sections.#`evidence/` test results.#' "$PKG/README.md"
# evidence: model evidence + latest test results (if present)
mkdir -p "$PKG/evidence"
cp -r ml/models/exp002/evidence "$PKG/evidence/model"
[ -d test-results ] && { mkdir -p "$PKG/evidence/tests"; cp test-results/*.json test-results/*.log "$PKG/evidence/tests/" 2>/dev/null || true;
  [ -d test-results/screenshots ] && cp -r test-results/screenshots "$PKG/evidence/tests/"; }
# safety checks: nothing secret or heavy slipped in
! find "$PKG" \( -name .env -o -name '*.pem' -o -name 'id_*' -o -name node_modules -o -name .venv -o -name __pycache__ -o -name '*.pt' \) | grep -q . \
  || { echo "forbidden files in package"; exit 1; }
grep -rIl --exclude-dir=evidence -E 'sk-ant-|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH) PRIVATE' "$PKG" && { echo "possible secret found"; exit 1; } || true
( cd "$PKG" && find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256 )
( cd "$OUT" && rm -f MealSenseAI-NUS-Submission.zip && zip -qr MealSenseAI-NUS-Submission.zip MealSenseAI-NUS-Submission )
du -sh "$PKG" "$OUT/MealSenseAI-NUS-Submission.zip"; echo "files: $(wc -l < "$PKG/MANIFEST.sha256")"
