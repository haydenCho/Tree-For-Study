# EC2 배포·백업·운영 절차

로컬에서 운영 스택(compose.production.yaml + Caddy)을 띄워 검증한 절차를 EC2에 그대로 적용한다.
실제 EC2 접속·배포·DNS 설정은 운영자가 직접 수행한다(Claude Code는 서버에 접속하지 않았다).

## 1. 서버 준비
1. EC2(예: t3.small, Ubuntu 24.04, 20GB gp3). 탄력적 IP를 붙인다.
2. 보안 그룹: 인바운드 80/443(0.0.0.0/0, ::/0), 22는 운영자 IP만. 5432·8000은 열지 않는다.
3. Docker Engine + Compose 플러그인 설치, 운영 계정을 docker 그룹에 추가.
4. 백업을 S3에 둘 경우 EC2에 S3 쓰기만 허용하는 IAM Role을 연결하고 `aws` CLI를 설치한다(액세스 키 파일 금지).
5. DNS: 도메인 A(필요하면 AAAA) 레코드를 탄력적 IP로 지정한다.

## 2. 첫 배포
```bash
git clone <저장소> /srv/tree-for-study && cd /srv/tree-for-study
cp .env.example .env && chmod 600 .env
# .env 편집: POSTGRES_PASSWORD, DATABASE_URL(같은 비밀번호), JWT_SECRET(아래 명령), SITE_ADDRESS, APP_ORIGIN=https://<도메인>
python3 -c "import secrets;print(secrets.token_urlsafe(48))"   # JWT_SECRET용, 화면 기록이 남지 않게 주의
docker compose -f compose.production.yaml up -d --build
docker compose -f compose.production.yaml ps            # backend healthy 확인
curl -fsS https://<도메인>/api/ready                     # {"status":"ready",...}
```
- backend는 시작 시 `alembic upgrade head`를 자동 적용한다.
- 운영 설정이 안전하지 않으면(짧은 JWT_SECRET, COOKIE_SECURE=false, http APP_ORIGIN, TRUSTED_PROXY_IPS 없음) backend가 시작을 거부한다.
- TRUSTED_PROXY_IPS는 compose가 Caddy 고정 IP(172.30.0.10)로 넣는다. 네트워크 대역을 바꾸면 compose의 두 값을 함께 바꾼다.

## 3. 운영자·멤버 준비
```bash
docker compose -f compose.production.yaml exec backend python -m app.cli create-operator --email <운영자 이메일> --real-name <실명>
docker compose -f compose.production.yaml exec backend python -m app.cli create-invite --max-uses 10 --ttl-days 7
```
초대 코드는 한 번만 출력된다. 멤버는 가입 후 '승인 대기' 상태이며 운영자가 /admin에서 실제 멤버와 대조해 승인한다.

## 4. 도서관 IP 등록(현장, docs/05-library-ip.md)
1. 운영자 PC를 도서관 Wi-Fi에 연결하고 VPN을 끈다.
2. /admin → '서버가 본 접속 IP'를 확인('프록시 경유' 표시가 함께 보여야 한다).
3. '현재 접속 IP 채우기' → 등록. 다른 PC/휴대폰에서도 같은 Wi-Fi로 인식되는지 대시보드의 도서관 안내로 확인.
4. 다음 방문일에도 다시 확인하고, 공인 IP가 바뀌면 갱신한다. 확인하지 않은 넓은 범위는 등록하지 않는다(/24·/56보다 넓으면 거부).

## 5. 백업과 복원
```bash
./infra/backup/backup.sh                                      # backups/에 덤프 + sha256, 14일 보관
BACKUP_S3_URI=s3://<버킷>/tree-for-study ./infra/backup/backup.sh   # 외부 사본
./infra/backup/restore.sh backups/<파일>.dump --verify        # 임시 DB에 복원해 행 수 확인(운영 무변경)
./infra/backup/restore.sh backups/<파일>.dump --replace       # 운영 DB 교체(RESTORE 입력, 교체 전 자동 백업)
```
cron(매일 04:30 KST 서버 시간대 기준):
```
30 4 * * * cd /srv/tree-for-study && BACKUP_S3_URI=s3://<버킷>/tree-for-study ./infra/backup/backup.sh >> backups/backup.log 2>&1
```
매주 한 번 `--verify`로 복원 리허설을 하고 결과를 기록한다. 덤프에는 개인 데이터가 있으므로 S3 버킷은 비공개·암호화로 둔다.

## 6. 업데이트·재시작
```bash
git pull && docker compose -f compose.production.yaml up -d --build
```
- 진행 중 집중 세션은 DB의 목표 시각으로 판정하므로 backend 재시작 후에도 완료 워커가 이어서 확정한다(로컬 검증 완료).
- 업데이트 전 `backup.sh`를 먼저 실행한다.
- 운영 스모크: `PROD_BASE_URL=https://<도메인> OP_EMAIL=... OP_PASSWORD=... npx playwright test --config prod.config.js` (e2e/ 폴더, 읽기 위주).

## 7. 점검 체크리스트(배포 직후)
- [ ] `https://<도메인>` 인증서 정상, http → https 리디렉트
- [ ] `/api/ready` 200, `/api/docs` 404(운영에서 문서 비공개)
- [ ] 외부에서 5432·8000 접속 불가(`nc -zv <IP> 5432` 실패)
- [ ] 로그인 → 새로고침 후 로그인 유지(refresh 쿠키 Secure·HttpOnly)
- [ ] 도서관 Wi-Fi에서 진단 IP 확인·등록 → 세션 시작 시 장식 표시
- [ ] 백업 1회 실행 + `--verify` 성공, S3 사본 확인
