# Log - IP-1.1: Veritabani semasi (multi-tenant)

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-13 15:17
- **Is paketi prompt'u:** `prompts/IP-1.1-db-sema.md`
- **Bagimliliklar (dogrulandi mi?):** IP-0.3 tamamlandi; log, disk, pgvector servisi ve Alembic upgrade kontrolleri gecti.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-0.3-backend-kurulum.md` mevcut ve `DURUM: TAMAMLANDI`.
- `backend/app/db/session.py`, `backend/alembic.ini` ve migration altyapisi diskte mevcut.
- `infra-db-1` servisi `pgvector/pgvector:pg16` imajiyla healthy durumdaydi.
- `docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run --no-sync alembic upgrade head` basarili oldu.

## 2. Yapilan isler (FAZ B)
- [x] `users`: email, parola hash'i, olusturma zamani ve KVKK onay zamani alanlari eklendi.
- [x] `profiles`: indeksli `user_id` FK, iletisim, egitim dizisi ve kisisel bilgi alanlari eklendi.
- [x] `pool_items`: kaynak/tip/dil enumlari, metin ve etiket alanlari, `vector(1024)` embedding, onay durumu ve zaman alani eklendi.
- [x] `jobs`: indeksli `user_id` FK, ilan girdisi, dil ve JSONB gereksinim alanlari eklendi.
- [x] `generated_cvs`: indeksli `user_id` FK, `job_id` FK, secilen pool UUID dizisi, cikti ve ATS alanlari eklendi.
- [x] `github_connections`: indeksli `user_id` FK, GitHub kullanici adi, sifreli token ve senkron zamani eklendi.
- [x] Sabit embedding boyutu `EMBEDDING_DIMENSION = 1024` olarak config'e eklendi ve modelde kullanildi.
- [x] Tek yeni Alembic migration'i `20260613_0002` olarak olusturuldu.
- [x] SQLAlchemy metadata Alembic autogenerate yapisina baglandi.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/core/config.py` | degisti | `EMBEDDING_DIMENSION = 1024` sabiti |
| `backend/app/db/base.py` | yeni | SQLAlchemy declarative base |
| `backend/app/models/` | yeni | Alti tablo modeli ve enumlar |
| `backend/migrations/env.py` | degisti | Model metadata baglantisi |
| `backend/migrations/versions/20260613_0002_multi_tenant_schema.py` | yeni | Tek sema migration'i |
| `backend/tests/test_models.py` | yeni | Tablo, tenant FK/index ve vector boyutu testleri |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Migration uygulanir; alti tablo olusur; embedding kolonu pgvector tipindedir.
- **Calistirilan komutlar:**
  ```text
  docker compose -f infra/docker-compose.yml --profile app build backend
  docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run pytest -q
  docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run --no-sync alembic upgrade head
  docker compose -f infra/docker-compose.yml exec -T db psql ... SELECT table_name FROM information_schema.tables ...
  docker compose -f infra/docker-compose.yml exec -T db psql ... SELECT ... format_type(...) ... embedding ...
  docker compose -f infra/docker-compose.yml exec -T db psql ... SELECT tablename, indexname FROM pg_indexes ...
  docker compose -f infra/docker-compose.yml exec -T db psql ... SELECT enum degerleri ...
  docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run --no-sync alembic check
  ```
- **Cikti ozeti:** Pytest `4 passed, 1 warning`. Alembic `20260613_0002 (head)` revizyonuna geldi. Sorgu `users`, `profiles`, `pool_items`, `jobs`, `generated_cvs`, `github_connections` olmak uzere 6 satir dondurdu. Embedding tipi `vector(1024)` olarak raporlandi. Bes tenant tablosunda `ix_<table>_user_id` indeksi goruldu. Alembic check `No new upgrade operations detected.` dondurdu.
- **Enum degerleri:** `pool_item_source = pdf|github|manual`; `pool_item_type = experience|project|skill`; `content_language = tr|en|mixed`.
- **Indexler:** `ix_profiles_user_id`, `ix_pool_items_user_id`, `ix_jobs_user_id`, `ix_generated_cvs_user_id`, `ix_github_connections_user_id`.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-2.0 embedding servisi tam olarak 1024 boyutlu vektor uretmelidir; model degisirse config sabiti ve yeni migration birlikte guncellenmelidir.
- `users` tenant kok tablosudur; kendi `id` alani tenant kimligidir. Diger bes uygulama tablosu indeksli `user_id -> users.id` FK ile izole edilir.
- pgvector ivfflat/hnsw indeksi veri hacmi ve sorgu operatoru belirlendiginde sonraki pakette eklenebilir.
- Tum tenant FK'lerinde hesap silme akisina hazirlik icin `ON DELETE CASCADE` vardir.

## 6. Acik sorunlar / bayraklar
- FastAPI TestClient kaynakli mevcut Starlette deprecation warning'i devam ediyor; test sonucunu etkilemiyor.
