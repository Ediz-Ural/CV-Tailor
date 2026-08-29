# Log - IP-2.4: ItemExtractor + onay akisi

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-18 18:20
- **Is paketi prompt'u:** `prompts/IP-2.4-itemextractor-onay.md`
- **Bagimliliklar (dogrulandi mi?):** IP-2.2 tamamlandi; IP-2.3 tamamlandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-2.2-pdf-parser.md` mevcut ve `DURUM: TAMAMLANDI`.
- `logs/IP-2.3-github-analiz.md` mevcut ve `DURUM: TAMAMLANDI`.
- Disk kontrolu:
  - `backend/app/api/pdf_import.py` mevcut; PDF import akisi `source=pdf`, `verified_by_user=false` kayit uretiyor.
  - `backend/app/services/github.py` mevcut; GitHub analizi `source=github`, `verified_by_user=false` kayit uretiyor.
  - `backend/app/models/pool_item.py` mevcut; `source`, `type`, `language`, `embedding`, `verified_by_user` alanlari hazir.
- Pre-flight komutu:
  ```text
  docker compose -f infra/docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/test_pdf_import.py tests/test_github_integration.py -q -p no:cacheprovider --basetemp=/tmp/ip24-preflight"
  ```
- Cikti ozeti: `6 passed, 1 warning`. PDF ve GitHub testleri otomatik cikarimlarin onaysiz (`verified_by_user=false`) olarak DB'ye yazildigini dogruladi.

## 2. Yapilan isler (FAZ B)
- [x] ItemExtractor servisi eklendi: `backend/app/services/item_extractor.py`.
  - PDF ve GitHub cikarimlari `ExtractedPoolItem` uzerinden tek `pool_items` formatina normalize ediliyor.
  - Normalize kurallari: `source`, `type`, `title`, `raw_content`, `tags`, `technologies`; bosluk temizleme; `tags`/`technologies` icinde tekrar eden stringleri tekillestirme; `detect_language(raw_content)`; `EmbeddingService.embed(raw_content)`; otomatik kayitlarda her zaman `verified_by_user=false`.
- [x] PDF import akisi ortak ItemExtractor normalizasyonuna tasindi: `backend/app/api/pdf_import.py`.
- [x] GitHub analiz akisi ortak ItemExtractor normalizasyonuna tasindi: `backend/app/services/github.py`.
- [x] Onay endpoint'leri eklendi: `backend/app/api/pool.py`.
  - `GET /pool/pending`: mevcut kullanicinin `source in (pdf, github)` ve `verified_by_user=false` ogelerini dondurur.
  - `POST /pool/approve`: verilen id listesinden sadece mevcut kullanicinin pending otomatik ogelerini `verified_by_user=true` yapar.
  - `POST /pool/reject`: verilen id listesinden sadece mevcut kullanicinin pending otomatik ogelerini siler.
- [x] Endpoint semalari eklendi: `PoolItemIdList`, `PoolApprovalResponse`, `PoolRejectResponse`.
- [x] Router uygulamaya baglandi: `backend/app/main.py`.
- [x] Etik kural testle korundu: otomatik ogeler onaysiz pending olarak gorunur; approve edilmeden `verified_by_user=true` olmaz; baska kullanicinin pending ogelerine approve/reject ile erisilemez.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/services/item_extractor.py` | yeni | Ortak otomatik cikarim normalizasyonu, pending sorgusu, approve/reject yardimcilari |
| `backend/app/api/pool.py` | yeni | `/pool/pending`, `/pool/approve`, `/pool/reject` endpointleri |
| `backend/tests/test_pool_approval.py` | yeni | Pending, approve, reject ve tenant izolasyonu testleri |
| `backend/app/api/pdf_import.py` | degisti | PDF cikarimlarini ItemExtractor servisiyle normalize eder |
| `backend/app/services/github.py` | degisti | GitHub cikarimlarini ItemExtractor servisiyle normalize eder |
| `backend/app/schemas/pool_item.py` | degisti | Onay/ret istek ve yanit semalari |
| `backend/app/main.py` | degisti | `/pool` router kaydi |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Otomatik cikarilan hicbir oge kullanici onayi olmadan CV'ye girmiyor.
- **Calistirilan komutlar:**
  ```text
  docker compose -f infra/docker-compose.yml --profile app build backend
  docker compose -f infra/docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/test_pool_approval.py tests/test_pdf_import.py tests/test_github_integration.py tests/test_pool_items.py -q -p no:cacheprovider --basetemp=/tmp/ip24-target-3"
  docker compose -f infra/docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/ -q -p no:cacheprovider --basetemp=/tmp/ip24-full"
  ```
- **Cikti ozeti:**
  - Hedef regresyon: `11 passed, 1 warning in 12.02s`.
  - Tam backend test paketi: `30 passed, 1 warning in 21.16s`.
- **Endpoint kaniti:**
  - `test_pending_approve_and_reject_flow_for_automatic_items`: `/pool/pending` PDF/GitHub onaysizlari dondurdu; `/pool/approve` secilen kaydi `verified_by_user=true` yapti; `/pool/reject` secilen kaydi sildi.
  - `test_pending_pool_items_are_tenant_isolated`: ikinci kullanici sadece kendi pending kaydini gordu; baskasinin id'siyle approve/reject `0` sonuc verdi ve kayit onaysiz kaldi.
- **Etik kanit:** `create_unverified_pool_items` ve `normalize_extracted_item` otomatik PDF/GitHub kayitlarini daima `verified_by_user=false` olusturuyor; sadece `/pool/approve` mevcut kullanicinin pending otomatik ogelerini true yapiyor.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-2.5 Graph 1 orkestrasyonunda PDFParser ve GitHubAnalyzer ciktisi `ExtractedPoolItem`/ItemExtractor yoluyla normalize edilebilir.
- Onay akisi icin frontend IP-2.6 su endpointleri kullanacak: `GET /pool/pending`, `POST /pool/approve`, `POST /pool/reject`.
- Reddedilen ogeler su an fiziksel olarak siliniyor; soft-delete kolonu yok.
- Tekilleme mevcut kapsamda `tags` ve `technologies` listeleri icin yapildi. Benzer icerik dedup'u eklenmedi.

## 6. Acik sorunlar / bayraklar
- FastAPI TestClient kaynakli mevcut Starlette deprecation warning'i devam ediyor; test sonucunu etkilemiyor.
