# PROMPT — IP-3.3: CVTailor

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-3.3-cvtailor`
- **Bağımlılıklar:** IP-3.2
- **Referans:** PROJECT_CONTEXT §2, §7 (Graph 2), §12 · IS_PAKETLERI İP-3.3

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-3.2-selector.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: Selector seçilen `pool_item_id` + skor döndürüyor; `jobs.detected_language` mevcut.
> ⛔ Eksikse: `logs/BLOCKED-IP-3.3.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] CVTailor node: seçilen öğeleri **ilana göre yeniden ifade** et.
- [ ] **İlanın diline uyarla:** EN ilan → EN CV, TR ilan → TR CV (karma'da baskın dil). `output_language` belirle.
- [ ] Teknik terimler **korunur** (çevrilmez): "machine learning", "FastAPI" vb.
- [ ] **UYDURMA BİLGİ YOK** — sadece var olanı öne çıkar / yeniden ifade et. (Bu en kritik kural; prompt'ta açıkça zorla.)
- [ ] Çıktı: tailor edilmiş yapılandırılmış CV içeriği + `output_language`.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Seçilen öğelerden ilana özel, doğru dilde, uydurmasız CV içeriği üretiliyor.
- [ ] Test: EN ilan → EN içerik; TR ilan → TR içerik; teknik terimler korunmuş.
- [ ] Test (anti-fabrikasyon): kaynak öğelerde olmayan beceri/deneyim çıktıya **eklenmiyor** (örnek girdiyle kontrol).
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-3.3-cvtailor.md` yaz (uydurma önleme stratejisi, dil uyarlama kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (IP-3.4 Evaluator ve IP-3.5 TypstRenderer bu çıktıyı tüketecek). Temiz çık.
