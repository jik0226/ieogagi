# 이어가기 프론트엔드

React(Vite) SPA. 언어는 JavaScript(JSX)이고 TypeScript는 쓰지 않는다. UI 컴포넌트 라이브러리 없이 일반 CSS만 쓴다. API 계약은 `../docs/API_설계.md`, 화면별 정리는 `../docs/화면목록.md`를 본다.

## 실행

Node 26 필요(`package.json`의 `engines`).

```bash
npm ci            # package-lock.json 그대로 설치
npm run dev       # http://localhost:5173
npm run lint      # eslint . --max-warnings 0 (경고도 실패)
npm run build     # dist/ 생성 (소스맵 없음)
npm run preview   # 빌드 결과 확인
```

- 백엔드는 `http://localhost:8000`에서 떠 있어야 한다. 개발 서버가 `/api`를 그쪽으로 프록시하므로 브라우저 입장에서는 같은 출처이고 CORS는 열지 않는다.
- 백엔드 주소가 다르면 `API_PROXY_TARGET=http://127.0.0.1:18000 npm run dev`처럼 환경 변수로 바꾼다.
- 백엔드의 CSRF 허용 목록(Origin)에 `http://localhost:5173`이 들어 있어야 POST·PUT·DELETE가 통과한다. 프록시는 Origin 헤더를 바꾸지 않는다.
- 세션 쿠키가 `Secure`라서 Chrome·Firefox는 `localhost`에서 동작하지만 Safari는 http 개발 서버에서 쿠키를 저장하지 않을 수 있다. 개발은 Chrome 계열로 한다.
- 백엔드 없이 화면만 볼 때는 로그인 화면까지만 열린다(앱 시작 시 `GET /api/auth/me`가 401이면 `/login`).

## 폴더 구조

```
frontend/
  index.html
  vite.config.js         dev 프록시(/api → :8000), build.sourcemap=false
  eslint.config.js       보안 규칙 포함 flat config
  src/
    main.jsx             진입점. 라우터·AuthProvider·CSS 불러오기
    App.jsx              라우트 표(가드 포함)
    api/                 fetch 래퍼(client.js)와 엔드포인트별 함수 27개
    auth/                AuthContext(로그인 상태), useAuth, guards(RequireRole·PublicOnly), roles
    components/          공용 컴포넌트(폼 칸, 대화상자, 탭, 배지, 로딩 막대, 403·404·오류 전용 화면)
    hooks/               useAsync(읽기), useMutation(쓰기), useTabParam(탭을 주소 ?tab=에 기억)
    pages/               화면. LoginPage·SignupPage, mentor/(W2~W4), staff/(W5·W6)
    styles/              tokens.css(디자인 토큰), base·layout·components·badges·forms·data·records·states.css와 화면별로 나눈 mentor-*.css·staff-*.css(파일마다 300줄 이하, main.jsx의 불러오기 순서가 곧 적용 순서)
    utils/               date(한국 시간), labels·auditLabels(표시 문구), messages(오류 문구), josa, validators, ids
```

화면별 경로·상태는 `../docs/화면목록.md`에 있다. 멘토 화면(W1~W4)은 휴대폰 우선(한 줄 카드 배치, 본문 폭 480px 가운데 정렬, 눌러야 하는 것은 44px 이상), 담당자·시설장 화면(W5·W6)은 PC 우선(넓은 표·2단 배치, 768px 미만에서는 표가 가로 스크롤)이다. `AppLayout`의 `variant`("mentor" | "staff")가 두 레이아웃을 가른다.

화면과 파일의 대응은 다음과 같다.

