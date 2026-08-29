# Log - IP-3.1: Ilan girisi + JobParser

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-18 19:13
- **Is paketi prompt'u:** `prompts/IP-3.1-jobparser.md`
- **Bagimliliklar (dogrulandi mi?):** IP-2.0 tamamlandi; IP-1.1 tamamlandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-2.0-llm-embedding.md` mevcut ve `DURUM: TAMAMLANDI`.
- `logs/IP-1.1-db-sema.md` mevcut ve `DURUM: TAMAMLANDI`.
- `backend/app/models/job.py` ve `backend/migrations/versions/20260613_0002_multi_tenant_schema.py` uzerinden `jobs` tablosu, `user_id` indeksi, `source_url`, `raw_text`, `detected_language`, `parsed_requirements_json` alanlari dogrulandi.
- `backend/app/services/llm.py` uzerinden structured LLM cagrisi (`LLMService.structured`) dogrulandi.
- `backend/app/services/embeddings.py` uzerinden `detect_language(text) -> tr|en|mixed` dogrulandi.

## 2. Yapilan isler (FAZ B)
- [x] Ilan girisi endpoint'i eklendi: `POST /jobs`, `raw_text` veya `source_url` alanlarindan tam olarak birini kabul eder.
- [x] URL girisinde yalnizca verilen URL icin tek HTTP GET yapilir; sayfa icindeki linkler takip edilmez, toplu tarama/scraping yoktur.
- [x] `JobParser` eklendi: ilan dilini `detect_language` temeliyle belirler; karma ilanda CV cikti dili icin baskin dili `tr` veya `en` olarak secer.
- [x] Structured gereksinim JSON semasi eklendi: `required_skills`, `preferred_skills`, `years_experience`, `key_terms`.
- [x] Teknik terimleri koruyan, uydurma gereksinim istemeyen LLM system/user prompt'u eklendi.
- [x] `jobs` tablosuna `source_url`, `raw_text`, `detected_language`, `parsed_requirements_json`, `user_id` ile kayit yapilir.
- [x] `GET /jobs`, `GET /jobs/{id}`, `DELETE /jobs/{id}` tenant scope ile eklendi.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/schemas/job.py` | yeni | Job girisi, yaniti ve gereksinim JSON semasi |
| `backend/app/services/job_parser.py` | yeni | JobParser, dominant dil secimi, tek sayfa URL fetch ve HTML text cikarimi |
| `backend/app/api/jobs.py` | yeni | Multi-tenant jobs endpointleri |
| `backend/app/main.py` | degisti | Jobs router FastAPI uygulamasina baglandi |
| `backend/tests/test_jobs.py` | yeni | TR/EN/karma dil, URL tek sayfa fetch, JSON sema ve tenant izolasyon testleri |
| `logs/IP-3.1-jobparser.md` | yeni | Bu paket kanit kaydi |
| `state/PROGRESS.md` | degisti | IP-3.1 satiri tamamlandi olarak guncellendi |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Ilan yapistir/URL ver -> dili tespit edilmis, structured gereksinimler JSON olarak elde.
- **Calistirilan komutlar:**
  ```text
  docker compose -f infra\docker-compose.yml --profile app build backend
  docker compose -f infra\docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/test_jobs.py -q -p no:cacheprovider"
  docker compose -f infra\docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest -q -p no:cacheprovider --basetemp=/tmp/ip31-full"
  ```
- **Cikti ozeti:** Hedef testler `4 passed, 2 warnings`. Tum backend testleri `36 passed, 2 warnings`. Uyarilar mevcut Starlette TestClient ve LangGraph deprecation uyarilaridir.
- **Dil tespiti kaniti:** `tests/test_jobs.py` TR ilan icin `detected_language=tr`, EN ilan icin `detected_language=en`, karma ilan icin baskin dil `tr` bekler ve gecmistir.
- **URL fetch siniri kaniti:** `tests/test_jobs.py` mock HTTP transport ile yalnizca `https://example.test/job` URL'sinin istendigini, sayfadaki `next` linkinin fetch edilmedigini `requested_urls == ["https://example.test/job"]` ile dogrular.
- **JSON sema kaniti:** Testte kaydedilen `parsed_requirements_json` su alanlari icerir: `required_skills`, `preferred_skills`, `years_experience`, `key_terms`.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-3.2 Selector, ilan gereksinimlerini `jobs.parsed_requirements_json` icindeki `required_skills`, `preferred_skills`, `years_experience`, `key_terms` alanlarindan okuyabilir.
- Selector icin job satirlari `user_id` ile izoledir; listeleme ve okuma endpointleri tenant scope uygular.
- Karma ilanlarda `jobs.detected_language` CV cikti dili olarak kullanilacak baskin dile set edilir.

## 6. Acik sorunlar / bayraklar
- Gercek LLM API anahtari testlerde kullanilmadi; structured LLM entegrasyonu mock servisle, ortak `LLMService.structured` sozlesmesi uzerinden dogrulandi.
