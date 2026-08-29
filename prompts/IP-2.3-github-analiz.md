# PROMPT — IP-2.3: GitHub OAuth + analiz (GitHubAnalyzer node)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-2.3-github-analiz`
- **Bağımlılıklar:** IP-2.0, IP-1.1
- **Referans:** PROJECT_CONTEXT §8, §10 · IS_PAKETLERI İP-2.3

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-2.0-llm-embedding.md` ve `logs/IP-1.1-db-sema.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: `github_connections` tablosu (`access_token_encrypted`), LLM structured çağrı, embedding servisi.
> ⛔ Eksikse: `logs/BLOCKED-IP-2.3.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] GitHub OAuth akışı: başlat + callback; kullanıcı token'ı **şifreli** olarak `github_connections`'a yaz
      (asla plaintext; şifreleme anahtarı config'ten).
- [ ] Repo çekme + **filtreleme** (§8): fork OLMAYAN + commit'i olan + README'si olan repolar. Boş/fork/tutorial elenir.
- [ ] Her repo için sinyal: README içeriği + dil dağılımı + commit sayısı + orijinal/fork → birlikte değerlendir.
- [ ] LLM structured çıkarım: `{ alan, teknolojiler, kısa_açıklama }`.
- [ ] `pool_items` formatına normalize: `source="github"`, embedding + dil, **`verified_by_user=false`**.
- [ ] **Arka plan job** olarak çalış (rate limit 5000/saat; senkron HTTP'yi bloklama).

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Kullanıcı GitHub bağlayınca, filtrelenmiş repolardan aday öğeler (onaysız) havuza düşüyor.
- [ ] Test: token `github_connections`'ta şifreli (plaintext değil) — doğrula.
- [ ] Test: fork/boş repo elenmiş; kalanlar `source=github`, `verified_by_user=false`, embedding dolu.
- [ ] Test: işlem background job olarak tetikleniyor (HTTP yanıtı beklemeden döner).
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-2.3-github-analiz.md` yaz (şifreleme yöntemi, filtre kuralları, background job mekanizması).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (onay IP-2.4; güvenlik denetimi IP-4.3). Temiz çık.
