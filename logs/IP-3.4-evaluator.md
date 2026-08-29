# Log - IP-3.4: Evaluator (ATS skoru)

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-18 19:33
- **Is paketi prompt'u:** `prompts/IP-3.4-evaluator.md`
- **Bagimliliklar (dogrulandi mi?):** IP-3.3 tamamlandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-3.3-cvtailor.md` mevcut ve `DURUM: TAMAMLANDI`.
- `backend/app/graphs/nodes/cvtailor.py` icinde CVTailor `tailored_cv` ve `output_language` uretiyor.
- `backend/app/models/job.py` icinde `jobs.parsed_requirements_json` mevcut.
- `backend/app/models/generated_cv.py` icinde `generated_cvs.ats_score` mevcut.
- `backend/tests/test_cvtailor.py` CVTailor cikti dili, teknik terim koruma ve anti-fabrikasyon davranisini test ediyor.

## 2. Yapilan isler (FAZ B)
- [x] Evaluator node eklendi: `backend/app/graphs/nodes/evaluator.py`.
- [x] ATS uyum skoru hesaplandi: ilan gereksinimleri `required_skills`, `preferred_skills`, `key_terms` ile tailor edilmis CV metni karsilastiriliyor.
- [x] Turkce exact string match'e bagli olmayan eslesme eklendi: Unicode TR karakter normalizasyonu + hafif kok/stem token eslesmesi kullaniliyor.
- [x] Eksik keyword listesi `missing_keywords` olarak uretiliyor.
- [x] Before/after diff uretiliyor: secili orijinal `pool_items.raw_content` ile `TailoredCVItem.content` kaynak ID uzerinden eslestirilip unified diff'e cevriliyor.
- [x] Skor `ats_score` alaninda donduruluyor; `generated_cvs.ats_score` yazimina hazir sayisal deger uretiliyor.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/graphs/nodes/evaluator.py` | yeni | ATS degerlendirme modeli, skor hesaplama, eksik keyword ve before/after diff |
| `backend/app/graphs/nodes/__init__.py` | degisti | Evaluator export'lari |
| `backend/tests/test_evaluator.py` | yeni | Yuksek skor, eksik keyword ve Turkce kok varyasyonu testleri |
| `logs/IP-3.4-evaluator.md` | yeni | Bu paket kanit kaydi |
| `state/PROGRESS.md` | degisti | IP-3.4 satiri tamamlandi olarak guncellendi |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Uretilen CV icin ATS skoru, eksik keyword'ler ve before/after ciktisi var.
- **Skor formulu:** Kategori agirliklari `required_skills=0.70`, `preferred_skills=0.20`, `key_terms=0.10`. Her keyword eslesmesi kendi kategori agirligini tasir; skor `matched_weight / total_weight * 100`, iki ondaliga yuvarlanir.
- **Eslesme yontemi:** CV metni ve keyword'ler casefold + Turkce karakter transliterasyonu ile normalize edilir. Token'lar hafif Turkce suffix temizleme ile koklestirilir; keyword token koklerinin tamami CV token koklerinde varsa eslesmis sayilir. Bu nedenle `gelistiren` ve `gelistirici` exact string olmadan eslesir.
- **Diff formati:** Her tailor edilmis item icin `source_pool_item_id` ile orijinal `pool_items.raw_content` bulunur; `difflib.unified_diff` ile `--- pool_item` / `+++ tailored_cv` baslikli unified diff uretilir.
- **Calistirilan komutlar:**
  ```text
  python -m pytest backend/tests/test_evaluator.py backend/tests/test_cvtailor.py backend/tests/test_selector.py -q -p no:cacheprovider
  docker compose -f infra\docker-compose.yml --profile app build backend
  docker compose -f infra\docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/test_evaluator.py tests/test_cvtailor.py tests/test_selector.py -q -p no:cacheprovider"
  docker compose -f infra\docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest -q -p no:cacheprovider --basetemp=/tmp/ip34-full"
  ```
- **Cikti ozeti:**
  - Yerel `python -m pytest ...` calismadi: host Python ortaminda `sqlalchemy` kurulu degil.
  - Docker hedef testleri: `9 passed`.
  - Docker tum backend testleri: `45 passed, 2 warnings`.
- **Test kanitlari:**
  - Iyi eslesen CV `ats_score == 100.0` uretiyor ve before/after diff var.
  - Eksik `Kubernetes` ve `React` becerileri `missing_keywords` listesinde.
  - Turkce `gelistirici` gereksinimi, CV'deki `gelistiren` varyasyonuyla exact string olmadan eslesiyor.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-3.5/3.6 `evaluator_node` ciktisindaki `ats_score` degerini `generated_cvs.ats_score` alanina yazabilir.
- `ats_evaluation` modeli `keyword_matches`, `missing_keywords` ve `before_after_diff` alanlarini birlikte tasir; frontend vitrin ekrani icin hazir veri yapisi saglar.

## 6. Acik sorunlar / bayraklar
- Eslesme deterministik hafif koklestirme ile yapiliyor; gercek embedding/LLM tabanli semantik eslesme eklenmedi. IP-3.2 ile ayni MVP yaklasimina uygun olarak exact string'e bagli kalinmadi.
