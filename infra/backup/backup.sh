#!/usr/bin/env bash
# PostgreSQL 일일 백업. 운영 서버(EC2)의 저장소 루트에서 실행한다.
#
#   ./infra/backup/backup.sh                 # backups/ 에 덤프 생성 + 보관 기간 지난 파일 정리
#   BACKUP_S3_URI=s3://버킷/경로 ./infra/backup/backup.sh   # 외부(S3) 사본도 업로드
#
# - pg_dump custom 형식(-Fc)으로 db 컨테이너 안에서 덤프해 호스트로 스트리밍한다(비밀번호 미출력).
# - 덤프에는 개인 데이터가 있으므로 backups/ 권한을 700으로 두고 git에 올리지 않는다(.gitignore).
# - cron 예: 30 4 * * * cd /srv/tree-for-study && ./infra/backup/backup.sh >> backups/backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/../.."

COMPOSE_FILE="${COMPOSE_FILE:-compose.production.yaml}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
DIR="backups"
mkdir -p "$DIR" && chmod 700 "$DIR"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$DIR/tree-for-study-$STAMP.dump"

docker compose -f "$COMPOSE_FILE" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner' > "$OUT.partial"
# 덤프가 비었거나 형식이 깨졌으면 실패로 처리한다.
if [ ! -s "$OUT.partial" ] || ! head -c 5 "$OUT.partial" | grep -q PGDMP; then
  echo "backup failed: empty or invalid dump" >&2
  rm -f "$OUT.partial"
  exit 1
fi
mv "$OUT.partial" "$OUT"
chmod 600 "$OUT"
sha256sum "$OUT" > "$OUT.sha256"
echo "backup ok: $OUT ($(du -h "$OUT" | cut -f1))"

if [ -n "${BACKUP_S3_URI:-}" ]; then
  # EC2 인스턴스 역할(IAM Role)로 인증한다. 액세스 키를 파일에 두지 않는다.
  aws s3 cp "$OUT" "$BACKUP_S3_URI/" --only-show-errors --sse AES256
  aws s3 cp "$OUT.sha256" "$BACKUP_S3_URI/" --only-show-errors --sse AES256
  echo "uploaded to $BACKUP_S3_URI"
fi

find "$DIR" -name 'tree-for-study-*.dump*' -mtime +"$RETENTION_DAYS" -delete
