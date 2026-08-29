# Log - IP-5.3: Gozlemlenebilirlik ve dagitim

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-21 14:06
- **Is paketi prompt'u:** `prompts/IP-5.3-gozlemlenebilirlik-dagitim.md`
- **Bagimliliklar (dogrulandi mi?):** IP-3.6 evet / IP-5.2 evet

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-3.6-graph2-orkestrasyon.md` mevcut ve `DURUM: TAMAMLANDI`.
- `logs/IP-5.2-test-kalite.md` mevcut ve `DURUM: TAMAMLANDI`.
- Diskte dogrulanan ana dosyalar: `backend/app/main.py`, `backend/app/graphs/cv_graph.py`, `backend/app/api/cv_generation.py`, `frontend/src/App.tsx`, `infra/docker-compose.yml`, `backend/Dockerfile`.
- On kontrol sonucu: backend + frontend + pipeline dosyalari ve docker-compose mevcut.

## 2. Yapilan isler (FAZ B)
- [x] Yapisal JSON loglama eklendi: `backend/app/core/logging.py`, request middleware `backend/app/main.py`.
- [x] Pipeline adim sureleri ve hata eventleri eklendi: `backend/app/services/cv_progress.py`, `backend/app/api/cv_generation.py`.
- [x] Health + temel metrikler eklendi: `GET /health`, `GET /metrics`.
- [x] LLM/render kuyrugu gorunurlugu eklendi: pipeline status/metrikleri ve `render_queue` sayaclari.
- [x] Production Dockerfile/compose eklendi: `backend/Dockerfile`, `backend/docker-entrypoint.sh`, `frontend/Dockerfile`, `frontend/nginx.conf`, `infra/docker-compose.prod.yml`.
- [x] Ortam degiskenleri dokumani guncellendi: `.env.example`, `frontend/.env.example`.
- [x] `README.md` dagitim, health/metrics ve smoke akis talimatlariyla guncellendi.
- [x] Deployment smoke icin acik opt-in `LLM_PROVIDER=mock` ve `EMBEDDING_MODEL=mock` modu eklendi; varsayilan production degerleri gercek provider/model olarak kaldi.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/core/logging.py` | degisti | JSON log formatter + hassas veri maskeleme |
| `backend/app/core/config.py` | degisti | `LOG_LEVEL`, `LOG_FORMAT` ayarlari |
| `backend/app/main.py` | degisti | request log middleware, DB health, metrics endpoint |
| `backend/app/services/cv_progress.py` | degisti | step start/end, `duration_ms`, pipeline metrikleri |
| `backend/app/api/cv_generation.py` | degisti | pipeline event loglari ve hata loglama |
| `backend/app/services/render_queue.py` | degisti | render queue sayaclari ve render sureleri |
| `backend/app/services/llm.py` | degisti | deployment smoke icin `mock` provider |
| `backend/app/services/embeddings.py` | degisti | deployment smoke icin `mock` embedding encoder |
| `backend/Dockerfile` | degisti | production entrypoint ve Python runtime env |
| `backend/docker-entrypoint.sh` | yeni | container baslangicinda Alembic migration |
| `frontend/Dockerfile` | yeni | Vite build + nginx production image |
| `frontend/nginx.conf` | yeni | SPA fallback ve `/api` reverse proxy |
| `frontend/.dockerignore` | yeni | frontend Docker context temizligi |
| `infra/docker-compose.prod.yml` | yeni | production DB/backend/frontend stack |
| `.env.example` | degisti | production env degiskenleri ve aciklamalari |
| `frontend/.env.example` | degisti | production `/api` varsayilani |
| `README.md` | degisti | deployment ve smoke talimatlari |
| `backend/tests/test_health.py` | degisti | health/metrics testleri |
| `backend/tests/test_cv_graph.py` | degisti | step duration dogrulamasi |
| `backend/tests/test_ai_services.py` | degisti | mock LLM/embedding testleri |
| `logs/IP-5.3-gozlemlenebilirlik-dagitim.md` | yeni | Bu paket kanit kaydi |
| `state/PROGRESS.md` | degisti | IP-5.3 durumu TAMAMLANDI |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Uygulama bir ortama dagitilip uctan uca calisiyor.
- **Calistirilan komutlar:**
  ```
  python -m pytest backend/tests/ -q -p no:cacheprovider
  npm run lint
  npm run build
  docker compose --env-file .env.example -f infra/docker-compose.prod.yml build
  $env:POSTGRES_PASSWORD='cv_tailor_dev'; $env:DATABASE_URL='postgresql+psycopg://cv_tailor:cv_tailor_dev@db:5432/cv_tailor'; $env:LLM_PROVIDER='mock'; $env:LLM_API_KEY=''; $env:EMBEDDING_MODEL='mock'; docker compose --env-file .env.example -f infra/docker-compose.prod.yml up -d --force-recreate
  Invoke-RestMethod -Uri http://localhost:8080/api/health
  Invoke-RestMethod -Uri http://localhost:8080/api/metrics
  Production HTTP smoke: register -> login -> pool item -> POST /api/cv-generation -> GET /api/cv-generation/{pipeline_id}
  docker compose --env-file .env.example -f infra/docker-compose.prod.yml logs --tail=1000 backend | Select-String -Pattern 'pipeline_step_completed|pipeline_completed'
  docker compose --env-file .env.example -f infra/docker-compose.prod.yml down
  ```
