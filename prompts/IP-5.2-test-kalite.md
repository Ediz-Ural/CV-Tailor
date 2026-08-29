# PROMPT — IP-5.2: Test ve kalite

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-5.2-test-kalite`
- **Bağımlılıklar:** IP-3.6
- **Referans:** PROJECT_CONTEXT §6, §7 · IS_PAKETLERI İP-5.2

---

## FAZ A — ÖN KONTROL (önceki işi DOĞRULA)
- [ ] `logs/IP-3.6-graph2-orkestrasyon.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: uçtan uca CV üretim akışı çalışıyor (Graph 2).
- [ ] Çekirdek backend modülleri (auth, havuz, pipeline node'ları) mevcut.
> ⛔ Eksikse: `logs/BLOCKED-IP-5.2.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] Backend birim/entegrasyon testleri (pytest): auth, parser'lar (PDF/Job), pipeline node'ları (Selector/CVTailor/Evaluator).
- [ ] **Tenant izolasyon testleri:** bir kullanıcı diğerinin verisine erişemez (tüm korumalı kaynaklar).
- [ ] Pipeline için **golden testler:** örnek ilan → beklenen seçim/skor aralığı (deterministik kısımlar).
- [ ] Anti-fabrikasyon testi: CVTailor kaynak dışı bilgi eklemiyor.
- [ ] CI yapılandırması (GitHub Actions vb.) ile testlerin koşması.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** CI'da testler geçiyor.
- [ ] Komut: `pytest` (ve varsa frontend test) yeşil; çıktı özetini logla.
- [ ] CI workflow dosyası mevcut ve testleri çağırıyor.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-5.2-test-kalite.md` yaz (test kapsamı, geçen test sayısı, CI dosyası).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (varsa kapsam boşlukları). Temiz çık.
