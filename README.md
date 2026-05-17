# healthAGI

개인용 헬스 건강 관리 모바일 앱.

- **Mobile**: Expo SDK 55 (React Native, iOS + Android)
- **Backend**: Python 3.12 + FastAPI, PostgreSQL 16
- **AI**: Google Gemini API (기본) · 또는 자체 호스팅 Ollama로 전환 가능
- **음성**: faster-whisper STT + XTTS v2 / Piper TTS (로컬, optional extras)
- **외부 접속**: Cloudflare Tunnel + 도메인

전체 설계는 `docs/architecture.md` 참고.

## 기능

- Phase 0: 모노레포 + Docker Compose 부트스트랩
- Phase 1: 인증 (이메일+비밀번호+JWT), 프로필, 오프라인 우선 회복 타이머
- Phase 2: 운동/식단 로깅 + Today 화면 + 체중 빠른 입력
- Phase 3: AI 텍스트 채팅 (SSE 스트리밍) + 자유 텍스트 운동/식단 파서
- Phase 4: 푸시투토크 음성 턴 (STT → LLM → TTS)
- Phase 4.5: 스트리밍 음성 (WebSocket + 문장 단위 TTS + 인터럽트)
- Phase 5: 사진 식단 분석 (비전 LLM)
- Phase 6: 일일 AI 추천 + 운동 종료 시 회복 타이머 제안

## 빠른 시작

### 1) 환경 설정

```bash
cp .env.example .env
# .env 열어서 JWT_SECRET, GEMINI_API_KEY 등 채우기
```

Gemini API 키: https://aistudio.google.com/apikey

### 2) 백엔드

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"        # 기본 (Gemini API 사용)
# 로컬 음성 모드 같이 쓰려면:
.venv/bin/pip install -e ".[dev,voice,storage]"

cd ..
make up         # postgres, minio, ollama 컨테이너 시작
make migrate    # DB 마이그레이션
make api        # FastAPI dev 서버 (http://localhost:8000/docs)
```

테스트:
```bash
make test       # 50 tests passing
```

### 3) 모바일

```bash
cd mobile
pnpm install
pnpm start      # Expo Dev Server
```

`app.json`의 `extra.apiBaseUrl`을 실기기에서 닿는 백엔드 주소로 변경하세요.

## LLM 백엔드 선택

기본은 Gemini API. 환경변수로 전환:

```bash
# Gemini (관리형, 기본)
HEALTHAGI_LLM_BACKEND=gemini
GEMINI_API_KEY=...
LLM_TEXT_MODEL=gemini-2.5-flash

# Ollama (로컬 GPU)
HEALTHAGI_LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_TEXT_MODEL=qwen2.5:7b
```

`GEMINI_API_KEY` 만 설정해도 자동으로 Gemini 백엔드가 선택됩니다.

## 디렉터리

```
healthAGI/
  backend/        FastAPI 서비스
    app/services/llm/   gemini_client.py / ollama_client.py / mock_client.py
  mobile/         Expo 앱
  infra/          cloudflared, nginx, systemd 유닛
  docs/           설계 문서
  docker-compose.yml
  .env.example
  Makefile
```

## 주요 환경변수

`.env.example` 전체 참고. 핵심:

- `DATABASE_URL` / `ALEMBIC_DATABASE_URL` — postgres 연결
- `JWT_SECRET` — 서버 비밀 (꼭 변경)
- `GEMINI_API_KEY` — Gemini API 키 (있으면 기본 백엔드)
- `HEALTHAGI_LLM_BACKEND` — `gemini` | `ollama` | `mock`
- `LLM_TEXT_MODEL` / `LLM_VISION_MODEL` / `LLM_VOICE_MODEL`
- `HEALTHAGI_STT_BACKEND`, `HEALTHAGI_TTS_BACKEND` — 음성 모드 (기본 mock)
- `HEALTHAGI_STORAGE_BACKEND` — `local` | `minio` | `memory`
- `MINIO_*` — 사진 저장용 (MinIO 백엔드일 때)