- **Cikti ozeti:**
  - Backend testleri: `61 passed, 2 warnings in 29.63s`.
  - Frontend lint: `eslint .` basarili.
  - Frontend build: `tsc -b && vite build` basarili; Vite `built in 3.89s`.
  - Production imajlari: `infra-backend` ve `infra-frontend` build edildi.
  - Production stack: `db`, `backend`, `frontend` ayaga kalkti; backend `healthy`.
  - `GET http://localhost:8080/api/health`: `{"status":"ok","checks":{"database":"ok"}}`.
  - `GET http://localhost:8080/api/metrics`: `pipelines`, `step_duration_ms`, `render_queue` alanlari dondu.
  - Smoke akis sonucu: `pipeline_status=completed`, `generated_cv_id=04a13fe7-c2d6-42d1-b977-a9b52d9a1adb`, `ats_score=88.24`, `render_completed=1`.
  - Status step sureleri: `job_parser=29.77`, `selector=11.91`, `cvtailor=4.15`, `evaluator=3.42`, `typst_renderer=563.09`.
  - Backend JSON loglari: `pipeline_step_completed` eventleri ve `pipeline_completed duration_ms=614.97` goruldu.
  - Dogrulama sonunda production stack `down` ile kapatildi.
- **Ek gercek LLM dogrulamasi (kullanici istegiyle):**
  - Production stack `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini`, `.env` icindeki gercek `LLM_API_KEY` ve `EMBEDDING_MODEL=mock` ile tekrar ayaga kaldirildi.
  - Ilk denemede OpenAI `400 Bad Request` dondu; neden OpenAI strict JSON schema gereksinimleriyle Pydantic default alanlarinin uyumsuz olmasiydi.
  - `backend/app/services/llm.py` icinde OpenAI icin strict JSON schema normalizasyonu eklendi: object alanlarinda `required` tum property'leri kapsiyor ve `additionalProperties=false`.
  - Tekrar calistirilan gercek LLM smoke sonucu: `pipeline_status=completed`, `generated_cv_id=9b20c057-7ef0-4f3b-9e23-c59fe18f6212`, `ats_score=70.97`.
  - Gercek LLM step sureleri: `job_parser=2483.54`, `selector=1547.22`, `cvtailor=2367.62`, `evaluator=8.07`, `typst_renderer=647.79`.
  - OpenAI cagri kaniti backend logunda goruldu: `POST https://api.openai.com/v1/chat/completions` once `400`, schema duzeltmesi sonrasi pipeline tamamlandi. API anahtari loglara yazdirilmadi.
  - Logging regresyonu bulundu ve duzeltildi: hassas veri redaction LogRecordFactory seviyesinde kaldi, ancak `uvicorn.*` logger'lari haric tutuldu; boylece `uvicorn.access` formatter bozulmuyor.
  - Son dogrulamalar: `python -m pytest backend/tests/ -q -p no:cacheprovider` -> `62 passed, 2 warnings`; `npm run lint` basarili; `npm run build` basarili; production backend imaji yeniden build edildi.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- Production smoke icin `LLM_PROVIDER=mock` ve `EMBEDDING_MODEL=mock` sadece acik opt-in olarak kullanildi. Gercek production icin `.env.example` varsayilanlari OpenAI ve gercek embedding modelinde kaldi.
- Mevcut Docker volume daha once `cv_tailor_dev` parolasiyla olusturuldugu icin dogrulamada gecici process env ile `POSTGRES_PASSWORD` ve `DATABASE_URL` buna esitlendi; yeni temiz production volume'da `.env` degerleri kendi icinde tutarli olmalidir.
- `cv_progress_store` process ici kalmaya devam ediyor; coklu replica icin ileride Redis/Postgres tabanli kalici progress store gerekir.

## 6. Acik sorunlar / bayraklar
- Uzak CI veya harici production ortami tetiklenmedi; dogrulama yerel Docker Compose production stack uzerinde yapildi.
