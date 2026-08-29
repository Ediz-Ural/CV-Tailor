# Log - IP-0.2: Yerel altyapi (Docker Compose + Postgres/pgvector)

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-13
- **Is paketi prompt'u:** `prompts/IP-0.2-docker-altyapi.md`
- **Bagimliliklar (dogrulandi mi?):** IP-0.1 tamamlandi; log, disk ve Git kontrolleri gecti.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-0.1-repo-iskelet.md` mevcut ve `DURUM: TAMAMLANDI`.
- Repo kokunde `backend/`, `frontend/`, `infra/`, `.gitignore` ve `README.md` mevcut.
- `git -C .. status --short` basariyla calisti.

## 2. Yapilan isler (FAZ B)
- [x] `infra/docker-compose.yml` eklendi: `pgvector/pgvector:pg16`, kalici volume, healthcheck ve `app` profili altinda backend/frontend placeholder servisleri.
- [x] `.env.example` gerekli DB, JWT, LLM ve GitHub OAuth degiskenleriyle eklendi.
- [x] `infra/initdb/01-extensions.sql` eklendi ve Compose initdb dizinine salt okunur mount edildi.
- [x] `.env` ignore ediliyor; `.env.example` ignore edilmiyor.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `.env.example` | yeni | Yerel ortam degiskeni ornegi |
| `infra/docker-compose.yml` | yeni | PostgreSQL/pgvector ve uygulama placeholder servisleri |
| `infra/initdb/01-extensions.sql` | yeni | `vector` extension init SQL'i |
| `codex/logs/IP-0.2-docker-altyapi.md` | degisti | Paket kanit kaydi |
| `codex/state/PROGRESS.md` | degisti | IP-0.2 durumu TAMAMLANDI |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** `docker compose -f infra/docker-compose.yml up -d db` ile PostgreSQL + pgvector ayaga kalkar, servis healthy olur ve `vector` extension sorgulanir.
- **Calistirilan komutlar:**
  ```text
  docker compose -f infra/docker-compose.yml config
  docker compose -f infra/docker-compose.yml up -d --wait db
  docker compose -f infra/docker-compose.yml ps
  docker compose -f infra/docker-compose.yml exec -T db psql -U cv_tailor -d cv_tailor -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
  git check-ignore -v .env
  git check-ignore .env.example
  ```
- **Cikti ozeti:** Compose yapilandirmasi basariyla cozuldu. `infra-db-1`, `pgvector/pgvector:pg16` imajiyla `Up (healthy)` durumunda ve `5432` portunu yayinliyor. SQL sorgusu `extversion = 0.8.2` dondurdu. `.env`, `.gitignore` satir 11 ile ignore ediliyor; `.env.example` ignore edilmiyor.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- Veritabani baglanti degerleri varsayilan olarak `cv_tailor / cv_tailor_dev / cv_tailor`; uygulamalar `.env` ile bunlari ezebilir.
- Backend container icinden varsayilan URL `postgresql://cv_tailor:cv_tailor_dev@db:5432/cv_tailor`.
- `db` servisi oturum sonunda calisir durumda birakildi.

## 6. Acik sorunlar / bayraklar
- Yok.
