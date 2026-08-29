# Log - IP-2.5: Graph 1 orkestrasyonu

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-18 18:36
- **Is paketi prompt'u:** `prompts/IP-2.5-graph1-orkestrasyon.md`
- **Bagimliliklar (dogrulandi mi?):** IP-2.4 tamamlandi; zincir loglari IP-2.2 ve IP-2.3 tamamlandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-2.4-itemextractor-onay.md` mevcut ve `DURUM: TAMAMLANDI`.
- Zincir loglari mevcut ve tamamlandi:
  - `logs/IP-2.2-pdf-parser.md` -> `DURUM: TAMAMLANDI`.
  - `logs/IP-2.3-github-analiz.md` -> `DURUM: TAMAMLANDI`.
- Disk kontrolu:
  - `backend/app/api/pdf_import.py` mevcut; PDFParser akisi ve PDF structured cikarim yardimcilari hazir.
  - `backend/app/services/pdf_parser.py` mevcut; PDF metin cikarimi hazir.
  - `backend/app/services/github.py` mevcut; GitHub repo sinyali ve analiz akisi hazir.
  - `backend/app/services/item_extractor.py` mevcut; otomatik cikarimlar `verified_by_user=false` normalizasyonuyla hazir.
  - `backend/app/api/pool.py` mevcut; pending/approve/reject onay akisi hazir.
- Pre-flight kaniti olarak IP-2.4 logundaki hedef regresyon okundu: `11 passed, 1 warning`; tam backend paketi `30 passed, 1 warning`.

## 2. Yapilan isler (FAZ B)
- [x] LangGraph dependency eklendi: `backend/pyproject.toml`, `backend/uv.lock`.
- [x] Graph 1 eklendi: `backend/app/graphs/pool_graph.py`.
  - State girdisi: `user_id`, `pdf_bytes`, `include_github`, servisler ve GitHub client factory.
  - State ciktisi: `pending_item_ids`, `pending_count`, `parallel_steps`.
  - Dugum sirasi: `START -> PDFParser` ve `START -> GitHubAnalyzer` paralel; iki dugum `ItemExtractor` dugumunde birlesir; `END`.
- [x] GitHub analizi icin DB'ye yazmadan aday ureten ortak yardimci eklendi: `extract_repository_pool_candidates`.
- [x] Profil olusturma/guncelleme graph tetikleyicisine baglandi: `POST /profile`, `PUT /profile`, `PATCH /profile` response'u bekletmeden `BackgroundTasks` ile Graph 1'i kuyruga alir.
- [x] Tek tetikleme endpoint'i eklendi: `POST /profile/pool-refresh`; opsiyonel PDF dosyasi ve `include_github` ile Graph 1'i background'a alir.
- [x] GitHub sync scheduler Graph 1'i tetikleyecek sekilde guncellendi; boylece GitHubAnalyzer node'u merkezi graph uzerinden calisir.
- [x] Testler eklendi: `backend/tests/test_pool_graph.py`.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/graphs/__init__.py` | yeni | LangGraph modulu paketi |
| `backend/app/graphs/pool_graph.py` | yeni | Graph 1 state semasi, PDFParser/GitHubAnalyzer paralel dugumleri ve ItemExtractor dugumu |
| `backend/app/schemas/pool_graph.py` | yeni | Graph tetikleme response semasi |
| `backend/tests/test_pool_graph.py` | yeni | Graph paralellik, pending kayit ve profil tetikleyici testleri |
| `backend/app/api/profile.py` | degisti | Profil create/update ve `/profile/pool-refresh` background graph tetikleyicileri |
| `backend/app/api/github.py` | degisti | GitHub sync scheduler Graph 1'e baglandi |
| `backend/app/services/github.py` | degisti | DB'ye yazmadan GitHub aday item ureten helper |
| `backend/pyproject.toml` | degisti | `langgraph` dependency eklendi |
| `backend/uv.lock` | degisti | LangGraph ve alt bagimlilikleri lock edildi |
| `state/PROGRESS.md` | degisti | IP-2.5 satiri tamamlandi olarak guncellendi |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Tek tetikleme ile PDF + GitHub paralel islenip havuz onaya hazir geliyor.
- **Calistirilan komutlar:**
  ```text
  docker run --rm -v "${PWD}:/workspace" -w /workspace/backend ghcr.io/astral-sh/uv:python3.13-bookworm-slim uv lock
  docker compose -f infra/docker-compose.yml --profile app build backend
  docker compose -f infra/docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/test_pool_graph.py tests/test_pdf_import.py tests/test_github_integration.py tests/test_pool_approval.py -q -p no:cacheprovider --basetemp=/tmp/ip25-target-2"
  docker compose -f infra/docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/ -q -p no:cacheprovider --basetemp=/tmp/ip25-full"
  ```
- **Cikti ozeti:**
  - Lock: `Resolved 92 packages`; `langgraph v0.6.11` ve alt paketleri eklendi.
  - Hedef regresyon: `10 passed, 2 warnings in 30.09s`.
  - Tam backend test paketi: `32 passed, 2 warnings in 38.05s`.
- **Paralel calisma kaniti:** `test_pool_graph_processes_pdf_and_github_in_parallel_to_pending_items` Graph 1'i tek `ainvoke` ile PDF bytes + bagli GitHub connection uzerinden tetikledi; `parallel_steps == {"pdf_parser", "github_analyzer"}` ve iki dalin baslangic zaman farki `< 0.08s` olarak dogrulandi.
- **Pending item kaniti:** Ayni test PDF ve GitHub kaynakli 2 `pool_items` kaydinin ayni `user_id` ile, embedding dolu ve `verified_by_user=false` olustugunu dogruladi.
- **Background tetikleyici kaniti:** `test_profile_create_update_and_refresh_queue_pool_graph_background_job` profil create/patch ve `/profile/pool-refresh` isteklerinin Graph 1 scheduler'ini `BackgroundTasks` ile cagirdigini dogruladi.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-2.6 frontend havuz ekrani pending ogeler icin mevcut `GET /pool/pending`, `POST /pool/approve`, `POST /pool/reject` endpointlerini kullanabilir.
- Profil kaynakli otomatik refresh su an `BackgroundTasks` uzerinde calisir; ileride Celery/RQ eklenirse `get_pool_graph_scheduler` tek noktadan degistirilebilir.
- `/profile/pool-refresh` opsiyonel PDF ve GitHub sync'i tek tetiklemeyle kuyruga alir.

## 6. Acik sorunlar / bayraklar
- FastAPI TestClient kaynakli Starlette deprecation warning'i ve LangGraph `allowed_objects` pending deprecation warning'i test sonucunu etkilemiyor.
