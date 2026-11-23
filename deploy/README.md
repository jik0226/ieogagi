# 운영 문서 — 설치·백업·복구·업데이트

> 서버 1대에 Docker Compose로 Caddy(HTTPS)·앱·DB를 올리는 절차. 기획서 ❷ 6절·❸ 3절의 "설치·백업·복구·업데이트 절차 문서"에 해당한다.
> 2026-10-11 로컬 검증(macOS + colima, Docker 29.5 / Compose 5.6, 도메인 `localhost`): 빌드 → 기동 → `migrate` 정상 종료 → HTTPS 응답·CSP/HSTS 헤더 → 운영에서 `/api/docs` 404 → `admin`으로 센터 추가 → 시설장 가입·로그인 → Origin 없는 요청 403 → 위조한 `X-Forwarded-For`가 감사 로그에 남지 않음까지 확인. 실제 공인 도메인·인증서 발급은 서버를 정하면 확인한다. 같은 날 보안 리뷰 반영 후 재검증: 마이그레이션 0004까지 소유자 역할로 적용(btree_gist 생성 포함), 앱 역할의 컬럼 단위 권한 확인.
> 2026-10-17 리눅스 파일 권한 검증(colima VM 안의 리눅스 파일시스템, Docker 29.5 / Compose v5.1.4): 외부 점검 지적대로 0600 secret 파일은 uid 10001 컨테이너가 읽지 못했고, Compose 긴 문법의 `uid`·`gid`·`mode`도 무시됐다. 아래 방식(0640 + 0700 디렉터리 + `group_add`)으로 바꾼 뒤 새 볼륨에서 `db-init` 역할 생성 → `migrate` 정상 종료 → 앱 기동·로그인 경로 → `admin`(운영자 계정)으로 센터 추가·0600 초대 코드 파일까지 확인했다. 10/11 검증은 macOS 공유 폴더라 소유자 검사가 느슨해 이 문제가 드러나지 않았다.
> colima로 로컬 검증할 때는 `export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock`.

## 구성

```
인터넷 ─443─▶ web(Caddy: HTTPS·정적 SPA·/api 프록시) ─▶ app(FastAPI, ieogagi_app 역할) ─▶ db(PostgreSQL)
                         edge 네트워크 │ backend 네트워크(internal: 외부 통신 불가)
migrate(1회 실행): ieogagi_owner 역할로 alembic upgrade head
```

- 앱은 DB 소유자 권한이 없다. 스키마 변경은 `migrate`만, 앱 역할은 `audit_log`에 추가·조회만 할 수 있다.
- 앱·DB 컨테이너는 인터넷으로 나가지 못한다(runtime에 외부 호출이 없으므로).
- 앱 컨테이너: 읽기 전용 파일시스템, root 아님, 모든 capability 제거.
- uvicorn은 Caddy 주소(172.28.0.10)가 보낸 `X-Forwarded-For`만 믿는다. 감사 로그의 접속 IP는 이 값이다.
- 비밀 파일 권한: Swarm 없이 Compose는 secret 파일을 서버의 소유자·권한 그대로 연결한다. 그래서 파일은 0640(운영자 소유, 운영자 기본 그룹), 디렉터리 `deploy/secrets/`는 0700으로 두고, 다른 uid로 도는 `db`·`migrate`·`app`에만 그 그룹(`IEOGAGI_SECRETS_GID`)을 붙인다. 서버의 다른 계정은 디렉터리에 들어가지 못하고, 각 컨테이너에는 자기에게 필요한 secret만 연결된다. `db`는 처음부터 postgres 사용자로 돈다(root로 시작하면 공식 entrypoint가 postgres로 바꾸면서 추가 그룹을 버린다).
- DB 초기화 스크립트(`db-init/01-roles.sh`)는 역할 암호를 psql 명령행 인자로 넘기지 않는다. psql이 표준입력 스크립트 안에서 secret 파일을 직접 읽어 `ps`에 암호가 보이지 않는다.

## 1. 설치

1. 서버 준비: Docker Engine + Compose v2, 도메인 A 레코드가 서버를 가리키게, 80·443 포트 개방.
2. 코드 받기: `git clone` 후 저장소 루트로 이동.
3. 비밀값 만들기(서버에서, 저장소 밖으로 복사하지 않는다):

```bash
backend/.venv/bin/ieogagi-dev-secrets --dir deploy/secrets --db-host db --group-readable
```

   서버에 백엔드 개발 환경이 없으면 개발 PC에서 만든 뒤 안전한 경로(scp)로 옮기고 PC 사본은 지운다. 옮긴 뒤에는 `chmod 700 deploy/secrets && chmod 640 deploy/secrets/*`로 권한을 맞춘다. `deploy/secrets/`는 git에 올라가지 않는다. 파일 권한은 640, 디렉터리는 700이다(로컬 개발용 `backend/.secrets/`는 옵션 없이 600).
