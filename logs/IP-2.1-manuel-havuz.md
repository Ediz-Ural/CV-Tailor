# Log - IP-2.1: Manuel havuz girisi

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-18 17:34
- **Is paketi prompt'u:** `prompts/IP-2.1-manuel-havuz.md`
- **Bagimliliklar (dogrulandi mi?):** IP-2.0 tamamlandi; IP-1.1 tamamlandi; canli embedding boyutu uyumu dogrulandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-2.0-llm-embedding.md` mevcut ve `DURUM: TAMAMLANDI`.
- `logs/IP-1.1-db-sema.md` mevcut ve `DURUM: TAMAMLANDI`.
- Disk kontrolu:
  - `backend/app/models/pool_item.py` mevcut; `PoolItem` modeli `pool_items` tablosunu ve `Vector(EMBEDDING_DIMENSION)` embedding kolonunu tanimliyor.
  - `backend/app/services/embeddings.py` mevcut; `EmbeddingService` ve `detect_language` tanimli.
  - `backend/migrations/versions/20260613_0002_multi_tenant_schema.py` mevcut; `pool_items.embedding` migration'da `Vector(dim=1024)`.
- Canli kontrol:
  ```text
  docker compose -f infra/docker-compose.yml up -d db
  docker compose -f infra/docker-compose.yml exec -T db psql -U cv_tailor -d cv_tailor -c "SELECT format_type(a.atttypid, a.atttypmod) AS embedding_type FROM pg_attribute a JOIN pg_class c ON a.attrelid = c.oid WHERE c.relname = 'pool_items' AND a.attname = 'embedding';"
  docker compose -f infra/docker-compose.yml run --rm backend uv run --no-sync python -c "from app.core.config import EMBEDDING_DIMENSION; from app.db.base import Base; import app.models; col=Base.metadata.tables['pool_items'].c.embedding; print(EMBEDDING_DIMENSION, col.type.dim)"
  ```
- Cikti ozeti: DB `embedding_type = vector(1024)` dondurdu. Backend metadata kontrolu `1024 1024` dondurdu.

## 2. Yapilan isler (FAZ B)
- [x] `pool_items` CRUD endpoint'leri eklendi: `POST /pool-items`, `GET /pool-items`, `GET /pool-items/{item_id}`, `PUT /pool-items/{item_id}`, `PATCH /pool-items/{item_id}`, `DELETE /pool-items/{item_id}`.
- [x] Kullaniciya ozel tenant izolasyonu tum sorgularda `TenantScope.apply(..., PoolItem)` ile uygulandi.
- [x] Manuel kayitta otomatik metadata eklendi: `source=manual`, `language=detect_language(raw_content)`, `embedding=EmbeddingService.embed(raw_content)`, `verified_by_user=true`.
- [x] `PUT` tum alanlari degistirirken embedding ve dil bilgisini yeniden uretir. `PATCH` sadece `raw_content` degisirse embedding ve dil bilgisini yeniden uretir.
- [x] Testlerde manuel ekleme, DB'de embedding yazimi ve baska kullanicinin ogelerine erisememe kontrol edildi.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/api/pool_items.py` | yeni | Tenant izole manuel havuz CRUD endpoint'leri |
| `backend/app/schemas/pool_item.py` | yeni | Havuz istek/yanit Pydantic semalari |
| `backend/tests/test_pool_items.py` | yeni | Manuel kayit, DB embedding kaniti, tenant izolasyonu ve validasyon testleri |
| `backend/app/main.py` | degisti | `pool_items` router kaydi |
| `backend/app/models/pool_item.py` | degisti | Yanitlarda embedding boyutunu gosteren `embedding_dimensions` property |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Kullanici manuel oge ekleyebiliyor, embedding DB'ye yaziliyor.
- **Calistirilan komutlar:**
  ```text
  docker compose -f infra/docker-compose.yml --profile app build backend
  docker compose -f infra/docker-compose.yml run --rm backend uv run --no-sync alembic upgrade head
  docker compose -f infra/docker-compose.yml run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/test_pool_items.py -q -p no:cacheprovider --basetemp=/tmp/ip21-pool"
  docker compose -f infra/docker-compose.yml run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest -q -p no:cacheprovider --basetemp=/tmp/ip21-full"
  ```
- **Cikti ozeti:** `tests/test_pool_items.py` sonucu `3 passed, 1 warning`. Tam backend test paketi `22 passed, 1 warning`. Yeni test, `POST /pool-items` sonrasi DB'deki `PoolItem.embedding` alaninin dolu ve `1024` boyutlu oldugunu, `source=manual`, `verified_by_user=true`, `language=en/tr` set edildigini dogruladi. Izolasyon testinde ikinci kullanici birinci kullanicinin ogesine `GET/PATCH/DELETE` ile erisemedi (`404`).
- **Sonuc:** DoD karsilandi.

## 5. Endpoint listesi
- `POST /pool-items`
- `GET /pool-items`
- `GET /pool-items/{item_id}`
- `PUT /pool-items/{item_id}`
- `PATCH /pool-items/{item_id}`
- `DELETE /pool-items/{item_id}`

## 6. Sonraki paket icin notlar
- IP-2.2 ve IP-2.3 ayni `pool_items` model formatina yazmali; otomatik kaynaklarda `verified_by_user=false` baslamali.
- IP-2.6 frontend manuel formu `type`, `title`, `raw_content`, `tags`, `technologies` alanlarini bu endpointlere gonderebilir.
- IP-2.6 liste ekraninda `source`, `language`, `verified_by_user`, `embedding_dimensions` alanlari hazir.
- IP-3.2 selector, `verified_by_user=true` ve tenant filtreli `pool_items` uzerinden secim yapmali.

## 7. Acik sorunlar / bayraklar
- Testlerde embedding model indirmesini ve dis bagimlilik maliyetini onlemek icin FastAPI dependency override ile deterministik 1024 boyutlu fake embedding servisi kullanildi. IP-2.0'da gercek modelin 1024 boyut urettigi ayrica dogrulanmisti.
- FastAPI TestClient kaynakli Starlette deprecation warning'i devam ediyor; test sonucunu etkilemiyor.
