# 이어가기 API 설계 (계약서)

> 프론트엔드(디자인 담당)와 백엔드가 같이 보는 계약 문서. 실제 스키마의 정본은 백엔드가 내보낸 `docs/api/openapi.json`이고, 이 문서는 사람이 읽는 요약이다. 둘이 다르면 openapi.json이 맞다. 바꿀 일이 있으면 이 문서부터 고친다.

## 공통 규칙

- 모든 API는 `/api` 아래. 응답은 JSON(UTF-8). 날짜는 `YYYY-MM-DD`(한국 날짜), 시각은 ISO 8601(UTC, 예: `2026-10-11T05:30:00Z`).
- **인증**: 로그인하면 서버가 `__Host-ieogagi_session` 쿠키(HttpOnly·Secure·SameSite=Strict·Path=/, Max-Age=유휴 만료 10분)를 내려주고, 인증된 응답마다 같은 토큰으로 Max-Age를 다시 내려준다(2026-11-05 진단 02.10 조치). 프론트는 쿠키를 읽을 수 없고 읽을 필요도 없다. `fetch(url, { credentials: "same-origin" })`로 보내기만 한다. 토큰을 localStorage에 저장하지 않는다.
- **같은 출처**: 개발 중엔 Vite 프록시(`/api` → `http://localhost:8000`), 배포 땐 Caddy가 SPA와 API를 같은 도메인으로 낸다. CORS는 열지 않는다.
- **CSRF**: 상태를 바꾸는 요청(POST·PUT·PATCH·DELETE)은 브라우저가 붙이는 `Origin` 헤더가 허용 목록에 있어야 한다. 브라우저 `fetch`는 자동으로 붙이므로 프론트가 할 일은 없다.
- **세션 만료**: 유휴 10분, 절대 8시간. 만료·폐기·계정 비활성화면 401 → 프론트는 로그인 화면으로 보낸다.
- **권한**: 역할은 `director`(시설장) · `staff`(담당자) · `mentor`(멘토). 권한이 없거나 배정 기간 밖이면 403.

### 오류 응답 형식 (모든 오류 공통)

```json
{ "error": { "code": "FORBIDDEN", "message": "접근 권한이 없습니다." } }
```

| HTTP | code | 언제 | 프론트 처리 |
|---|---|---|---|
| 401 | `UNAUTHENTICATED` | 쿠키 없음·세션 만료·비활성 계정 | 로그인 화면으로 |
| 401 | `LOGIN_FAILED` | 아이디·비밀번호 틀림 또는 잠김(문구 동일) | message 그대로 표시 |
| 403 | `FORBIDDEN` | 역할 부족, 다른 센터, 배정 기간 밖, 회수됨 | "열람 기간이 아니거나 권한이 없습니다" 안내 |
| 404 | `NOT_FOUND` | 대상 없음 | |
| 409 | `CONFLICT` | 아이디 중복, 이미 정정된 기록, 같은 멘토·아동의 기간 겹치는 배정, 이미 회수·비활성화 등 | message 표시 |
| 413 | `REQUEST_TOO_LARGE` | 요청 본문 64KB 초과 | 일반 오류 안내 |
| 422 | `VALIDATION_FAILED` | 입력 형식 오류. `fields`: 문제 필드 경로 문자열 배열(예: `["body.password"]`). 서버가 정한 안내 문구가 있으면 `message`에 담김 | 해당 필드 표시 |
| 422 | `SENSITIVE_CONFIRM_REQUIRED` | 회차 기록에 건강·가정 관련 단어. `categories`: `["health","family"]` 중 | 확인창 → `sensitive_confirmed: true`로 다시 보냄 |
| 422 | `SENSITIVE_BASIS_REQUIRED` | 민감정보 확인 전 아동에 메모 원문 작성 | 안내 |
| 429 | `RATE_LIMITED` | 요청 과다(로그인·초대 코드 확인) | 잠시 후 재시도 안내 |
| 500 | `INTERNAL_ERROR` | 서버 오류(내부 정보는 절대 내려가지 않음) | 일반 오류 안내 |

## 엔드포인트 (27개)

