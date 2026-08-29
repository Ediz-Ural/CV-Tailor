# PROMPT — IP-5.3: Gözlemlenebilirlik ve dağıtım

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-5.3-gozlemlenebilirlik-dagitim`
- **Bağımlılıklar:** IP-3.6
- **Referans:** PROJECT_CONTEXT §4, §5 · IS_PAKETLERI İP-5.3

---

## FAZ A — ÖN KONTROL (önceki işi DOĞRULA)
- [ ] `logs/IP-3.6-graph2-orkestrasyon.md` var ve `DURUM: TAMAMLANDI`.
- [ ] (Tercihen) `logs/IP-5.2-test-kalite.md` TAMAMLANDI — dağıtımdan önce testler yeşil olmalı (yoksa bayrak kaldır).
- [ ] Diskte: backend + frontend + pipeline çalışıyor; docker-compose mevcut.
> ⛔ Eksikse: `logs/BLOCKED-IP-5.3.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] **Yapısal loglama** (JSON log), pipeline adım süreleri (her node ne kadar sürdü), hata izleme.
- [ ] Sağlık/durum metrikleri (health + temel metrikler); LLM/render kuyruğu görünürlüğü.
- [ ] **Üretim Dockerfile'ları** (backend + frontend) ve production docker-compose / dağıtım yapılandırması.
- [ ] Ortam değişkenleri dokümanı (`.env.example` güncel + açıklamalar).
- [ ] `README.md`'ye dağıtım talimatı ekle.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Uygulama bir ortama dağıtılıp uçtan uca çalışıyor.
- [ ] Komut: production imajları build oluyor; compose ile tüm stack ayağa kalkıyor; `/health` + örnek akış çalışıyor.
- [ ] Loglarda adım süreleri görünüyor.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-5.3-gozlemlenebilirlik-dagitim.md` yaz (log formatı, dağıtım adımları, build kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (proje MVP olarak dağıtıma hazır). Temiz çık.
