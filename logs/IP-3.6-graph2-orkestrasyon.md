# Log - IP-3.6: Graph 2 orkestrasyonu

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-21 00:00
- **Is paketi prompt'u:** `prompts/IP-3.6-graph2-orkestrasyon.md`
- **Bagimliliklar (dogrulandi mi?):** IP-3.1 ✅ / IP-3.2 ✅ / IP-3.3 ✅ / IP-3.4 ✅ / IP-3.5 ✅

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-3.5-typst-render.md` mevcut ve `DURUM: TAMAMLANDI`.
- Zincir loglari mevcut ve `DURUM: TAMAMLANDI`: `logs/IP-3.1-jobparser.md`, `logs/IP-3.2-selector.md`, `logs/IP-3.3-cvtailor.md`, `logs/IP-3.4-evaluator.md`.
- Diskte dogrulanan node/servis dosyalari:
  - `backend/app/services/job_parser.py` -> JobParser
  - `backend/app/graphs/nodes/selector.py` -> Selector
  - `backend/app/graphs/nodes/cvtailor.py` -> CVTailor
  - `backend/app/graphs/nodes/evaluator.py` -> Evaluator
  - `backend/app/render/typst.py` ve `backend/app/services/render_queue.py` -> TypstRenderer + render kuyrugu
- Tekil node/render testleri IP-3.6 kapsaminda tekrar kosuldu; hedef set gecis kaniti asagida.

## 2. Yapilan isler (FAZ B)
- [x] LangGraph zinciri eklendi: `JobParser -> Selector -> CVTailor -> Evaluator -> TypstRenderer`.
- [x] Graph state semasi eklendi: girdi `user_id`, `user_email`, ilan metni/URL; ara alanlar `job_id`, `selected_pool_items`, `tailored_cv`, `ats_evaluation`, `ats_score`; cikti `generated_cv_id`.
- [x] Ilan girisi Graph 2'yi tetikliyor: `POST /cv-generation`.
- [x] Progress/status mekanizmasi eklendi: `pipeline_id`, adim durumlari ve sonuc id'leri `GET /cv-generation/{pipeline_id}` ile sorgulaniyor.
- [x] Render adimi IP-3.5 ile uyumlu: `GeneratedCV` kaydi olusturuluyor ve `render_generated_cv_task(generated_cv_id)` siniri kullaniliyor.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/graphs/cv_graph.py` | yeni | Graph 2 LangGraph zinciri, state semasi, JobParser ve TypstRenderer node wrapper'lari |
| `backend/app/services/cv_progress.py` | yeni | Process ici pipeline progress store ve step durum modeli |
| `backend/app/api/cv_generation.py` | yeni | `POST /cv-generation` tetikleyici ve `GET /cv-generation/{pipeline_id}` status endpoint'i |
| `backend/app/schemas/cv_generation.py` | yeni | Graph 2 start/status response semalari |
| `backend/app/main.py` | degisti | CV generation router eklendi |
| `backend/tests/test_cv_graph.py` | yeni | Uctan uca Graph 2 entegrasyon ve tenant scoped progress testleri |
| `logs/IP-3.6-graph2-orkestrasyon.md` | yeni | Bu paket kanit kaydi |
| `state/PROGRESS.md` | degisti | IP-3.6 durumu TAMAMLANDI |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Ilan ver -> uctan uca optimize PDF CV + ATS skoru otomatik uretiliyor.
- **Calistirilan komutlar:**
  ```
  python -m pytest backend/tests/test_cv_graph.py backend/tests/test_typst_render.py backend/tests/test_selector.py backend/tests/test_cvtailor.py backend/tests/test_evaluator.py -q -p no:cacheprovider
  python -m pytest backend/tests/ -q -p no:cacheprovider
  python -m pytest backend/tests/test_cv_graph.py -q -p no:cacheprovider
  ```
- **Cikti ozeti:**
  - Hedef Graph 2 + onceki node/render seti: `14 passed, 2 warnings`.
  - Tum backend testleri: `50 passed, 2 warnings`.
  - Son Graph 2 tekrar kosumu: `2 passed, 2 warnings`.
- **Uctan uca kanit:** `backend/tests/test_cv_graph.py::test_cv_generation_graph_creates_job_generated_cv_pdf_and_ats_score`
  - Dolu ve verified havuza sahip kullanici icin `POST /cv-generation` calisti.
  - Status endpoint'i tum adimlari `completed` raporladi.
  - `generated_cvs` kaydi olustu; `selected_pool_item_ids`, `ats_score`, `typst_source`, `pdf_path` dogrulandi.
  - PDF dosyasi fake render worker ile `%PDF` icerigiyle yazildi.
- **Progress kaniti:** `backend/tests/test_cv_graph.py::test_cv_generation_progress_is_tenant_scoped`
  - Baska kullanici ayni `pipeline_id` icin `404` aldi.
- **Sonuc:** DoD karsilandi ✅

## 5. Sonraki paket icin notlar
- IP-3.7 frontend `POST /cv-generation` ile pipeline baslatabilir; yanittaki `status_url` veya `pipeline_id` ile `GET /cv-generation/{pipeline_id}` poll edebilir.
- Status response alanlari: `status`, `current_step`, `steps[]`, `job_id`, `generated_cv_id`, `error`.
- PDF indirme mevcut endpoint ile yapilir: `GET /generated-cvs/{generated_cv_id}/download`.
- IP-5.2 icin Graph 2 testleri `backend/tests/test_cv_graph.py` altinda hazir.

## 6. Acik sorunlar / bayraklar
- Progress store process ici bellekte tutuluyor; coklu worker/kalici job takibi IP-5.3 gozlemlenebilirlik/dagitim kapsaminda kalici tablo veya harici kuyrukla guclendirilmeli.