표의 `권한` 칸: 공개 = 로그인 불필요, D = 시설장, S = 담당자, M = 멘토, M* = 멘토이면서 해당 아동의 **배정 기간 안**(같은 센터 ∧ 본인 배정 ∧ 시작일 ≤ 오늘 ≤ 종료일 ∧ 미회수).

### 인증 (F1)

| # | 메서드·경로 | 권한 | 요청 | 응답 |
|---|---|---|---|---|
| 1 | `POST /api/auth/invites/verify` | 공개(IP 제한) | `{code}` | 200 `{role, center_name, expires_at}` / 404 |
| 2 | `POST /api/auth/signup` | 공개(IP 제한) | `{code, login_id, display_name, password}` | 201 `Me` |
| 3 | `POST /api/auth/login` | 공개(IP 제한) | `{login_id, password}` | 200 `Me` + Set-Cookie / 401 `LOGIN_FAILED` |
| 4 | `POST /api/auth/logout` | 공개 | – | 204 (세션이 살아 있으면 폐기, 쿠키는 항상 삭제) |
| 5 | `GET /api/auth/me` | 로그인 | – | 200 `Me` |

- `login_id`: 영문 소문자·숫자·`_` 4~32자. `display_name`: 1~30자(한글·영문·숫자·공백·`.`·`-`·`_`).
- `password`: 10~128자, 영문 대문자·영문 소문자·숫자·특수문자 중 2종류 이상.
- 로그인 5회 연속 실패 시 15분 잠금. 실패·잠금 응답 문구는 같다.
- 가입 후 자동 로그인하지 않는다(가입 → 로그인 화면).

### 계정 (F1·F9)

| # | 메서드·경로 | 권한 | 요청 | 응답 |
|---|---|---|---|---|
| 6 | `POST /api/invites` | D·S | `{role: "staff" \| "mentor"}` | 201 `{code, role, expires_at}` (코드는 이때 한 번만 보임) |
| 7 | `GET /api/users` | D·S | – | 200 `UserSummary[]` |
| 8 | `POST /api/users/{user_id}/disable` | D·S | – | 200 `UserSummary` |

- `staff` 초대는 시설장만. 담당자는 멘토만 비활성화할 수 있고, 시설장은 담당자·멘토를 비활성화할 수 있다(자기 자신 불가). 비활성화하면 그 사람의 세션이 모두 폐기된다.
- `UserSummary.assignment_ended`가 `true`면 "배정이 끝난 활성 계정" → 담당자 화면에 강조 표시.

### 아동·배정 (F2·F3·F8)

| # | 메서드·경로 | 권한 | 요청 | 응답 |
|---|---|---|---|---|
| 9 | `POST /api/children` | D·S | `{alias, grade, privacy_consent_confirmed: true, sensitive_basis_confirmed}` | 201 `Child` |
| 10 | `GET /api/children` | D·S | – | 200 `Child[]` |
| 11 | `POST /api/children/{child_id}/sensitive-basis` | D·S | – | 200 `Child` |
| 12 | `DELETE /api/children/{child_id}` | D | – | 204 (기록·메모·배정까지 파기, 감사 로그는 남음) |
| 13 | `POST /api/assignments` | D·S | `{mentor_id, child_id, start_date, end_date}` | 201 `Assignment` |
| 14 | `GET /api/assignments?child_id=&mentor_id=` | D·S | – | 200 `Assignment[]` |
| 15 | `POST /api/assignments/{assignment_id}/revoke` | D·S | – | 200 `Assignment` |

- `alias`: 1~20자 별칭(실명 금지 안내). `grade`: `"초1"`~`"초6"`, `"중1"`~`"중3"`, `"고1"`~`"고3"`.
- `privacy_consent_confirmed`는 반드시 `true`여야 등록된다. 민감정보 확인은 나중에 #11로 해도 된다.
- 배정: `start_date ≤ end_date`, 기간 최대 366일. 멘토·아동이 같은 센터여야 한다.

### 멘토 홈·인계 카드·회차 기록 (F4·F5·F6·F8)

