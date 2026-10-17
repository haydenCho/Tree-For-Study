#!/usr/bin/env bash
# 브라우저 E2E 실행기. 개발 DB와 분리된 tfs-e2e 프로젝트로 스택을 띄우고 끝나면 정리한다.
# 운영자 비밀번호는 매 실행마다 난수로 만들고 화면에 출력하지 않는다.
set -euo pipefail
cd "$(dirname "$0")/.."
P="docker compose -p tfs-e2e -f compose.yaml -f compose.e2e.yaml"

cleanup() { if [ "${KEEP:-0}" != "1" ]; then $P --profile e2e down -v >/dev/null 2>&1 || true; fi; }
trap cleanup EXIT

$P up -d --build db backend frontend
echo "백엔드 준비 대기…"
for _ in $(seq 1 60); do
  if $P exec -T backend curl -fsS http://localhost:8000/api/ready >/dev/null 2>&1; then break; fi
  sleep 2
done

OP_EMAIL="operator-$(date +%s)@e2e.local"
OP_PASSWORD="$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 20)"
echo "$OP_PASSWORD" | $P exec -T backend python -m app.cli create-operator --email "$OP_EMAIL" --real-name "운영자" --display-name "숲지기" >/dev/null
INVITE_CODE="$($P exec -T backend python -m app.cli create-invite --max-uses 10 --label e2e | sed -n 's/^초대 코드(한 번만 표시): //p')"

$P --profile e2e run --rm -T \
  -e OP_EMAIL="$OP_EMAIL" -e OP_PASSWORD="$OP_PASSWORD" -e INVITE_CODE="$INVITE_CODE" \
  e2e sh -c "npm install --no-audit --no-fund --silent && npx playwright test $*"
