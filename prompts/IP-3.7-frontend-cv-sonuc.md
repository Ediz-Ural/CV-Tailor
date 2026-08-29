# PROMPT — IP-3.7: Frontend — İlan girişi + CV sonucu (vitrin)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-3.7-frontend-cv-sonuc`
- **Bağımlılıklar:** IP-3.6, IP-1.4
- **Referans:** PROJECT_CONTEXT §9 · IS_PAKETLERI İP-3.7

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-3.6-graph2-orkestrasyon.md` ve `logs/IP-1.4-frontend-auth.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: Graph 2 tetikleyici + progress endpoint'leri; frontend auth + layout.
- [ ] Backend uçtan uca CV üretimi canlı çalışıyor.
> ⛔ Eksikse: `logs/BLOCKED-IP-3.7.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] İlan giriş ekranı: metin/URL toggle.
- [ ] Pipeline **ilerleme göstergesi** (adım adım, monospace log stili — §9).
- [ ] **Vitrin (sonuç) ekranı** (§9): büyük tipografi ile ATS skoru, before/after diff,
      seçilen havuz öğeleri, **PDF önizleme + indir**.
- [ ] Güçlü kontrast / büyük tipografi (vitrin anı); dark-mode-first.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Kullanıcı ilan verip sonucu görsel olarak güçlü bir ekranda görüp PDF indirebiliyor.
- [ ] Komut: `npm run build` hatasız.
- [ ] Akış kanıtı: ilan gir → progress → sonuç ekranı (skor + before/after + PDF indir) çalışıyor.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-3.7-frontend-cv-sonuc.md` yaz (ekran/komponent listesi, kullanılan endpoint'ler).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (çekirdek ürün akışı tamam). Temiz çık.
