# Log - IP-2.2: PDF CV parse

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-18 17:51
- **Is paketi prompt'u:** `prompts/IP-2.2-pdf-parser.md`
- **Bagimliliklar (dogrulandi mi?):** IP-2.0 tamamlandi; IP-2.1 tamamlandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-2.0-llm-embedding.md` mevcut ve `DURUM: TAMAMLANDI`.
- `logs/IP-2.1-manuel-havuz.md` mevcut ve `DURUM: TAMAMLANDI`.
- Disk kontrolu:
  - `backend/app/services/llm.py` mevcut; `LLMService.structured(...)` structured JSON ciktisi uretiyor.
  - `backend/app/services/embeddings.py` mevcut; `EmbeddingService` ve `detect_language` hazir.
  - `backend/app/api/pool_items.py` mevcut; tenant izole `pool_items` CRUD ve embedding yazimi hazir.
  - `backend/app/models/pool_item.py` mevcut; `source`, `type`, `language`, `embedding`, `verified_by_user` alanlari hazir.
- Pre-flight komutu:
  ```text
  docker compose -f infra/docker-compose.yml run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/test_pool_items.py tests/test_ai_services.py -q -p no:cacheprovider --basetemp=/tmp/ip22-preflight"
  ```
- Cikti ozeti: `11 passed, 1 warning`. Sistem Python'inda backend paketleri olmadigi icin ilk yerel `python -m pytest ...` denemesi import hatasiyla basarisiz oldu; kanit Docker backend ortami uzerinden alindi.

## 2. Yapilan isler (FAZ B)
- [x] `POST /pool/import/pdf` endpoint'i eklendi; auth zorunlu, multipart PDF aliyor.
- [x] Dosya tipi kontrolu eklendi: `content_type=application/pdf` ve `.pdf` dosya adi zorunlu.
- [x] Dosya boyut limiti eklendi: `settings.pdf_import_max_bytes` varsayilan `5 MiB`; limit asiminda `413`.
- [x] PDF metin cikarimi `pypdf` ile yapildi; okunamayan veya metinsiz PDF `422` donuyor.
- [x] LLM structured cikarim semasi eklendi: `PDFExtraction.items[]` icinde `kind=experience|education|skill`, `title`, `raw_content`, `tags`, `technologies`.
- [x] Cikarilan ogeler `pool_items` formatina normalize edildi: `source=pdf`, `verified_by_user=false`, dil tespiti ve embedding yazimi.
- [x] `user_id` izolasyonu endpoint seviyesinde `current_user.id` ile kayit, liste/erisime mevcut `pool_items` tenant filtresiyle devam edecek sekilde korundu.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/api/pdf_import.py` | yeni | PDF upload endpoint'i, dosya validasyonu, LLM cikarimi ve pool kaydi |
| `backend/app/schemas/pdf_import.py` | yeni | Structured LLM cikarim ve import response semalari |
| `backend/app/services/pdf_parser.py` | yeni | `pypdf` ile PDF metin cikarimi ve hata sarmalama |
| `backend/tests/test_pdf_import.py` | yeni | Basarili import, bozuk/bos PDF, tip/boyut/auth ve tenant izolasyonu testleri |
| `backend/app/main.py` | degisti | PDF import router kaydi |
| `backend/app/core/config.py` | degisti | `pdf_import_max_bytes` ayari |
| `backend/pyproject.toml` | degisti | `pypdf`, `python-multipart` bagimliliklari |
| `backend/uv.lock` | degisti | `pypdf==6.13.3`, `python-multipart==0.0.32` lock kaydi |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Bir PDF CV yuklenince havuza aday ogeler (onaysiz) dusuyor.
- **Calistirilan komutlar:**
  ```text
  docker run --rm -v "${PWD}:/workspace" -w /workspace/backend ghcr.io/astral-sh/uv:python3.13-bookworm-slim uv lock
  docker compose -f infra/docker-compose.yml --profile app build backend
  docker compose -f infra/docker-compose.yml run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/test_pdf_import.py -q -p no:cacheprovider --basetemp=/tmp/ip22-pdf"
  docker compose -f infra/docker-compose.yml run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest -q -p no:cacheprovider --basetemp=/tmp/ip22-full"
  ```
- **Cikti ozeti:** Lock komutu `Resolved 76 packages`, `Added pypdf v6.13.3`, `Added python-multipart v0.0.32`. Hedef PDF testleri `3 passed, 1 warning`. Tam backend test paketi `25 passed, 1 warning`.
- **Onaysiz kayit kaniti:** `test_pdf_import_creates_unverified_pdf_pool_items_with_embeddings` gercek multipart PDF upload sonrasi 3 adet `source=pdf`, `verified_by_user=false`, `embedding_dimensions=1024` kayit olustugunu ve DB'de embedding alanlarinin dolu oldugunu dogruladi.
- **Bozuk/bos PDF kaniti:** `test_pdf_import_rejects_corrupt_or_empty_pdf_without_crashing` bozuk PDF ve bos PDF icin `422` dondugunu dogruladi.
- **Tenant izolasyonu kaniti:** Ayni testte ikinci kullanicinin `/pool-items` listesinin bos oldugu dogrulandi; kayitlar sadece import eden `user_id` ile olustu.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-2.4 onay akisinda PDF kaynakli ogeler `verified_by_user=false` geldigi icin onay bekleyen aday olarak listelenebilir.
- `pool_items` enum'unda `education` tipi yok; PDF structured `education` kayitlari `type=experience` olarak normalize edildi ve `tags` icine `education` eklendi.
- Gercek LLM cagrisi icin `LLM_API_KEY` gerekir; testlerde LLM ve embedding dependency override ile deterministik dogrulandi.

## 6. Acik sorunlar / bayraklar
- FastAPI TestClient kaynakli Starlette deprecation warning'i devam ediyor; test sonucunu etkilemiyor.
