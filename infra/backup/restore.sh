#!/usr/bin/env bash
# 백업 덤프 복원.
#
#   ./infra/backup/restore.sh backups/tree-for-study-XXXX.dump --verify
#       → 별도 임시 DB(restore_check)에 복원해 테이블·행 수를 확인하고 지운다(운영 데이터 무변경).
#   ./infra/backup/restore.sh backups/tree-for-study-XXXX.dump --replace
#       → 운영 DB를 덤프 내용으로 교체한다. backend를 멈추고, 교체 전 현재 DB를 한 번 더 백업한다.
#         되돌릴 수 없는 작업이므로 'RESTORE'를 직접 입력해야 진행한다.
set -euo pipefail
cd "$(dirname "$0")/../.."

DUMP="${1:?덤프 파일 경로가 필요합니다}"
MODE="${2:---verify}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.production.yaml}"
DC="docker compose -f $COMPOSE_FILE"

[ -s "$DUMP" ] || { echo "덤프 파일이 없습니다: $DUMP" >&2; exit 1; }
if [ -f "$DUMP.sha256" ]; then sha256sum -c "$DUMP.sha256" >/dev/null && echo "checksum ok"; fi

psql_db() { $DC exec -T db sh -c "psql -v ON_ERROR_STOP=1 -U \"\$POSTGRES_USER\" -d $1 -tA -c \"$2\""; }

case "$MODE" in
  --verify)
    psql_db postgres "DROP DATABASE IF EXISTS restore_check"
    psql_db postgres "CREATE DATABASE restore_check"
    $DC exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d restore_check --no-owner --exit-on-error' < "$DUMP"
    echo "restore_check 테이블별 행 수:"
    for t in users focus_sessions trees community_placements daily_entries goals timetable_blocks wbs_tasks weekly_reviews attendance; do
      printf '  %-22s %s\n' "$t" "$(psql_db restore_check "SELECT count(*) FROM $t")"
    done
    printf '  %-22s %s\n' "alembic_version" "$(psql_db restore_check "SELECT version_num FROM alembic_version")"
    psql_db postgres "DROP DATABASE restore_check"
    echo "verify ok (운영 DB는 변경하지 않았습니다)"
    ;;
  --replace)
    read -r -p "운영 DB를 $DUMP 내용으로 교체합니다. 계속하려면 RESTORE 입력: " answer
    [ "$answer" = "RESTORE" ] || { echo "취소했습니다."; exit 1; }
    ./infra/backup/backup.sh
    $DC stop backend
    $DC exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --exit-on-error' < "$DUMP"
    $DC start backend
    echo "replace ok"
    ;;
  *)
    echo "사용법: $0 <dump> [--verify|--replace]" >&2
    exit 1
    ;;
esac
