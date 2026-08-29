# PROMPT — IP-3.4: Evaluator (ATS skoru)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-3.4-evaluator`
- **Bağımlılıklar:** IP-3.3
- **Referans:** PROJECT_CONTEXT §4 (Türkçe ATS), §7 (Graph 2), §12 · IS_PAKETLERI İP-3.4

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-3.3-cvtailor.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: CVTailor tailor edilmiş içerik + `output_language` üretiyor; `jobs.parsed_requirements_json` var.
> ⛔ Eksikse: `logs/BLOCKED-IP-3.4.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] Evaluator node: **ATS uyum skoru** hesapla (ilan gereksinimleri ↔ tailor edilmiş CV).
- [ ] Türkçe'de **exact string match YOK** → lemmatization/semantic keyword eşleşmesi (IP-3.2 ile aynı yaklaşım).
- [ ] **Eksik keyword listesi** üret.
- [ ] **Before/after diff** üret (orijinal havuz içeriği vs tailor edilmiş).
- [ ] Skoru `generated_cvs.ats_score` için hazırla.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Üretilen CV için ATS skoru, eksik keyword'ler ve before/after çıktısı var.
- [ ] Test: ilanla iyi eşleşen CV yüksek skor; eksik beceriler "missing keywords"te.
- [ ] Test: Türkçe kök varyasyonu ("geliştiren" vs "geliştirici") eşleşmiş sayılıyor (exact match değil).
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-3.4-evaluator.md` yaz (skor formülü, eşleşme yöntemi, diff formatı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver. Temiz çık.
