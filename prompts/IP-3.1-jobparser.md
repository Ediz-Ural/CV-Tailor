# PROMPT — IP-3.1: İlan girişi + JobParser

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-3.1-jobparser`
- **Bağımlılıklar:** IP-2.0, IP-1.1
- **Referans:** PROJECT_CONTEXT §2, §3, §7 (Graph 2) · IS_PAKETLERI İP-3.1

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-2.0-llm-embedding.md` ve `logs/IP-1.1-db-sema.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: `jobs` tablosu, LLM structured çağrı, `detect_language`.
> ⛔ Eksikse: `logs/BLOCKED-IP-3.1.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] İlan girişi endpoint'i: **metin yapıştır** VEYA **URL**.
      URL verilince **tek bir sayfa** fetch edilir (kullanıcının açık isteğiyle; scraping/toplu tarama YOK).
- [ ] JobParser: ilan dilini tespit (`detected_language` = tr|en|mixed; karma'da baskın dil) →
      CV çıktı dilini bu belirleyecek.
- [ ] Structured gereksinim çıkarımı (JSON şema): zorunlu/tercihen skill, deneyim yılı, anahtar terimler.
      TR + EN + karma ilanları işler; teknik terimler korunur.
- [ ] `jobs` tablosuna kaydet (`source_url`, `raw_text`, `detected_language`, `parsed_requirements_json`), `user_id` izole.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** İlan yapıştır/URL ver → dili tespit edilmiş, structured gereksinimler JSON olarak elde.
- [ ] Test: TR ilan → `detected_language=tr`; EN ilan → `en`; karma → baskın dil.
- [ ] Test: URL girişi tek sayfa fetch ediyor; çıkarılan JSON şemaya uyuyor.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-3.1-jobparser.md` yaz (gereksinim JSON şeması, dil tespiti kanıtı, URL fetch sınırı notu).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (IP-3.2 Selector bu çıktıyı kullanacak). Temiz çık.
