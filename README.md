# healthAGI

개인용 헬스 건강 관리 모바일 앱.

- **Mobile**: Expo SDK 55 (React Native, iOS + Android)
- **Backend**: Python 3.12 + FastAPI, PostgreSQL 16
- **AI**: 자체 호스팅 Ollama (Gemma 3 / Qwen 2.5) + faster-whisper STT + Coqui XTTS v2 TTS
- **외부 접속**: Cloudflare Tunnel + 도메인

전체 설계는 `docs/architecture.md` 참고.

## 현재 진행 상황 (Phase 0 + 1)

- 인프라 스캐폴드 (docker-compose, 모노레포)
- 인증 (이메일 + 비밀번호 + JWT)
- 프로필 / 신체 지표 기록
- 회복 타이머 (오프라인 우선, 로컬 알림 예약)

## 빠른 시작

### 백엔드

```bash
cd backend
uv sync                          # 또는 pip install -e .
docker compose up -d postgres    # 또는 전체 docker compose up
alembic upgrade head
uvicorn app.main:app --reload
```

API 문서: http://localhost:8000/docs

### 모바일

```bash
cd mobile
pnpm install
pnpm start                       # Expo Dev Server
```

## 디렉터리

```
healthAGI/
  backend/        FastAPI 서비스
  mobile/         Expo 앱
  infra/          cloudflared, nginx, systemd 유닛
  docs/           설계 문서
  docker-compose.yml
  .env.example
  Makefile
```

## 주요 환경변수

`.env.example` 참고. 핵심:

- `DATABASE_URL` — postgres 연결 문자열
- `JWT_SECRET` — 서버 비밀
- `OLLAMA_BASE_URL` — `http://ollama:11434`
- `LLM_TEXT_MODEL`, `LLM_VISION_MODEL`, `LLM_VOICE_MODEL`
- `MINIO_*` — 사진 저장용
