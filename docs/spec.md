# healthAGI 기능 명세서

> UI 리디자인 참고용 — 현재 구현된 기능과 데이터 흐름을 화면 단위로 정리.

---

## 목차

1. [전체 구조](#1-전체-구조)
2. [화면별 기능 명세](#2-화면별-기능-명세)
   - [2.1 로그인 / 회원가입](#21-로그인--회원가입)
   - [2.2 Today 탭](#22-today-탭)
   - [2.3 Timers 탭 — 근육 회복 타이머](#23-timers-탭--근육-회복-타이머)
   - [2.4 Log 탭 — 운동 / 식단 로깅](#24-log-탭--운동--식단-로깅)
   - [2.5 AI 탭 — 텍스트 채팅 코치](#25-ai-탭--텍스트-채팅-코치)
   - [2.6 Profile 탭](#26-profile-탭)
3. [공통 데이터 모델](#3-공통-데이터-모델)
4. [API 엔드포인트 목록](#4-api-엔드포인트-목록)
5. [오프라인 / 동기화 동작](#5-오프라인--동기화-동작)
6. [AI 통합 상세](#6-ai-통합-상세)
7. [알림 동작](#7-알림-동작)
8. [비즈니스 규칙 요약](#8-비즈니스-규칙-요약)

---

## 1. 전체 구조

### 탭 구성 (5개)
| 탭 | 라우트 | 역할 |
|---|---|---|
| Today | `/(tabs)/today` | 오늘의 요약 (타이머 상태 + 운동/식단 통계 + AI 추천) |
| Timers | `/(tabs)/timers` | 근육 부위별 회복 타이머 |
| Log | `/(tabs)/log` | 운동 세션 기록 + 식단 기록 |
| AI | `/(tabs)/ai` | AI 코치 텍스트 채팅 |
| Profile | `/(tabs)/profile` | 사용자 정보 + 체중 기록 |

### 인증 흐름
- 앱 시작 시 `AsyncStorage / SecureStore`에서 액세스 토큰 확인
- 토큰 없으면 로그인/회원가입 화면으로 리다이렉트
- 토큰 만료 시 리프레시 토큰으로 자동 갱신 (HTTP 401 인터셉트)
- 로그아웃 시 로컬 토큰 삭제 + 서버 블랙리스트 등록

---

## 2. 화면별 기능 명세

### 2.1 로그인 / 회원가입

**표시 요소**
- 이메일 입력 필드
- 비밀번호 입력 필드 (최소 8자, 대소문자+숫자+특수문자 포함)
- 로그인 버튼 / 회원가입 탭 전환 버튼
- 에러 메시지 표시 영역

**동작**
- 로그인: `POST /v1/auth/login` → 액세스 토큰 + 리프레시 토큰 저장
- 회원가입: `POST /v1/auth/register` → 즉시 로그인 처리
- 성공 시 Today 탭으로 이동

**API**
- `POST /v1/auth/register` — `{ email, password }` → `{ user, tokens }`
- `POST /v1/auth/login` — `{ email, password }` → `{ user, tokens }`
- `POST /v1/auth/refresh` — `{ refresh_token }` → `{ access_token }`
- `POST /v1/auth/logout` — 리프레시 토큰 블랙리스트 등록

---

### 2.2 Today 탭

**표시 요소**
- 오늘 날짜 헤더
- 현재 진행 중인 회복 타이머 요약 (부위명 + 남은 시간)
- 오늘의 운동 세션 수
- 오늘의 칼로리/단백질 섭취 합계
- AI 추천 카드 (서버에서 미리 계산된 일일 추천)
- 당겨서 새로고침

**동작**
- `GET /v1/timers/current` — 현재 활성 타이머 목록
- `GET /v1/recommendations/daily` — 오늘의 AI 추천 (운동 부위, 영양 조언)
- `GET /v1/workouts/sessions` (오늘 날짜 필터) — 오늘 운동 수
- `GET /v1/meals` (오늘 날짜 필터) — 오늘 칼로리 합산

**상태**
- 오프라인 시 캐시된 타이머 데이터 표시 + 배너 표시

---

### 2.3 Timers 탭 — 근육 회복 타이머

**표시 요소**
- 근육 부위 리스트 (12개 부위)
- 각 행: 부위명 + 기본 회복 시간 + 현재 상태
  - **운동 가능**: 타이머 없음 또는 만료됨 → 초록색 텍스트
  - **회복 중**: 남은 시간 카운트다운 `HH:MM:SS` 형식 → 노란색
  - **준비 완료 ✓**: 타이머 만료 → 초록색
- 운동 완료 버튼 (파란색) / 취소 버튼 (회색)
- 오프라인 배너 (오프라인 시 상단 표시)
- 당겨서 새로고침

**근육 부위 목록 (12개)**
| ID | 한국어명 | 기본 회복 시간 |
|---|---|---|
| chest | 가슴 | 48h |
| back | 등 | 48h |
| shoulders | 어깨 | 48h |
| biceps | 이두 | 24h |
| triceps | 삼두 | 24h |
| quads | 대퇴사두 | 72h |
| hamstrings | 햄스트링 | 72h |
| glutes | 둔근 | 72h |
| calves | 종아리 | 24h |
| core | 코어 | 24h |
| forearms | 전완 | 24h |
| neck | 목 | 24h |

**타이머 시작 플로우**
1. "운동 완료" 버튼 탭 → 시간 선택 모달 팝업
2. 모달에서 선택 옵션:
   - 프리셋 버튼: 24h / 기본값(부위별) / 48h / 72h
   - 직접 입력: 시간 단위 숫자 입력 (예: 36)
3. 선택/확인 → 타이머 시작

**타이머 취소 플로우**
1. "취소" 버튼 탭 → 즉시 소프트 삭제
2. 로컬 알림 취소
3. 서버에 DELETE 요청 (오프라인이면 outbox에 큐잉)

**시간 카운트다운 동작**
- 1초 인터벌로 tick 상태 업데이트 (`setInterval 1000ms`)
- `timerProgress(timer)` = `start_time + duration_minutes * 60 * 1000 - Date.now()`
- 만료 시 "준비 완료 ✓"로 전환 (서버 요청 없음)

**API**
- `GET /v1/muscle-groups` — 부위 목록 (서버 동기화, 로컬 캐시)
- `GET /v1/timers/current` — 활성 타이머 목록
- `POST /v1/timers` — 타이머 생성 `{ muscle_group_id, start_time, duration_minutes, source: "manual", client_op_id }`
- `DELETE /v1/timers/{id}` — 타이머 삭제 (소프트 삭제)

**오프라인 동작**
- 타이머 시작/취소는 로컬 SQLite에 즉시 반영
- 작업은 `outbox` 테이블에 큐잉 → 온라인 복구 시 플러시

---

### 2.4 Log 탭 — 운동 / 식단 로깅

두 개의 패널로 구성: **운동** / **식단** (탭 또는 스크롤로 전환).

#### 운동 패널

**표시 요소**
- 오늘의 운동 세션 카드 목록
  - 세션 시작 시각
  - 세트 목록: 운동명 + `세트수 × 무게kg × reps` + RPE
- 새 세션 추가 버튼
- AI 파싱 버튼 (✨): 텍스트 입력 → 구조화 파싱
- 음성 입력 버튼 (🎤): 마이크 녹음 → 파싱

**운동 입력 방법 3가지**
1. **수동 입력**: 운동명 검색 → 세트/무게/reps/RPE 입력
2. **AI 텍스트 파싱**: 자유 텍스트 (예: "벤치프레스 100kg 5세트 5개") → `POST /v1/workouts/parse` → 세트 목록 자동 생성
3. **음성 파싱**: 녹음 시작(🎤 빨간색) → 중지(■) → `POST /v1/workouts/parse-audio` → 세트 목록 자동 생성

**AI 파싱 결과 적용**
- 파싱된 세트 목록 미리보기
- 운동 세션 없으면 새 세션 자동 생성
- 세트를 현재 세션에 추가

**데이터 필드 (운동 세트)**
| 필드 | 타입 | 설명 |
|---|---|---|
| exercise_id | string | 운동 종목 ID |
| set_index | number | 세트 번호 |
| reps | number | 반복 횟수 |
| weight_kg | decimal | 무게 (kg) |
| rpe | number 1-10 | 자각적 운동 강도 |
| is_warmup | boolean | 워밍업 세트 여부 |

#### 식단 패널

**표시 요소**
- 오늘 식사 목록 (아침/점심/저녁/간식)
  - 식사명 + 총 칼로리 + 단백질/탄수화물/지방 (g)
- 일일 합계: 칼로리 / 단백질 / 탄수화물 / 지방
- 새 식사 추가 버튼
- AI 파싱 버튼 (✨): 텍스트 → 매크로 자동 계산
- 음성 입력 버튼 (🎤): 음성 → 파싱

**식단 입력 방법 3가지**
1. **수동 입력**: 음식명 + 중량(g) + 칼로리/매크로 직접 입력
2. **AI 텍스트 파싱**: 자유 텍스트 (예: "닭가슴살 200g 현미밥 한공기") → `POST /v1/meals/parse` → 음식 항목 + 영양소 자동 계산
3. **음성 파싱**: 녹음 → `POST /v1/meals/parse-audio` → 파싱

**데이터 필드 (식사)**
| 필드 | 타입 | 설명 |
|---|---|---|
| meal_type | enum | breakfast/lunch/dinner/snack |
| eaten_at | datetime | 식사 시각 |
| total_kcal | decimal | 총 칼로리 |
| protein_g | decimal | 단백질 (g) |
| carbs_g | decimal | 탄수화물 (g) |
| fat_g | decimal | 지방 (g) |
| raw_input | text | 원본 입력 텍스트 |

**데이터 필드 (식품 항목)**
| 필드 | 타입 | 설명 |
|---|---|---|
| name | string | 음식명 |
| serving_g | decimal | 1회 제공량 (g) |
| kcal | decimal | 칼로리 |
| protein_g | decimal | 단백질 |
| ai_confidence | decimal 0-1 | AI 추정 신뢰도 |
| user_confirmed | boolean | 사용자 확인 여부 |

**API**
- `GET /v1/workouts/sessions` — 세션 목록 (날짜 필터)
- `POST /v1/workouts/sessions` — 세션 생성
- `POST /v1/workouts/sessions/{id}/sets` — 세트 추가
- `GET /v1/exercises?q=` — 운동 종목 검색 (자동완성)
- `POST /v1/workouts/parse` — 텍스트 → 세트 목록 파싱
- `POST /v1/workouts/parse-audio` — 오디오 → 세트 목록 파싱 (multipart)
- `GET /v1/meals` — 식사 목록 (날짜 필터)
- `POST /v1/meals` — 식사 등록
- `POST /v1/meals/parse` — 텍스트 → 식사 파싱
- `POST /v1/meals/parse-audio` — 오디오 → 식사 파싱 (multipart)

---

### 2.5 AI 탭 — 텍스트 채팅 코치

**표시 요소**
- 대화 목록 (최근 대화 이어가기 또는 새 대화)
- 채팅 버블 (사용자: 오른쪽, AI: 왼쪽)
- 텍스트 입력 + 전송 버튼
- AI 응답 스트리밍 (SSE 실시간 표시)
- 마크다운 렌더링 (볼드, 리스트, 테이블 등)
- 도구 호출 확인 다이얼로그 (쓰기 작업 시)

**AI 컨텍스트 구성 (매 턴 동적 조립)**
1. **페르소나**: 한국어 헬스 코치, 이름 "헬스AI"
2. **사용자 프로필**: 키, 체중, 나이, 목표, 로케일
3. **현재 회복 상태**: 각 근육 부위별 회복 완료 여부 + 남은 시간
4. **최근 7일 운동 요약**: 운동 부위, 총 볼륨, 세션 수
5. **최근 3일 식단 요약**: 일일 칼로리, 단백질 평균
6. **도구 정의**: 읽기 도구 + 쓰기 도구 목록

**AI 도구 (Tool Calling)**

읽기 도구 (즉시 실행):
- `query_history(kind, from, to)` — 운동/식단 이력 조회
- `get_recommendation(kind)` — 오늘의 추천 조회

쓰기 도구 (사용자 확인 후 실행):
- `start_recovery_timer(muscle_group_id, duration_hours)` — 타이머 시작
- `log_workout(sets)` — 운동 세트 기록
- `log_meal(items)` — 식사 기록

**확인 다이얼로그 동작**
- AI가 쓰기 도구를 호출하면 채팅 화면에 확인 카드 표시
- "적용" → 실제 API 호출 → 결과를 AI 컨텍스트에 반영
- "취소" → 도구 실패로 처리, 대화 계속

**API**
- `GET /v1/chat/conversations` — 대화 목록
- `POST /v1/chat/conversations` — 새 대화 생성
- `GET /v1/chat/conversations/{id}/messages` — 메시지 이력
- `POST /v1/chat/conversations/{id}/messages` — 메시지 전송 (SSE 스트리밍)

**SSE 이벤트 형식**
```
data: {"type": "token", "content": "안녕하세요"}
data: {"type": "tool_call", "name": "start_recovery_timer", "args": {...}}
data: {"type": "done"}
```

---

### 2.6 Profile 탭

**표시 요소**
- 로그인된 이메일 (상단)
- 표시 이름 입력
- 키 (cm) 입력
- 체중 섹션:
  - 현재 체중 표시 (`현재 72.5kg · 2026-05-20`)
  - 새 체중 입력 + "기록" 버튼
- 목표 입력 (멀티라인 텍스트)
- 저장 버튼
- 메타 정보: 로케일, 타임존
- 로그아웃 버튼 (빨간색)

**체중 기록 동작**
- 체중 입력 후 "기록" → `POST /v1/profile/body-metrics`
- 최신 기록이 레이블 옆에 즉시 표시
- 체중 기록은 시계열로 누적 (덮어쓰지 않음)

**프로필 저장 동작**
- "저장" → `PATCH /v1/profile` → 성공 시 "저장됨" Alert

**API**
- `GET /v1/profile` — 프로필 조회
- `PATCH /v1/profile` — 프로필 수정 (`display_name`, `height_cm`, `goals`)
- `GET /v1/profile/body-metrics` — 체중 기록 이력
- `POST /v1/profile/body-metrics` — 체중 기록 추가 `{ measured_at, weight_kg }`

---

## 3. 공통 데이터 모델

### User
```
id          uuid
email       string (unique)
created_at  datetime
```

### Profile
```
user_id           uuid (FK)
display_name      string?
birth_date        date?
sex               enum(male/female/other)?
height_cm         decimal?
timezone          string (기본: Asia/Seoul)
locale            string (기본: ko)
goals             text?
```

### BodyMetric (체중 기록)
```
id            uuid
user_id       uuid (FK)
measured_at   datetime
weight_kg     decimal
body_fat_pct  decimal?
resting_hr    decimal?
sleep_hours   decimal?
```

### MuscleGroup (근육 부위)
```
id                      string (예: "chest")
display_name_ko         string (예: "가슴")
display_name_en         string (예: "Chest")
default_recovery_hours  number
sort_order              number
```

### RecoveryTimer (회복 타이머)
```
id                uuid
user_id           uuid (FK)
muscle_group_id   string (FK)
start_time        datetime (UTC ISO)
duration_minutes  number
intensity_score   decimal? (1-10)
source            string ("manual" | "ai")
notes             text?
deleted_at        datetime? (soft delete)
```

### WorkoutSession (운동 세션)
```
id          uuid
user_id     uuid (FK)
started_at  datetime
ended_at    datetime?
raw_input   text?
```

### WorkoutSet (운동 세트)
```
id          uuid
session_id  uuid (FK)
exercise_id uuid (FK)
set_index   number
reps        number?
weight_kg   decimal?
rpe         number? (1-10)
is_warmup   boolean
```

### Exercise (운동 종목)
```
id                       uuid
canonical_name           string
display_name_ko          string
display_name_en          string
primary_muscle_group_id  string (FK)
secondary_muscle_group_ids  string[]
equipment                string?
is_compound              boolean
```

### Meal (식사)
```
id          uuid
user_id     uuid (FK)
eaten_at    datetime
meal_type   enum(breakfast/lunch/dinner/snack)
raw_input   text?
total_kcal  decimal?
protein_g   decimal?
carbs_g     decimal?
fat_g       decimal?
source      enum(manual/ai_text/ai_voice)
```

### MealItem (식품 항목)
```
id              uuid
meal_id         uuid (FK)
name            string
serving_g       decimal?
kcal            decimal?
protein_g       decimal?
carbs_g         decimal?
fat_g           decimal?
ai_confidence   decimal? (0-1)
user_confirmed  boolean
```

### ChatConversation
```
id      uuid
user_id uuid (FK)
mode    enum(text|voice)
title   string?
```

### ChatMessage
```
id           uuid
conv_id      uuid (FK)
role         enum(user/assistant/tool)
content      text
tool_name    string?
tool_args    jsonb?
tokens_in    number?
tokens_out   number?
model        string?
```

---

## 4. API 엔드포인트 목록

베이스 URL: `https://api.<domain>/v1`  
인증: `Authorization: Bearer <access_token>`

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/auth/register` | 회원가입 |
| POST | `/auth/login` | 로그인 |
| POST | `/auth/refresh` | 토큰 갱신 |
| POST | `/auth/logout` | 로그아웃 |
| GET | `/auth/me` | 현재 사용자 정보 |
| GET | `/profile` | 프로필 조회 |
| PATCH | `/profile` | 프로필 수정 |
| GET | `/profile/body-metrics` | 체중 이력 |
| POST | `/profile/body-metrics` | 체중 기록 추가 |
| GET | `/muscle-groups` | 근육 부위 목록 |
| GET | `/timers/current` | 현재 활성 타이머 |
| GET | `/timers` | 타이머 이력 (since 파라미터) |
| POST | `/timers` | 타이머 생성 |
| DELETE | `/timers/{id}` | 타이머 취소 |
| GET | `/workouts/sessions` | 운동 세션 목록 |
| POST | `/workouts/sessions` | 세션 생성 |
| PATCH | `/workouts/sessions/{id}` | 세션 종료 시각 등 수정 |
| POST | `/workouts/sessions/{id}/sets` | 세트 추가 |
| GET | `/exercises` | 종목 검색 (`?q=`) |
| POST | `/workouts/parse` | 텍스트 → 운동 파싱 |
| POST | `/workouts/parse-audio` | 오디오 → 운동 파싱 |
| GET | `/meals` | 식사 목록 |
| POST | `/meals` | 식사 등록 |
| PATCH | `/meals/{id}` | 식사 수정 |
| POST | `/meals/parse` | 텍스트 → 식단 파싱 |
| POST | `/meals/parse-audio` | 오디오 → 식단 파싱 |
| GET | `/chat/conversations` | 대화 목록 |
| POST | `/chat/conversations` | 새 대화 생성 |
| GET | `/chat/conversations/{id}/messages` | 메시지 이력 |
| POST | `/chat/conversations/{id}/messages` | 메시지 전송 (SSE) |
| GET | `/recommendations/daily` | 오늘의 AI 추천 |
| GET | `/healthz` | 헬스 체크 |

---

## 5. 오프라인 / 동기화 동작

### 로컬 SQLite 테이블 (모바일)
- `recovery_timers` — 타이머 (서버 필드 + `notification_id`, `server_synced_at`, `pending_op`)
- `muscle_groups_cache` — 부위 정보 캐시
- `outbox` — 미전송 작업 큐 (`kind`, `payload`, `client_op_id`, `fail_count`, `last_error`)

### 동기화 흐름 (`sync()`)
1. `GET /muscle-groups` → 로컬 캐시 갱신
2. Outbox 플러시:
   - `timer.create`: 서버에 POST → 성공 시 서버 ID로 로컬 레코드 교체 → dequeue
   - `timer.delete`: 서버에 DELETE → 404면 로컬 hard delete → dequeue
   - 실패 시 `fail_count++`, `last_error` 기록, `online = false`, 반복 중단
3. `GET /timers/current` → 로컬 upsert → 화면 반영

### 충돌 해결
- **Last-Write-Wins**: `updated_at` 기준, 단일 사용자이므로 서버 값 우선
- **멱등성**: `client_op_id`로 중복 생성 방지 (서버에서 `outbox_processed` 테이블로 체크)
- **소프트 삭제**: `deleted_at != null`이면 화면에서 제외 (실제 DB 삭제 없음)

### 오프라인 UX
- `online` 상태가 false면 상단에 주황색 배너 표시: `"오프라인 — 캐시된 데이터로 표시 중"`
- 타이머 시작/취소는 오프라인에서도 즉시 가능 (outbox 큐잉)
- 채팅/파싱은 오프라인 시 에러 Alert 표시

---

## 6. AI 통합 상세

### LLM 백엔드
- **기본**: Google Gemini API (`gemini-2.5-flash`)
- **선택**: Ollama 로컬 모델 (`LLM_PROVIDER=ollama`)
- **테스트**: Mock 클라이언트 (응답 큐 방식)

### AI 기능 목록
| 기능 | 입력 | 출력 | 엔드포인트 |
|---|---|---|---|
| 채팅 코치 | 사용자 메시지 + 컨텍스트 | 스트리밍 텍스트 + 도구 호출 | `POST /chat/.../messages` |
| 운동 텍스트 파싱 | 자유 텍스트 | 세트 목록 JSON | `POST /workouts/parse` |
| 운동 음성 파싱 | 오디오 파일 | 세트 목록 JSON | `POST /workouts/parse-audio` |
| 식단 텍스트 파싱 | 자유 텍스트 | 식품 항목 + 매크로 JSON | `POST /meals/parse` |
| 식단 음성 파싱 | 오디오 파일 | 식품 항목 + 매크로 JSON | `POST /meals/parse-audio` |
| 일일 추천 | 회복 상태 + 이력 | 추천 운동 부위 + 영양 조언 | `GET /recommendations/daily` |

### 시스템 프롬프트 조립 순서
```
[페르소나 정의]
이름: 헬스AI. 한국어로 응답. 간결하고 실용적인 헬스 코치.

[사용자 프로필]
키: {height_cm}cm, 목표: {goals}

[현재 회복 상태]
- 가슴: 회복 완료
- 등: 23:14:05 남음
- 어깨: 회복 완료
...

[최근 7일 운동 요약]
...

[최근 3일 식단 요약]
...

[사용 가능한 도구]
...
```

### 음성 파싱 처리 흐름 (모바일)
1. 🎤 버튼 탭 → `expo-av` 녹음 시작 (m4a/AAC)
2. ■ 버튼 탭 → 녹음 중지 → URI 획득
3. multipart/form-data로 `parse-audio` 엔드포인트 업로드 (최대 20MB)
4. 서버: Gemini `complete_audio_json()` 호출 → 구조화 JSON 반환
5. 클라이언트: 파싱 결과를 세트/식품 목록에 자동 적용

---

## 7. 알림 동작

### 회복 완료 알림 (로컬 알림)
- 타이머 시작 시 `expo-notifications`로 OS 레벨 예약
- 예약 시각: `start_time + duration_minutes`
- 메시지: `"{부위명} 회복 완료!"`
- 타이머 취소 시 예약된 알림도 함께 취소
- **서버 다운 시에도 알림 동작** (OS가 직접 발화)

### Expo Go 예외
- Expo Go에서는 `expo-notifications` 모듈을 로드하지 않음 (호환성 이슈)
- 알림 기능은 standalone 빌드에서만 동작

---

## 8. 비즈니스 규칙 요약

### 타이머
- 같은 부위에 활성 타이머가 있으면 새 타이머 시작 불가 (서버 단에서 기존 것 삭제 후 생성)
- 만료된 타이머는 자동으로 "운동 가능" 상태 표시 (별도 API 호출 없음, 클라이언트 계산)
- 최소 타이머 시간: 1분 (`Math.max(1, Math.round(hours * 60))`)

### 운동 종목
- 이름 중복 방지: `pg_trgm`으로 유사 종목 검색, 신뢰도 임계치 이상이면 기존 종목 재사용
- AI 파싱 시 인식 못하면 새 종목 자동 생성 (`is_compound`, `primary_muscle_group_id` 추정)

### 식단 파싱
- AI 추정 신뢰도(`ai_confidence`) 0.7 미만이면 UI에서 노란색 경고 표시
- 사용자가 항목 수정하면 `user_confirmed = true`

### AI 채팅
- 쓰기 도구 호출은 반드시 사용자 확인 후에만 실행
- 읽기 도구는 자동 실행 후 결과를 컨텍스트에 추가
- 대화 히스토리는 최근 20개 메시지만 컨텍스트에 포함 (토큰 절약)

### 인증 / 보안
- 액세스 토큰: 15분 만료
- 리프레시 토큰: 30일 만료, DB 블랙리스트 방식
- 비밀번호: 최소 8자, 대문자+소문자+숫자+특수문자 조합
- 모든 API는 Bearer 토큰 필수 (`/auth/*`, `/healthz` 제외)
