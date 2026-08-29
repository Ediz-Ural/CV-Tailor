# Log - IP-3.3: CVTailor

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-18 19:26
- **Is paketi prompt'u:** `prompts/IP-3.3-cvtailor.md`
- **Bagimliliklar (dogrulandi mi?):** IP-3.2 tamamlandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-3.2-selector.md` mevcut ve `DURUM: TAMAMLANDI`.
- `backend/app/graphs/nodes/selector.py` icinde selector ciktisi `selected_pool_items` olarak `pool_item_id` + `score` donduruyor.
- `backend/app/models/job.py` icinde `jobs.detected_language` mevcut.
- `backend/tests/test_selector.py` selector secim ve skor davranisini test ediyor.

## 2. Yapilan isler (FAZ B)
- [x] CVTailor node eklendi: `backend/app/graphs/nodes/cvtailor.py`.
- [x] Secilen pool item'lar `user_id`, `pool_item_id` sirasi ve `verified_by_user=true` filtresiyle yukleniyor.
- [x] `output_language` belirlendi: `jobs.detected_language` `tr` veya `en` ise aynen kullaniliyor; `mixed` ise mevcut `dominant_job_language` yardimcisiyle baskin dil `tr`/`en` olarak seciliyor.
- [x] LLM prompt'u, CV icerigini ilanin dilinde uretmeyi ve teknik terimleri kaynakta gectigi gibi korumayi acikca zorluyor.
- [x] Uydurma bilgi onleme stratejisi eklendi:
  - LLM sadece secili verified kaynak ogelerinden uretebilir.
  - Her cikti ogesi `source_pool_item_id` tasir.
  - Cikti ID'leri secili kaynak ID'leriyle sinirlanir.
  - Oge teknolojileri kaynak ogedeki `technologies` disina cikamaz.
  - Ilan gereksinimlerinde gecen ama kaynaklarda bulunmayan terim ciktiya girerse LLM ciktisi reddedilir ve kaynak-temelli fallback kullanilir.
- [x] Cikti `TailoredCVContent`: `summary`, `experience`, `projects`, `skills`, `output_language`.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/graphs/nodes/cvtailor.py` | yeni | CVTailor node, output language secimi, LLM prompt'u, anti-fabrikasyon validasyonu |
| `backend/app/graphs/nodes/__init__.py` | degisti | Selector ve CVTailor node export'lari |
| `backend/tests/test_cvtailor.py` | yeni | EN/TR dil uyarlama, teknik terim koruma ve anti-fabrikasyon testleri |
| `logs/IP-3.3-cvtailor.md` | yeni | Bu paket kanit kaydi |
| `state/PROGRESS.md` | degisti | IP-3.3 satiri tamamlandi olarak guncellendi |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Secilen ogelerden ilana ozel, dogru dilde, uydurmasiz CV icerigi uretiliyor.
- **Calistirilan komutlar:**
  ```text
  python -m pytest backend/tests/test_cvtailor.py backend/tests/test_selector.py -q -p no:cacheprovider
  docker compose -f infra\docker-compose.yml --profile app build backend
  docker compose -f infra\docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/test_cvtailor.py tests/test_selector.py -q -p no:cacheprovider"
  docker compose -f infra\docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest -q -p no:cacheprovider --basetemp=/tmp/ip33-full"
  ```
- **Cikti ozeti:**
  - Yerel `python -m pytest ...` calismadi: host Python ortaminda `sqlalchemy` kurulu degil.
  - Docker hedef testleri: `6 passed`.
  - Docker tum backend testleri: `42 passed, 2 warnings`.
- **Dil uyarlama kaniti:** `tests/test_cvtailor.py` EN ilanda `output_language=en`, TR ilanda `output_language=tr` bekliyor.
- **Teknik terim kaniti:** Testlerde `FastAPI` ve `machine learning` cikti metninde cevrilmeden korunuyor.
- **Anti-fabrikasyon kaniti:** Kaynakta olmayan `Kubernetes` becerisini LLM ciktisi eklediginde CVTailor bunu reddedip kaynak-temelli fallback uretiyor; final cikti `Kubernetes` icermiyor.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-3.4 Evaluator `tailored_cv` alanindaki `TailoredCVContent` yapisini tuketebilir: `summary`, `experience`, `projects`, `skills`, `output_language`.
- IP-3.5 TypstRenderer ayni yapidan Typst kaynagi uretebilir; her item `source_pool_item_id` tasidigi icin before/after ve kaynak izleme korunur.
- CVTailor henuz Graph 2 zincirine baglanmadi; IP-3.6 orkestrasyon paketinde Selector -> CVTailor -> Evaluator akisi kurulabilir.

## 6. Acik sorunlar / bayraklar
- Testlerde gercek LLM yerine deterministik fake LLM kullanildi.
- Uydurma onleme validasyonu kaynakta olmayan ilan terimlerini ve teknoloji listesi disina cikmayi yakalar; serbest metindeki tum olasi factual iddialar icin tam formal dogrulama degildir, bu nedenle prompt ve kaynak-ID izleme birlikte kullanildi.