| # | 메서드·경로 | 권한 | 요청 | 응답 |
|---|---|---|---|---|
| 16 | `GET /api/me/assignments` | M | – | 200 `MyAssignment[]` (진행 중 + 시작 전) |
| 17 | `GET /api/children/{child_id}/handover-card` | M* | – | 200 `HandoverCard` |
| 18 | `GET /api/children/{child_id}/records` | M* · D·S | – | 200 `MentorRecord[]`(멘토) / `StaffRecord[]`(담당자·시설장) |
| 19 | `POST /api/children/{child_id}/records` | M* | `{session_date, did, stuck, next_step, sensitive_confirmed}` | 201 `MentorRecord` / 422 `SENSITIVE_CONFIRM_REQUIRED` |
| 20 | `POST /api/records/{record_id}/corrections` | M*(본인 기록) | `{did, stuck, next_step, sensitive_confirmed}` | 201 `MentorRecord` |
| 21 | `POST /api/records/{record_id}/hide` | D·S | `{reason_code}` | 200 `StaffRecord` |
| 22 | `POST /api/records/{record_id}/redact` | D·S | `{fields: ["did" \| "stuck" \| "next_step", ...]}` | 200 `StaffRecord` |

- 멘토가 #18에서 받는 것: **배정 기간 중 자기가 쓴 기록**만(숨김·정정 전 원본 제외). 다른 멘토 기록은 #17 인계 카드로만 본다.
- 인계 카드: 배정 시작일 **이전** 기록 중 최근 4회(숨김·정정 전 원본 제외) + 담당자가 쓴 공유 문구.
- `session_date`: 배정 기간 안이고 오늘 이후가 아니어야 한다.
- `did`·`stuck`·`next_step`: 각 0~500자, 세 칸 중 하나 이상 입력.
- 기록은 덮어쓰지 않는다. 정정은 새 기록으로 쌓이고, 한 기록은 한 번만 정정할 수 있다(정정본을 다시 정정하는 건 가능).
- `reason_code`: `INAPPROPRIATE`(부적절) · `WRONG_CHILD`(다른 아동 기록) · `DUPLICATE`(중복) · `SENSITIVE`(민감정보) · `OTHER`(기타).

### 담당자 메모 (F7)

| # | 메서드·경로 | 권한 | 요청 | 응답 |
|---|---|---|---|---|
| 23 | `POST /api/children/{child_id}/notes` | D·S | `{body?, share_text?}` | 201 `NoteSummary` |
| 24 | `GET /api/children/{child_id}/notes` | D·S | – | 200 `NoteSummary[]` |
| 25 | `GET /api/notes/{note_id}` | D·S | – | 200 `NoteDetail` (원문 열람, 감사 로그 기록) |

- `body`(원문, 건강·가정 내용, 0~2000자)는 서버에서 AES-256-GCM으로 암호화해 저장. 아동의 민감정보 확인 전이면 422 `SENSITIVE_BASIS_REQUIRED`.
- `share_text`(멘토에게 보일 공유 문구, 0~200자). 둘 중 하나 이상 필요.

### 감사 로그 (F10)

| # | 메서드·경로 | 권한 | 요청 | 응답 |
|---|---|---|---|---|
| 26 | `GET /api/audit-logs?action=&result=&date_from=&date_to=&limit=50&offset=0` | D·S | – | 200 `{items: AuditLog[], total}` |
| 27 | `GET /api/health` | 공개 | – | 200 `{status: "ok"}` |

## 역할별 권한 매트릭스

같은 센터 기준. ✅ 허용 · ⛔ 403 · 🔒 로그인 필요(401) · 조건은 칸 안에. "멘토(기간 안)"은 해당 아동에 대해 같은 센터 ∧ 본인 배정 ∧ 시작일 ≤ 오늘(한국 날짜) ≤ 종료일 ∧ 미회수인 멘토. 다른 센터의 대상은 역할과 관계없이 ⛔(존재 여부도 알려 주지 않음).

