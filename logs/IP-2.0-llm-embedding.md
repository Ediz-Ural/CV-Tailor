# Log - IP-2.0: LLM ve Embedding altyapisi

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-14 14:17
- **Is paketi prompt'u:** `prompts/IP-2.0-llm-embedding.md`
- **Bagimliliklar (dogrulandi mi?):** IP-0.3 tamamlandi; log ve FastAPI health kaniti gecti. IP-1.1 embedding boyutu disk ve log uzerinden `vector(1024)` olarak dogrulandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-0.3-backend-kurulum.md` mevcut ve `DURUM: TAMAMLANDI`.
- `backend/app/core/config.py` mevcut; `LLM_API_KEY`, `LLM_PROVIDER` ve model ayarlarini okuyor.
- `logs/IP-1.1-db-sema.md` mevcut; `pool_items.embedding` boyutu `vector(1024)`.
- `backend/app/models/pool_item.py`, `Vector(EMBEDDING_DIMENSION)` kullaniyor ve sabit boyut `1024`.
- Guncel backend imaji baslatildiktan sonra `GET /health` cagrisi `HTTP 200` ve `{"status":"ok"}` dondurdu.

## 2. Yapilan isler (FAZ B)
- [x] Provider-agnostik LLM servisi eklendi: OpenAI ve Anthropic provider secimi, Pydantic JSON schema structured output parse destegi.
- [x] Cok dilli embedding servisi eklendi: FastEmbed/ONNX ile `intfloat/multilingual-e5-large`, `embed(text) -> list[float]`.
- [x] Embedding boyutu IP-1.1 ile ayni sabit kaynaga baglandi: `EMBEDDING_DIMENSION = 1024`; ortam degiskeniyle farkli boyuta cekilemez.
- [x] `detect_language(text) -> tr|en|mixed` yardimcisi eklendi.
- [x] LLM timeout, yeniden deneme ve hata siniflari eklendi.
- [x] LLM, embedding ve cache ayarlari config, `.env.example` ve Docker Compose'a baglandi.
- [x] Model cache'i kalici `cv-tailor-fastembed-cache` Docker volume'una baglandi.
- [x] Birim testleri embedding boyutu/hata, TR-EN-karma dil tespiti, OpenAI/Anthropic structured parse ve transient retry davranisini kapsiyor.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/services/__init__.py` | yeni | Ortak servis paketi |
| `backend/app/services/llm.py` | yeni | OpenAI/Anthropic structured LLM sarmalayicisi |
| `backend/app/services/embeddings.py` | yeni | Cok dilli 1024 boyutlu embedding ve dil tespiti |
| `backend/tests/test_ai_services.py` | yeni | IP-2.0 birim testleri |
| `backend/app/core/config.py` | degisti | Provider, model, timeout, retry ve embedding model ayarlari |
| `backend/pyproject.toml` | degisti | `httpx`, `fastembed`, `pytest-asyncio` bagimliliklari |
| `backend/uv.lock` | degisti | 74 paketlik guncel kilit cozumu |
| `backend/.dockerignore` | yeni | Yerel venv/cache dosyalarini build context disinda tutar |
| `.env.example` | degisti | LLM/embedding ayar ornekleri |
| `infra/docker-compose.yml` | degisti | LLM/embedding env aktarimi ve kalici model cache volume'u |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Bir metin verince embedding vektoru ve Pydantic modele parse edilen JSON structured cikti alinabiliyor.
- **Calistirilan komutlar:**
  ```text
  docker compose -f infra/docker-compose.yml --profile app build backend
  docker compose -f infra/docker-compose.yml --profile app run --rm backend sh -c "uv sync --frozen && uv run --no-sync pytest -q -p no:cacheprovider --basetemp=/tmp/ip20-final-2"
  docker compose -f infra/docker-compose.yml --profile app run --rm -e FASTEMBED_CACHE_PATH=/models -v cv-tailor-fastembed-cache:/models backend uv run --no-sync python -c "... embed('merhaba dunya / hello world') ..."
  Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
  ```
- **Cikti ozeti:** Pytest `19 passed, 1 warning`. Gercek `intfloat/multilingual-e5-large` modeli ornek metin icin `EMBEDDING_DIMENSION=1024` ve ilk deger `0.07976549` uretti. OpenAI ve Anthropic structured ciktilari mock HTTP yanitlariyla Pydantic `Summary` modeline parse edildi. Retry testi ilk `429` yanitindan sonra ikinci denemede basarili oldu. Health `HTTP_STATUS=200`, `{"status":"ok"}`.
- **Embedding boyut eslesmesi:** FastEmbed model metadata `1024`; servis ciktisi `1024`; IP-1.1 PostgreSQL kolonu `vector(1024)`. Tam eslesme var.
- **Sonuc:** DoD karsilandi.

## 5. Secimler ve politikalar
- **Embedding modeli:** `intfloat/multilingual-e5-large` (FastEmbed ONNX), cok dilli, 1024 boyut.
- **LLM provider:** Varsayilan `openai`, model `gpt-4o-mini`; `anthropic` ayni servis arayuzunden secilebilir.
- **Timeout:** Varsayilan 30 saniye.
- **Retry:** Varsayilan 2 yeniden deneme; timeout/network ve HTTP `408, 409, 429, 500, 502, 503, 504` icin artan bekleme (`1s`, `2s`, en fazla `4s`).
- **Hata yonetimi:** Yapilandirma, provider ve structured-output hatalari ayri servis hata siniflariyla sarilir.

## 6. Sonraki paket icin notlar
- IP-2.1 manuel havuz kaydinda `EmbeddingService.embed()` ve `detect_language()` kullanabilir.
- Ilk model indirmesi buyuktur; model `cv-tailor-fastembed-cache` volume'unda kalici olarak cache'lendi.
- LLM structured testleri gercek API harcamasi yapmayan mock provider yanitlariyla dogrulandi; `.env` anahtari Git tarafindan dislanir.

## 7. Acik sorunlar / bayraklar
- FastEmbed 0.8.0, bu model icin mean pooling davranis degisikligi uyarisi veriyor; uretilen boyut ve servis sozlesmesi etkilenmiyor.
- Mevcut FastAPI TestClient kaynakli Starlette deprecation warning'i devam ediyor; test sonucunu etkilemiyor.