| 화면 | 파일 |
|---|---|
| S1 로그인·가입 | `pages/LoginPage.jsx`, `pages/SignupPage.jsx` |
| S2 멘토 홈 | `pages/mentor/MentorHome.jsx` |
| S3 인계 카드·기록 | `pages/mentor/ChildPage.jsx`, `HandoverCardView.jsx`, `MyRecordsList.jsx` (403이면 `components/ForbiddenView.jsx`) |
| S4 기록 입력·정정 | `pages/mentor/RecordNewPage.jsx`, `RecordCorrectPage.jsx`, `RecordForm.jsx` |
| S5 관리 | `pages/staff/StaffPage.jsx` → `ChildrenTab`(→ `ChildForm`, `ChildrenTable`), `AssignmentsTab`(→ `AssignmentManager`), `AccountsTab`(→ `InviteForm`, `UserTable`) |
| S6 기록·감사 | `pages/staff/StaffRecordsPage.jsx` → `RecordsTab`(→ `StaffRecordList`, `NotesPanel`), `AuditTab` |

## 규칙

### 보안

- `dangerouslySetInnerHTML`·`innerHTML`·`eval`·`new Function`·문자열 `setTimeout`·`javascript:` URL을 쓰지 않는다. 서버가 준 텍스트는 JSX 안에서 그대로 출력해 React가 이스케이프하게 한다. 여러 줄 텍스트는 CSS `white-space: pre-wrap`으로 보여 준다.
- 토큰·개인정보를 `localStorage`·`sessionStorage`에 저장하지 않는다. 세션은 HttpOnly 쿠키라 프론트가 읽지 않는다. 로그인 상태는 `AuthContext`의 메모리 상태뿐이다.
- `console.*`, 디버그 코드, 주석 처리된 코드를 남기지 않는다.
- 외부 링크를 넣게 되면 `rel="noopener noreferrer"`를 붙인다(`react/jsx-no-target-blank`가 검사).
- 입력 칸의 `maxLength`는 계약과 같게 둔다: 별칭 20, 이름 30, 아이디 32, 비밀번호 128, 기록 칸 500, 메모 원문 2000, 공유 문구 200. 클라이언트 검사는 가벼운 안내용이고 서버가 최종 검증한다.
- 경로 매개변수는 `segment()`(= `encodeURIComponent`)로 감싸고, 화면 경로의 id는 `isNumericId()`로 확인한다.
- ESLint가 위 규칙을 자동으로 검사한다: `react/no-danger`, `react/jsx-no-target-blank`, `react/jsx-no-script-url`, `no-eval`, `no-implied-eval`, `no-new-func`, `no-script-url`, `no-console`, `eslint-plugin-security` 권장 규칙, `react-hooks` 권장 규칙. `npm run lint`는 경고 0개여야 통과한다.
- `security/detect-object-injection`을 피하려고 `obj[변수]` 대신 `Map`, 배열 `find`, 값 묶음 함수(`recordFieldEntries`)를 쓴다.
- 파일 하나는 300줄을 넘기지 않는다(목표 200줄 미만).

### API 함수 추가

1. `docs/API_설계.md`에 엔드포인트가 있는지 확인한다(없으면 문서부터 고친다).
2. `src/api/`의 알맞은 파일에 함수 하나를 추가한다. 주석에 계약의 `#` 번호를 적는다.

   ```js
   import { get, post, segment } from './client.js';

   // #11
   export const confirmSensitiveBasis = (childId) =>
     post(`/children/${segment(childId)}/sensitive-basis`);
   ```

3. 읽기는 화면에서 `useAsync(load)`, 쓰기는 `useMutation(action)`으로 부른다. `load`는 `useCallback`으로 감싼 함수여야 한다.
4. 로그인·초대 코드 확인처럼 401이 "세션 만료"가 아닌 호출은 `{ skipUnauthorizedHandler: true }`를 넘긴다(`api/auth.js` 참고).

### 오류 처리

