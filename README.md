# healthAGI

개인용 헬스 건강 관리 모바일 앱.

- **Mobile**: Expo SDK 55 (React Native, iOS + Android)
- **Backend**: Python 3.12 + FastAPI, PostgreSQL 16
- **AI (default)**: **Google Gemini API** — 기능별 모델 티어링
  - Chat / Parse / Vision → `gemini-2.5-flash`
  - Recovery 회복 추천 / 일일 카드 → `gemini-2.5-pro` (분석 품질 위주)
  - Voice PTT 응답 → `gemini-2.5-flash-lite` (지연 최소화)
- **로컬 (CPU)**: STT(faster-whisper) / TTS(Piper) — GPU 없이 동작 가능, optional
- **외부 접속**: Cloudflare Tunnel + 도메인 (선택)

전체 설계는 `docs/architecture.md`. 구현 단계별 변경 이력은 git log.

## 빠른 시작 (5분)

### 1) 시크릿 생성 + `.env` 작성

```bash
cd /home/user/healthAGI
cp .env.example .env

# 랜덤 값 만들기
openssl rand -hex 32     # JWT_SECRET 용
openssl rand -hex 16     # POSTGRES_PASSWORD 용
```

`.env` 수정 — 최소 다음만 채우면 됨:

```bash
JWT_SECRET=...           # 위 32바이트
POSTGRES_PASSWORD=...    # 위 16바이트
DATABASE_URL=postgresql+asyncpg://healthagi:<위_비번>@localhost:5435/healthagi
ALEMBIC_DATABASE_URL=postgresql+psycopg://healthagi:<위_비번>@localhost:5435/healthagi
GEMINI_API_KEY=AIza...   # https://aistudio.google.com/apikey
```

### 2) Postgres 컨테이너만 띄우기

```bash
make up         # docker compose up -d postgres
docker compose ps
```

기본은 Gemini API + 로컬 파일 스토리지라 **Postgres 하나면 충분**. MinIO/Ollama는 옵션.

### 3) 백엔드 설치 + 마이그레이션

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cd ..

make migrate
make api         # http://localhost:8000/docs
```

테스트:
```bash
make test        # 50 passed
```

### 4) 모바일

```bash
cd mobile
pnpm install
pnpm start
```

`mobile/app.json`의 `extra.apiBaseUrl`을 실기기에서 닿는 주소(LAN IP 또는 도메인)로 변경.

## 기능

- Phase 0: 모노레포 + Docker Compose 부트스트랩
- Phase 1: 인증, 프로필, 오프라인 우선 회복 타이머 + 로컬 알림
- Phase 2: 운동/식단 로깅 + Today 화면 + 체중 기록
- Phase 3: AI 텍스트 채팅 (SSE 스트리밍) + 자유 텍스트 운동/식단 파서
- Phase 4: 푸시투토크 음성 턴 (STT → LLM → TTS)
- Phase 4.5: 스트리밍 음성 WS + 문장 단위 TTS + 인터럽트
- Phase 5: 사진 식단 분석 (Gemini vision)
- Phase 6: 일일 AI 추천 카드 + 운동 종료 시 회복 타이머 제안

## LLM 백엔드 선택

기본은 Gemini API. 환경변수로 전환:

```bash
# Gemini (기본, GEMINI_API_KEY만 있으면 자동 선택)
HEALTHAGI_LLM_BACKEND=gemini
GEMINI_API_KEY=...

# 기능별 모델 (원하는 만큼 오버라이드)
LLM_CHAT_MODEL=gemini-2.5-flash
LLM_VOICE_MODEL=gemini-2.5-flash-lite
LLM_PARSE_MODEL=gemini-2.5-flash
LLM_RECOMMENDATION_MODEL=gemini-2.5-pro
LLM_VISION_MODEL=gemini-2.5-flash

# 로컬 Ollama로 전환하고 싶을 때 (GPU 필요)
HEALTHAGI_LLM_BACKEND=ollama
LLM_CHAT_MODEL=qwen2.5:7b
```

## 옵션 컨테이너

기본(`make up`)은 postgres만 시작. 다음 기능을 켜려면 프로필 지정:

```bash
make up-storage   # MinIO 추가 (사진 식단 클라우드 저장 시)
make up-ollama    # Ollama 추가 (로컬 LLM 쓸 때)
make up-all       # 다 띄우기
```

## 음성 기능 (선택)

서버 사양이 부족해도 CPU만으로 동작 가능한 조합:

```bash
# .env 에 추가
HEALTHAGI_STT_BACKEND=whisper
HEALTHAGI_WHISPER_MODEL=small
HEALTHAGI_WHISPER_COMPUTE=int8
HEALTHAGI_TTS_BACKEND=piper
HEALTHAGI_PIPER_VOICE=/path/to/ko_KR-glow_tts.onnx
```

설치:
```bash
cd backend && .venv/bin/pip install -e ".[voice]"
```

Piper 한국어 보이스: https://github.com/rhasspy/piper/blob/master/VOICES.md 에서 받기.

## 디렉터리

```
healthAGI/
  backend/
    app/
      api/v1/         REST + WS 라우터
      models/         SQLAlchemy 모델
      schemas/        Pydantic 입출력
      services/
        llm/          gemini_client / ollama_client / mock_client + factory
        stt/          faster-whisper / mock
        tts/          xtts / piper / mock
        vad/          silero / mock
        storage/      local / minio / memory
        recommendations.py
    alembic/          DB 마이그레이션
    tests/            pytest (50개)
  mobile/             Expo 앱 (expo-router)
  infra/              cloudflared, nginx, systemd 유닛
  docs/               설계 문서
  docker-compose.yml
  .env.example
  Makefile
```

## 주요 환경변수

`.env.example` 전체 참고. 핵심:

- `JWT_SECRET` — 꼭 변경
- `POSTGRES_PORT` — 호스트에 이미 5432 쓰면 다른 값 (예: 5435)
- `DATABASE_URL` / `ALEMBIC_DATABASE_URL` — 위 포트·비번과 일치해야 함
- `GEMINI_API_KEY` — Gemini 사용 (또는 `GOOGLE_API_KEY`)
- `HEALTHAGI_LLM_BACKEND` — `gemini` | `ollama` | `mock`
- `LLM_*_MODEL` — 기능별 모델
- `HEALTHAGI_STORAGE_BACKEND` — `local` | `minio` | `memory`
