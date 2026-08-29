# PROMPT — IP-4.3: Veri saklama / güvenlik kontrolleri

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-4.3-veri-guvenlik`
- **Bağımlılıklar:** IP-2.3
- **Referans:** PROJECT_CONTEXT §8, §10 · IS_PAKETLERI İP-4.3

---

## FAZ A — ÖN KONTROL (önceki işi DOĞRULA)
- [ ] `logs/IP-2.3-github-analiz.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: `github_connections.access_token_encrypted` üzerinden token saklanıyor.
> ⛔ Eksikse: `logs/BLOCKED-IP-4.3.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] **GitHub token şifreleme denetimi:** DB'de ve loglarda **asla plaintext** olmadığını doğrula/garantile.
      Şifreleme anahtarı ortamdan; gerekirse şifreleme katmanını sağlamlaştır.
- [ ] Hassas verilerin loglara sızmadığını kontrol (token, parola, kişisel veri redaksiyonu).
- [ ] **Veri saklama/silme politikası** dokümanı (`docs/` veya kod yorumları) — politikanın kod ile uyumu.
- [ ] (Varsa) parola hash, JWT secret yönetimi gözden geçir.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Güvenlik kontrol listesi geçiyor.
- [ ] Test: DB'de token şifreli (ham metin değil); log çıktısında token/parola görünmüyor.
- [ ] Kontrol listesi sonucu (madde madde geçti/kaldı) logla.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-4.3-veri-guvenlik.md` yaz (güvenlik kontrol listesi + sonuçlar, bulgular).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (varsa açık güvenlik bayrakları). Temiz çık.