- `api/client.js`가 모든 오류 응답 `{error:{code,message,fields?,categories?}}`을 `ApiError`(status, code, message, fields, categories)로 바꿔 던진다. 네트워크 실패는 `status: 0`, `code: "NETWORK_ERROR"`다. 본문이 JSON이 아니면 일반 문구를 쓰고, 응답 원문이나 스택은 화면에 내지 않는다.
- 401(로그인 요청과 앱 시작 때의 `GET /api/auth/me` 제외)이면 `setUnauthorizedHandler`로 등록된 콜백이 불리고, 로그인해 있던 중이면 `AuthProvider`가 `expired` 표시와 함께 로그인 상태를 비워 가드가 `/login`으로 보낸다. 로그인 화면은 "세션이 만료되었습니다. 다시 로그인해 주세요." 안내를 띄운다. 처음부터 로그인 안 한 경우에는 안내가 없다.
- 화면에 보이는 문구는 `describeError()`(`utils/messages.js`)를 거친다. 403은 고정 문구 "열람 기간이 아니거나 권한이 없습니다.", 그 외는 서버의 `message`다. `ApiError`가 아닌 예외는 일반 문구로 바꾼다.
- 멘토 화면의 403(조회·저장 모두)은 `ForbiddenView`(CSS로 그린 진입 금지 표시가 있는 전용 차단 화면, 이유는 쓰지 않음)로 바꿔 보여 준다. 멘토 화면의 그 밖의 불러오기 실패는 `GenericErrorView`("문제가 생겼습니다 / 다시 시도"), 없는 주소는 `NotFoundView`다. `AsyncView`의 `screen` 옵션이 이 전체 화면 처리를 켠다. 렌더링 중 예외는 `ErrorBoundary`가 같은 오류 화면으로 막는다.
- 422 `VALIDATION_FAILED`는 `invalidFieldNames()`로 문제 칸을 찾아 표시한다. `SENSITIVE_CONFIRM_REQUIRED`(S4)와 `SENSITIVE_BASIS_REQUIRED`(S6 메모)는 일반 오류 박스 대신 전용 안내로 처리한다(`useMutation`의 `skipError`).
- 목록·상세 화면은 `AsyncView`가 로딩(회색 막대 `Loading`)·오류를, 각 화면이 빈 목록을 그린다.

### 날짜

- 계약의 날짜는 한국 날짜(`YYYY-MM-DD`)이고 시각은 UTC ISO 8601이다. 오늘 날짜는 `todayKst()`(`Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Seoul' })`), 시각 표시는 `formatDateTime()`이 한국 시간으로 바꾼다. 브라우저의 시간대에 의존하지 않는다.

## 접근성·인라인 스타일 규칙

- 인라인 `style=` 속성을 쓰지 않는다(배포 CSP `style-src 'self'`). 모양은 CSS 클래스로만 정한다.
- 색 값은 `tokens.css`에만 둔다. 본문 글씨 4.5:1 이상, 입력칸·버튼 테두리(`--color-border-strong`)와 포커스 링(`--color-focus`, 3px 실선)은 흰 바탕 대비 3:1 이상이다. "시작 전" 카드는 투명도 대신 별도 색을 써서 글씨 대비를 지킨다.
- 상태는 색만으로 구분하지 않는다. 배지에는 항상 글자가 있고, 감사 로그의 거부 행은 연한 빨강 배경과 "거부" 배지를 함께 쓴다.
- 눌러야 하는 것의 높이는 `--tap-min`(44px). 밀도가 높은 PC 표 안의 작은 버튼만 `--tap-compact`(36px)이고, 768px 미만에서는 44px로 커진다.
- 비활성 버튼에는 이유 문구를 옆에 둔다(아동 등록의 개인정보 동의, 파기의 별칭 입력).

## 일부러 남겨 둔 것 (디자인 담당의 디자인 작업)

- 시각 디자인의 최종 다듬기: 색·글꼴·간격·모서리는 `src/styles/tokens.css`의 변수로 모아 두었다. 클래스 이름(`card`, `btn`, `badge`, `field`, `table`, `dialog`, `tabs`, `record`)을 유지하면 마크업을 건드리지 않고 다시 꾸밀 수 있다.
- 브랜드·로고·아이콘·일러스트, 웹폰트(지금은 시스템 글꼴 목록만 지정, 외부 글꼴을 불러오지 않음).
- 다크 모드.
- 인계 카드의 수첩 같은 표현(W3), 감사 로그 표 밀도(W6).
- PropTypes·타입 선언: 프로젝트가 JavaScript라 `react/prop-types` 규칙은 꺼 두었다.
- 아직 없는 것: 자동 테스트(Vitest 등), 스크린리더 실기 점검, CSP 헤더(배포 시 Caddy에서 설정).