4. 환경 설정: `cp deploy/.env.example deploy/.env` 후 `IEOGAGI_DOMAIN`을 고치고, `IEOGAGI_SECRETS_GID`에 운영자 기본 그룹 번호(`id -g`)를 넣는다. 비밀 파일의 그룹이 이 번호여야 한다(`ls -ln deploy/secrets`).
5. 실행:

```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
```

6. 첫 센터와 시설장 초대 코드 만들기. 코드는 명령 출력(컨테이너 로그에 남는다)에 나오지 않고, 운영자만 읽을 수 있는 파일(0600)로만 나온다:

```bash
install -d -m 700 deploy/secrets/invites
docker compose -f deploy/docker-compose.yml --env-file deploy/.env --profile tools run --rm --user "$(id -u):$(id -g)" admin ieogagi-add-center "햇살지역아동센터"
# 출력: Center id=1 created; director invite id=1 issued ... Code written to /run/ieogagi-invites/director_invite_center1.txt
cat deploy/secrets/invites/director_invite_center1.txt   # 시설장에게 직접 전달(채팅·메일에 붙이지 않는다)
rm deploy/secrets/invites/director_invite_center1.txt
```

   센터 추가는 소유자 역할이 필요해, 평소에는 뜨지 않는 `admin` 서비스(profile `tools`)로 실행한다. `--user`는 결과 파일을 운영자 계정 소유로 만들기 위한 것이다. 명령은 남의 소유이거나 다른 사람이 쓸 수 있는 디렉터리에는 쓰지 않는다. 코드는 72시간 안에 한 번만 쓸 수 있다. 2026-10-13 외부 점검으로 바꾼 절차이고, Docker에서는 서버를 정한 뒤 다시 확인한다(로컬 개발에서는 `backend/.secrets/`에 같은 파일이 생긴다).

7. 확인: `https://<도메인>/api/health`가 `{"status":"ok"}`, `https://<도메인>/api/docs`는 404여야 한다(운영에서 문서 비공개).

**실제 아동 정보를 넣기 전 조건**(기획서 ❸ 6절): 외부 접속 계정의 안전한 인증수단(일회용 비밀번호 등)을 갖추기 전에는 가상 데이터로만 운영한다.

## 1-1. 서버 없이 임시 주소로 열기 (시연·팀원 테스트용, 준비만 해 둠)

> 2026-10-11 기준 **실행·설치하지 않았다**. 10/17 핵심 기능 보고 때 "팀원 접속 방법 1안"으로 올리고, 팀장 확인 후 디자인 담당의 실기기 확인(~10/18)·사용성 테스트·현장 검증 담당의 현장 시연에 쓴다. 비용 없음.

팀장 맥에서 개발 서버를 그대로 두고, 무료 터널로 HTTPS 임시 주소를 붙이는 방법이다. 후보는 계정 없이 쓰는 Cloudflare Quick Tunnel(`brew install cloudflared` 후 `cloudflared tunnel --url http://localhost:5173`, 실행할 때마다 `https://<무작위>.trycloudflare.com` 주소가 나온다). 순서: ① `make dev-backend`, `make dev-frontend` 실행 ② 터널을 열어 주소 확인 ③ `backend/.env`의 `IEOGAGI_ALLOWED_ORIGINS`에 그 주소를 추가하고 백엔드 재시작(없으면 로그인 같은 POST가 403) ④ Vite가 낯선 호스트를 막으므로 `frontend/vite.config.js`의 `server.allowedHosts`에 `.trycloudflare.com`을 임시로 추가 ⑤ 쓰고 나면 터널을 바로 닫고 ③④를 되돌린다. 지킬 것: **가상 시드 데이터만**(실제 아동 정보 금지, 기획서 ❸ 6절), 주소는 팀 채널에만 공유, 시연이 끝나면 `ieogagi-seed --reset`으로 데이터 초기화. 터널 주소는 HTTPS라 `__Host-` 보안 쿠키가 정상 동작한다. 맥이 잠자기에 들어가면 끊기니 시연 동안 전원 연결.

- **팀원 쪽 준비물**: 휴대폰·PC 브라우저(Chrome·Safari 최신)만 있으면 된다. 앱 설치·계정 가입 없음. 데모 계정은 팀장이 개인 메시지로 따로 전달(단체 대화방에 비밀번호를 올리지 않음).
- **한계와 2안**: 주소가 실행할 때마다 바뀌고 팀장 맥이 켜져 있어야 한다. 테스트 시간을 미리 정해 그 시간에만 연다. 시간이 맞지 않으면 2안은 팀원 PC에 저장소를 받아 README대로 로컬 실행(개발 환경 설치 필요, 디자인·공격 시나리오 담당은 1안 권장).

## 2. 백업

| 대상 | 방법 | 주기·보관 |
|---|---|---|
| DB | `docker compose exec -T db pg_dump -U postgres -Fc ieogagi > backup/ieogagi_$(date +%F).dump` | 매일, 14일 보관 후 덮어씀 |
| 메모 암호 키(`deploy/secrets/note_keyring`) | DB 백업과 **다른 곳**(오프라인 매체 등)에 사본 | 키를 바꿀 때마다 |
| 나머지 비밀값 | 분실 시 재발급 가능(세션 키를 바꾸면 모두 다시 로그인) | — |

