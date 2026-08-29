# PROMPT — IP-2.2: PDF CV parse (PDFParser node)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-2.2-pdf-parser`
- **Bağımlılıklar:** IP-2.0, IP-2.1
- **Referans:** PROJECT_CONTEXT §7 (Graph 1), §8 etik · IS_PAKETLERI İP-2.2

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-2.0-llm-embedding.md` ve `logs/IP-2.1-manuel-havuz.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: `pool_items` CRUD + embedding yazımı çalışıyor; LLM structured çağrı hazır.
> ⛔ Eksikse: `logs/BLOCKED-IP-2.2.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] PDF yükleme endpoint'i (`POST /pool/import/pdf`): dosya tipi + boyut limiti kontrolü.
- [ ] PDF metin çıkarımı (`pypdf` veya `pdfplumber`).
- [ ] LLM ile structured çıkarım: deneyim / eğitim / skill → JSON şema.
- [ ] Çıkanları `pool_items` formatına normalize: `source="pdf"`, dil tespiti + embedding,
      **`verified_by_user=false`** (kullanıcı onayı IP-2.4'te).
- [ ] `user_id` izolasyonu.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Bir PDF CV yüklenince havuza aday öğeler (onaysız) düşüyor.
- [ ] Test: örnek PDF yükle → `pool_items`'ta `source=pdf`, `verified_by_user=false` kayıtlar oluşuyor, embedding dolu.
- [ ] Test: bozuk/boş PDF zarif şekilde hata veriyor (çökmüyor).
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-2.2-pdf-parser.md` yaz (kullanılan PDF kütüphanesi, çıkarım şeması, onaysız kayıt kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (onay akışı IP-2.4'te). Temiz çık.