| # | API | 비로그인 | 시설장 | 담당자 | 멘토(기간 안) | 멘토(기간 밖·미배정·회수) |
|---|---|---|---|---|---|---|
| 1~3 | 초대 확인·가입·로그인 | ✅ (IP당 분당 5~10회) | ✅ | ✅ | ✅ | ✅ |
| 4 | 로그아웃 | ✅ (쿠키 삭제만) | ✅ | ✅ | ✅ | ✅ |
| 5 | 내 정보 | 🔒 | ✅ | ✅ | ✅ | ✅ |
| 6 | 초대 코드 발급 | 🔒 | ✅ 담당자·멘토 | ✅ 멘토만 (담당자 초대 ⛔) | ⛔ | ⛔ |
| 7 | 계정 목록 | 🔒 | ✅ | ✅ | ⛔ | ⛔ |
| 8 | 계정 비활성화 | 🔒 | ✅ 담당자·멘토 (본인 ⛔) | ✅ 멘토만 | ⛔ | ⛔ |
| 9~11 | 아동 등록·목록·민감정보 확인 | 🔒 | ✅ | ✅ | ⛔ | ⛔ |
| 12 | 아동 파기 | 🔒 | ✅ | ⛔ | ⛔ | ⛔ |
| 13~15 | 배정 생성·목록·회수 | 🔒 | ✅ | ✅ | ⛔ | ⛔ |
| 16 | 내 배정 목록 | 🔒 | ⛔ | ⛔ | ✅ (진행 중 + 시작 전) | ✅ (끝난 배정은 안 보임) |
| 17 | 인계 카드 | 🔒 | ⛔ | ⛔ | ✅ | ⛔ |
| 18 | 기록 보기 | 🔒 | ✅ 전체(숨김 포함) | ✅ 전체(숨김 포함) | ✅ 기간 중 자기 기록만 | ⛔ |
| 19 | 회차 기록 작성 | 🔒 | ⛔ | ⛔ | ✅ 날짜는 기간 안·오늘 이전 | ⛔ |
| 20 | 정정 | 🔒 | ⛔ | ⛔ | ✅ 기간 중 자기 기록만 | ⛔ |
| 21~22 | 숨김·칸 지우기 | 🔒 | ✅ | ✅ | ⛔ | ⛔ |
| 23~25 | 메모 작성·목록·원문 | 🔒 | ✅ | ✅ (원문 작성은 민감정보 확인된 아동만) | ⛔ | ⛔ |
| 26 | 감사 로그 | 🔒 | ✅ 자기 센터만 | ✅ 자기 센터만 | ⛔ | ⛔ |
| 27 | health | ✅ | ✅ | ✅ | ✅ | ✅ |

모든 ⛔는 감사 로그에 `access.denied`(시도한 경로, 사유 코드: role / not_assigned / before_start / after_end / revoked / other_center_or_missing 등)로 남는다. 위 표는 `backend/tests/test_authz_boundaries.py`(기획서 경계 14개)와 `test_management.py`·`test_records.py`로 검증한다.

## 기획서(❷ 5절) 대비 차이

