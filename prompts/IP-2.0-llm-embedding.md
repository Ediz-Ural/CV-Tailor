# PROMPT — IP-2.0: LLM ve Embedding altyapısı (ortak servis katmanı)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-2.0-llm-embedding`
- **Bağımlılıklar:** IP-0.3
- **Referans:** PROJECT_CONTEXT §4 · IS_PAKETLERI İP-2.0

---

## FAZ A — ÖN KONTROL (önceki işi DOĞRULA)
- [ ] `logs/IP-0.3-backend-kurulum.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: `backend/app/core/config.py` (LLM_API_KEY/PROVIDER okuyor), FastAPI çalışıyor.
- [ ] (Varsa) `logs/IP-1.1-db-sema.md`'deki embedding boyutunu oku — tutarlı olmalı.
> ⛔ Eksikse: `logs/BLOCKED-IP-2.0.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] LLM çağrı sarmalayıcı (`backend/app/services/llm.py`): provider-agnostik arayüz
      (OpenAI/Anthropic seçilebilir), **structured output / JSON şema** desteği (pydantic ile parse).
- [ ] Embedding servisi (`backend/app/services/embeddings.py`): çok dilli model (multilingual-e5 veya BGE-m3),
      `embed(text) -> vector`. Boyut, IP-1.1'deki `vector` kolon boyutuyla **aynı** olmalı.
- [ ] Dil tespiti yardımcı fonksiyonu (`detect_language(text) -> tr|en|mixed`).
- [ ] Retry + timeout + hata yönetimi (LLM ~10–30sn olabilir; timeout ve yeniden deneme).
- [ ] Yapılandırma `config`'ten okunur (model adı, provider, key).

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Bir metin verince embedding vektörü ve JSON structured çıktı alınabiliyor.
- [ ] Test: `embed("merhaba dünya / hello world")` → doğru boyutta vektör.
- [ ] Test: LLM structured çağrısı bir pydantic modele parse oluyor (mock veya gerçek key ile).
- [ ] Test: `detect_language` TR/EN/karma örneklerinde doğru sonuç.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-2.0-llm-embedding.md` yaz (seçilen embedding modeli + boyut, LLM provider, timeout/retry politikası).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (embedding boyutu — IP-1.1 ile eşleşme durumu). Temiz çık.
