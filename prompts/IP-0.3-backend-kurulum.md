# PROMPT — IP-0.3: Backend temel kurulum (FastAPI)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-0.3-backend-kurulum`
- **Bağımlılıklar:** IP-0.2
- **Referans:** PROJECT_CONTEXT §4 · IS_PAKETLERI İP-0.3

---

## FAZ A — ÖN KONTROL (bir önceki işi DOĞRULA)
- [ ] `logs/IP-0.2-docker-altyapi.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte gerçekten var: `infra/docker-compose.yml`, `.env.example`, pgvector init SQL'i.
- [ ] db servisi ayağa kalkabiliyor (gerekirse `docker compose up -d db` + pgvector kontrolü).
> ⛔ Eksikse: `logs/BLOCKED-IP-0.3.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] `backend/` içinde Python projesi başlat (uv veya poetry). Bağımlılıklar:
      `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings`, `sqlalchemy>=2` (veya `sqlmodel`),
      `alembic`, `psycopg[binary]`, `pgvector`, `python-jose[cryptography]` (veya `pyjwt`), `passlib[bcrypt]`.
- [ ] `backend/app/main.py`: FastAPI app + `GET /health` → `{"status":"ok"}`.
- [ ] `backend/app/core/config.py`: `pydantic-settings` ile `.env` okuyan `Settings` (DATABASE_URL, JWT_SECRET vb.).
- [ ] `backend/app/db/session.py`: SQLAlchemy engine + session (DATABASE_URL ile).
- [ ] Alembic kur: `backend/alembic.ini` + `backend/migrations/` (env Postgres'e bağlanır).
- [ ] `backend/Dockerfile` + `infra/docker-compose.yml`'deki `backend` servisini gerçek build context'e bağla.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** `GET /health` → `200 {"status":"ok"}`.
- [ ] Komut: backend'i çalıştır (lokal `uvicorn app.main:app` veya compose) ve `curl http://localhost:8000/health`.
- [ ] Komut: `alembic upgrade head` hatasız çalışıyor (boş da olsa migration zinciri kurulu).
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-0.3-backend-kurulum.md` yaz (LOG_TEMPLATE; kullanılan port, bağımlılık yöneticisi, health kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (port, çalıştırma komutu, sonraki paket IP-0.4 ve IP-1.1). Temiz çık.
