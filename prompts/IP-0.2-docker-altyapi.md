# PROMPT — IP-0.2: Yerel altyapı (Docker Compose + Postgres/pgvector)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-0.2-docker-altyapi`
- **Bağımlılıklar:** IP-0.1
- **Referans:** PROJECT_CONTEXT §4, §0.2 · IS_PAKETLERI İP-0.2

---

## FAZ A — ÖN KONTROL (bir önceki işi DOĞRULA — sadece log'a güvenme)
- [ ] `logs/IP-0.1-repo-iskelet.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte gerçekten var: `backend/`, `frontend/`, `infra/`, kök `.gitignore`, kök `README.md`.
- [ ] `git status` çalışıyor (repo başlatılmış).
> ⛔ Biri eksikse: `logs/BLOCKED-IP-0.2.md` yaz (neyin eksik olduğu), DUR, devam etme.

## FAZ B — GÖREV (checklist)
- [ ] `infra/docker-compose.yml` oluştur:
  - `db` servisi: imaj `pgvector/pgvector:pg16` (veya güncel), port 5432, volume, healthcheck.
  - `backend` ve `frontend` servisleri için placeholder (build context ileride doldurulacak) — şimdilik db zorunlu.
  - Ortam değişkenleri `.env`'den okunur.
- [ ] Kök `.env.example` oluştur: `DATABASE_URL`, `POSTGRES_USER/PASSWORD/DB`, `JWT_SECRET`,
      `LLM_API_KEY`, `LLM_PROVIDER`, `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET` (placeholder değerlerle).
- [ ] pgvector extension migration'ı için hazırlık: `infra/initdb/01-extensions.sql` →
      `CREATE EXTENSION IF NOT EXISTS vector;` (compose'ta initdb olarak mount et).
- [ ] `.gitignore`'a `.env` zaten ekli olduğunu doğrula; `.env.example` izlenir.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** `docker compose -f infra/docker-compose.yml up -d db` ile Postgres + pgvector ayağa kalkıyor.
- [ ] Komut: `docker compose -f infra/docker-compose.yml ps` → db healthy.
- [ ] Komut: db içinde `SELECT extversion FROM pg_extension WHERE extname='vector';` sonuç döndürüyor.
      (`docker compose exec db psql -U <user> -d <db> -c "..."`)
- [ ] Çıktı özetlerini logla.

## FAZ D — KAYIT
- [ ] `logs/IP-0.2-docker-altyapi.md` yaz (LOG_TEMPLATE; çalıştırılan compose komutları + pgvector kanıtı).
- [ ] `state/PROGRESS.md`'de IP-0.2 satırını güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver, db servisini bırakıp bırakmadığını belirt. Temiz çık.