- DB 백업에는 메모 원문이 암호문으로만 들어 있다. 키 없이 백업만 유출되면 원문을 읽을 수 없다.
- 파기한 아동의 기록은 백업 보관 주기(14일)가 지나 덮어써질 때 백업에서도 사라진다.

## 2-1. 보관 기간과 정기 정리 (2026-10-13 확정)

| 대상 | 보관 | 정리 방법 |
|---|---|---|
| 아동 정보·회차 기록·담당자 메모·공유 문구 | 아동이 센터 이용을 마치면 지체 없이 | 시설장이 화면에서 「파기」(되돌릴 수 없음). 백업에서는 14일 안에 사라진다 |
| 만료·폐기된 세션, 사용·만료된 초대 | 끝난 뒤 30일 | 주 1회 `ieogagi-cleanup` (아래) |
| 감사 로그, 아동 연결이 끊긴 배정 행, 비활성화된 계정 | 3년 | 연 1회 소유자 역할로 수동 정리(아래). 계정은 감사 로그가 ID로 가리키므로 감사 로그와 같은 시점에 정리 |
| 서버(컨테이너) 로그 | 용량 기준 10MB × 5개 | `docker-compose.yml`의 `x-logging`이 자동 회전 |

근거: 개인정보 보호법 제16조·제21조·제22조의2, 「개인정보의 안전성 확보조치 기준」 제5조 ③(권한 부여·변경·말소 내역 최소 3년)·제8조(접속기록 1년 이상, 민감정보 처리 시스템 2년 이상). 결정 기록은 `docs/보안설계.md` 5절.

```bash
# 주 1회: 끝난 지 30일이 지난 세션·초대 행 삭제 (먼저 --dry-run으로 건수 확인)
docker compose -f deploy/docker-compose.yml --env-file deploy/.env --profile tools run --rm admin ieogagi-cleanup --dry-run
docker compose -f deploy/docker-compose.yml --env-file deploy/.env --profile tools run --rm admin ieogagi-cleanup
```

- 앱 역할에는 이 표들의 DELETE 권한이 없어서, 정리는 소유자 역할로 도는 `admin` 서비스에서만 한다.
- 3년 정리는 실수로 지우면 되돌릴 수 없어 명령으로 만들지 않았다. 연 1회 백업을 먼저 받은 뒤 소유자 역할로 `created_at`이 3년 지난 `audit_log` 행, 아동 연결이 끊기고(`child_id IS NULL`) 회수·종료된 지 3년 지난 `assignment` 행, 비활성화된 지 3년 지난 계정을 정리한다.

## 3. 복구

```bash
docker compose -f deploy/docker-compose.yml stop app
docker compose -f deploy/docker-compose.yml exec -T db pg_restore -U postgres -d ieogagi --clean --if-exists < backup/ieogagi_YYYY-MM-DD.dump
docker compose -f deploy/docker-compose.yml start app
```

복구 후 메모 원문 열람이 되는지 확인한다(키링이 백업 시점의 `key_id`를 포함해야 한다).

## 4. 업데이트

```bash
git pull && docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
```

`migrate`가 먼저 돌아 스키마를 올린 뒤 앱이 뜬다. 업데이트 전에는 2절 방법으로 DB를 백업한다. 의존성은 해시 고정 lock으로만 설치되므로, lock 파일이 바뀐 커밋은 리뷰를 거친다.

## 5. 키 교체 (메모 암호 키)

1. `note_keyring`의 `keys`에 새 키(`k2`, 32바이트 base64)를 추가하고 `active`를 `k2`로 바꾼다. 기존 `k1`은 지우지 않는다.
2. 앱 재시작. 새 메모는 `k2`로 암호화되고, 기존 메모는 저장된 `key_id`(`k1`)로 계속 복호화된다.
3. (선택) 모든 메모를 `k2`로 다시 암호화한 뒤에만 `k1`을 지운다. 재암호화 명령은 아직 없다.

## 6. 운영 점검 (시설장 운영 절차)

- **월 1회** 감사 로그 점검: 담당자 화면 → 감사 로그에서 `access.denied`(차단), `user.disable`, `assignment.revoke`, `note.view` 확인. (개인정보 안전성 확보조치 기준 제8조 접속기록 점검)
- 담당자 화면의 "배정이 끝난 활성 계정"을 확인해 비활성화한다.
- 감사 로그는 최소 3년 보관한다(제5조 ③). 앱 역할은 감사 로그를 지울 수 없고, 3년이 지난 기록 정리는 DB 관리자가 소유자 역할로만 한다.
- DB 관리자 접근(소유자·postgres 역할)은 서버 관리자 1~2명으로 제한하고, 접근 시 사유를 운영 일지에 남긴다.
