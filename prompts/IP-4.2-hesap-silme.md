# PROMPT — IP-4.2: Hesap silme (cascade)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-4.2-hesap-silme`
- **Bağımlılıklar:** IP-1.1
- **Referans:** PROJECT_CONTEXT §10 · IS_PAKETLERI İP-4.2

---

## FAZ A — ÖN KONTROL (önceki işi DOĞRULA)
- [ ] `logs/IP-1.1-db-sema.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: tüm tablolar `user_id` FK ile mevcut.
- [ ] (Mümkünse) auth çalışıyor, böylece silme korumalı endpoint olarak test edilebilir.
> ⛔ Eksikse: `logs/BLOCKED-IP-4.2.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] **"Hesabımı sil"** endpoint'i (korumalı): kullanıcının tüm `user_id` satırları **cascade** silinir
      (profiles, pool_items, jobs, generated_cvs, github_connections, users).
- [ ] İlişkili dosyalar temizlenir: üretilen **PDF dosyaları** ve GitHub token kaydı.
- [ ] FK'larda `ON DELETE CASCADE` veya uygulama seviyesinde tam temizlik (gerekirse migration).
- [ ] Geri dönülemez işlem için onay mekanizması (frontend opsiyonel; backend kesin siler).

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Hesap silinince kullanıcıya ait hiçbir veri kalmıyor.
- [ ] Test: veri dolu kullanıcı (profil + pool + job + cv + github) oluştur → sil → tüm tablolarda 0 satır, PDF dosyaları gitmiş.
- [ ] Test: başka kullanıcının verisi etkilenmiyor (izolasyon).
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-4.2-hesap-silme.md` yaz (cascade yöntemi, dosya temizliği, doğrulama kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver. Temiz çık.