| 항목 | 기획서 | 구현 | 이유 |
|---|---|---|---|
| API 수 | 약 20개 | 27개 | 내 정보(#5)·내 배정(#16)·민감정보 나중 확인(#11)·메모 목록(#24)·health(#27) 등 화면에 필요한 조회를 분리. 기능 범위(F1~F10)는 같음 |
| 인증 4개 | 코드 검증·가입·로그인·로그아웃 | + 내 정보(#5) | 새로고침 후 로그인 상태·역할 확인용 |
| 메모 2개 | 작성·원문 조회 | + 목록(#24) | 원문 없이 공유 문구·작성자만 보여 주는 목록이 따로 필요 |
| 세션 쿠키 | HttpOnly·Secure·SameSite=Strict | + `__Host-` 접두사, Max-Age=유휴 만료(10분, 설정 상한 60분)·인증된 응답마다 갱신 | 하위 도메인 쿠키 주입 방지, 브라우저 쪽 쿠키 수명을 서버 세션과 맞춰 디스크에 오래 남는 쿠키 방지 |
| 오류 응답 | (명시 없음) | `{"error":{"code","message"}}` 고정 형식 | 예외 내용 노출 방지, 프론트 처리 일관화 |

## 응답 스키마

```ts
type Role = "director" | "staff" | "mentor";

type Me = {
  id: number; login_id: string; display_name: string; role: Role;
  center: { id: number; name: string };
};

type UserSummary = {
  id: number; login_id: string; display_name: string; role: Role;
  disabled_at: string | null;      // 비활성화 시각
  assignment_ended: boolean;       // 배정이 모두 끝난 활성 멘토
};

type Child = {
  id: number; alias: string; grade: string;
  consent_at: string;              // 개인정보 처리 동의 확인 시각
  sensitive_basis_at: string | null; // 민감정보 동의/근거 확인 시각
  created_at: string;
};

type Assignment = {
  id: number; mentor_id: number; mentor_name: string;
  child_id: number; child_alias: string;
  start_date: string; end_date: string;
  revoked_at: string | null;
  status: "upcoming" | "active" | "ended" | "revoked";
};

type MyAssignment = {
  assignment_id: number;
  child: { id: number; alias: string; grade: string };
  start_date: string; end_date: string;
  status: "upcoming" | "active";
};

type CardRecord = {
  session_no: number; session_date: string;
  did: string; stuck: string; next_step: string;
};

type HandoverCard = {
  child: { id: number; alias: string; grade: string };
  assignment: { start_date: string; end_date: string };
  records: CardRecord[];           // 최근 것이 먼저, 최대 4개
  share_texts: string[];
};

type MentorRecord = {
  id: number; session_date: string;
  did: string; stuck: string; next_step: string;
  corrects_id: number | null;      // 정정본이면 원본 id
  created_at: string;
};

type StaffRecord = MentorRecord & {
  session_no: number | null;       // 인계 카드와 같은 누적 회차. 숨김·대체된 행은 null
  author: { id: number; display_name: string };
  hidden_at: string | null; hidden_reason_code: string | null;
  redacted_at: string | null;
  superseded: boolean;             // 정정되어 대체된 원본이면 true
};

type NoteSummary = {
  id: number; share_text: string | null; has_body: boolean;
  author: { id: number; display_name: string }; created_at: string;
};

type NoteDetail = NoteSummary & { body: string | null };

type AuditLog = {
  id: number; actor_id: number | null; action: string;
  target_type: string | null; target_id: number | null;
  result: "success" | "denied" | "failure";
  ip: string | null; detail: Record<string, unknown>; created_at: string;
};
```

## 확정 사항 (2026-10-11, 프론트 골격 작업 중 나온 질문)

1. 정정 화면용 단건 조회 API는 두지 않는다. 기록은 #18 목록에서 넘겨받고, 새로고침 때는 아동 ID로 #18을 다시 읽는다.
2. `fields`는 `"body.password"`처럼 점으로 이은 **문자열 배열**이다.
3. 숨김·칸 지우기(redact)된 칸은 **빈 문자열**로 내려간다(null 아님). 어느 칸을 지웠는지는 응답에 없다(감사 로그 `record.redact`의 detail에 있음).
4. 감사 로그 `date_from`·`date_to`는 `YYYY-MM-DD`, 한국 날짜 기준, **양 끝 포함**.
5. #9 `sensitive_basis_confirmed`는 선택(기본 `false`).
6. 배정 최대 기간: `end_date - start_date ≤ 366일`.
7. 한 아동에 **서로 다른 멘토**의 기간이 겹치는 배정은 허용한다(공동 지도·인계 겹침). **같은 멘토·같은 아동**의 살아 있는 배정끼리 기간이 겹치면 409(DB 배제 제약, 회수가 항상 접근을 닫게 하려는 것).
8. 개발 중 Origin 허용 목록은 `backend/.env`의 `IEOGAGI_ALLOWED_ORIGINS`(기본 `["http://localhost:5173"]`). Safari는 http localhost에서 Secure 쿠키를 저장하지 않을 수 있으니 개발은 Chrome으로.
9. 429에는 대기 시간을 주지 않는다(제한은 분당 10회).

## 감사 로그 action 목록

`auth.login` · `auth.logout` · `auth.signup` · `invite.create` · `user.disable` · `child.create` · `child.sensitive_basis` · `child.destroy` · `assignment.create` · `assignment.revoke` · `record.view` · `record.create` · `record.correct` · `record.hide` · `record.redact` · `record.sensitive_prompt` · `handover.view` · `note.create` · `note.view` · `audit.view` · `access.denied`
