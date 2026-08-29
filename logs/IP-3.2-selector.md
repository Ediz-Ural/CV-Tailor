# Log - IP-3.2: Selector (semantik + LLM secim)

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-18 19:20
- **Is paketi prompt'u:** `prompts/IP-3.2-selector.md`
- **Bagimliliklar (dogrulandi mi?):** IP-3.1 tamamlandi; IP-2.1 tamamlandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-3.1-jobparser.md` mevcut ve `DURUM: TAMAMLANDI`.
- `logs/IP-2.1-manuel-havuz.md` mevcut ve `DURUM: TAMAMLANDI`.
- `backend/app/models/job.py` uzerinden `jobs.parsed_requirements_json` alaninin JSONB olarak var oldugu dogrulandi.
- `backend/tests/test_jobs.py` uzerinden `parsed_requirements_json` uretiminin test edildigi dogrulandi.
- `backend/app/models/pool_item.py` uzerinden `pool_items.embedding` ve `verified_by_user` alanlari dogrulandi.
- `backend/tests/test_pool_items.py` uzerinden manuel pool item kaydinda embedding yazildigi ve `verified_by_user=true` oldugu dogrulandi.

## 2. Yapilan isler (FAZ B)
- [x] Selector node eklendi: `backend/app/graphs/nodes/selector.py`.
- [x] Ilan gereksinimlerinden semantic sorgu metni olusturuldu: `required_skills`, `preferred_skills`, `key_terms`, `years_experience`; yoksa `raw_text` fallback.
- [x] pgvector semantic arama eklendi: `PoolItem.embedding.cosine_distance(query_embedding)` ile cosine distance, skor `1 - distance`.
- [x] Arama sadece ayni `user_id`, `verified_by_user=true`, `embedding is not null` pool item satirlarinda calisir.
- [x] LLM rerank eklendi: semantic adaylar `SelectorRanking` JSON semasiyla secilir/siralanir; aday listesi disindaki ID'ler yok sayilir.
- [x] Dil farki filtre olarak kullanilmadi; adaylar TR/EN/mixed fark etmeksizin semantic skora gore gelir.
- [x] Turkce icin exact string match kullanilmadi. Secim semantic embedding ile yapilir; ek olarak log/test kaniti icin hafif Turkce kok yardimcisi `turkish_light_lemmas` eklendi.
- [x] Cikti `selected_pool_items`: `pool_item_id` ve `score` listesi.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/graphs/nodes/__init__.py` | yeni | Graph node paketi |
| `backend/app/graphs/nodes/selector.py` | yeni | Semantic aday arama, LLM rerank, secim skorlari |
| `backend/tests/test_selector.py` | yeni | verified filtresi, tenant izolasyonu, cross-language semantic secim ve Turkce kok varyasyonu testleri |
| `logs/IP-3.2-selector.md` | yeni | Bu paket kanit kaydi |
| `state/PROGRESS.md` | degisti | IP-3.2 satiri tamamlandi olarak guncellendi |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Bir ilana karsi havuzdan en alakali ogeler (id listesi + skor) donuyor.
- **Calistirilan komutlar:**
  ```text
  docker compose -f infra\docker-compose.yml --profile app build backend
  docker compose -f infra\docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/test_selector.py -q -p no:cacheprovider"
  docker compose -f infra\docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest -q -p no:cacheprovider --basetemp=/tmp/ip32-full"
  ```
- **Cikti ozeti:** Hedef testler `3 passed`. Tum backend testleri `39 passed, 2 warnings`.
- **Verified filtresi kaniti:** `tests/test_selector.py` icinde ayni semantic embedding'e sahip unverified item secilmedi; sadece `verified_by_user=true` adaylar semantic candidate listesine girdi.
- **TR/EN karma kaniti:** EN ilan gereksinimi `backend gelistirici`, TR pool item icerigi `FastAPI ... gelistirme ...` olmasina ragmen secildi; item dil farki nedeniyle elenmedi.
- **Turkce exact match yok kaniti:** Testte secilen TR pool item `gelistirici` exact string'ini icermiyor; secim embedding semantic sorgusuyla yapildi. Hafif kok yardimcisi `gelistirici` ve `gelistirme` icin ortak kok urettigini ayrica dogruladi.
- **Benzerlik metrigi:** pgvector cosine distance (`<=>` karsiligi SQLAlchemy `cosine_distance`) kullanildi; skor `1 - distance` araligina clamp edildi.
- **LLM secim mantigi:** LLM semantic aday listesini `SelectorRanking` semasiyla rerank eder; final skor LLM skoru ve semantic skor ortalamasidir. LLM hatasinda semantic siralama fallback olarak kullanilir.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-3.3 CVTailor, selector cikisini `selected_pool_items` listesinden okuyabilir: her ogede `pool_item_id` ve `score` var.
- Selector node henuz tam Graph 2 zincirine baglanmadi; IP-3.6 orkestrasyon paketinde JobParser -> Selector -> CVTailor akisi kurulabilir.
- LLM rerank prompt'u aday iceriklerini kisaltarak (`raw_content[:1200]`) gonderir; uzun pool item'larda token kontrolu icin bu sinir kullaniliyor.

## 6. Acik sorunlar / bayraklar
- Testlerde gercek LLM ve gercek embedding modeli yerine deterministik fake servisler kullanildi; pgvector cosine sorgusu gercek PostgreSQL/pgvector ortaminda calisti.
