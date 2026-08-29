# PROGRESS.md — İş Paketi Durum Tablosu

> Codex her paketi bitirince ilgili satırı günceller. DURUM değerleri:
> ⬜ TODO · 🟡 KISMİ · ⛔ BLOCKED · ✅ TAMAMLANDI

| İP | Başlık | Bağımlılık | Durum | Log | Tarih |
|---|---|---|---|---|---|
| IP-0.1 | Repo ve monorepo yapısı | — | ✅ TAMAMLANDI | [log](../logs/IP-0.1-repo-iskelet.md) | 2026-06-13 |
| IP-0.2 | Yerel altyapı (Docker Compose) | 0.1 | ✅ TAMAMLANDI | [log](../logs/IP-0.2-docker-altyapi.md) | 2026-06-13 |
| IP-0.3 | Backend temel kurulum | 0.2 | ✅ TAMAMLANDI | [log](../logs/IP-0.3-backend-kurulum.md) | 2026-06-13 |
| IP-0.4 | Frontend temel kurulum | 0.3 | ✅ TAMAMLANDI | [log](../logs/IP-0.4-frontend-kurulum.md) | 2026-06-13 |
| IP-1.1 | Veritabanı şeması (multi-tenant) | 0.3 | ✅ TAMAMLANDI | [log](../logs/IP-1.1-db-sema.md) | 2026-06-13 |
| IP-1.2 | Auth (JWT) | 1.1 | ✅ TAMAMLANDI | [log](../logs/IP-1.2-auth-jwt.md) | 2026-06-13 |
| IP-1.3 | Profil CRUD | 1.2 | ✅ TAMAMLANDI | [log](../logs/IP-1.3-profil-crud.md) | 2026-06-13 |
| IP-1.4 | Frontend auth akışı | 1.3, 0.4 | ✅ TAMAMLANDI | [log](../logs/IP-1.4-frontend-auth.md) | 2026-06-13 |
| IP-2.0 | LLM ve Embedding altyapısı | 0.3 | ✅ TAMAMLANDI | [log](../logs/IP-2.0-llm-embedding.md) | 2026-06-14 |
| IP-2.1 | Manuel havuz girişi | 2.0, 1.1 | ✅ TAMAMLANDI | [log](../logs/IP-2.1-manuel-havuz.md) | 2026-06-18 |
| IP-2.2 | PDF CV parse | 2.0, 2.1 | ✅ TAMAMLANDI | [log](../logs/IP-2.2-pdf-parser.md) | 2026-06-18 |
| IP-2.3 | GitHub OAuth + analiz | 2.0, 1.1 | ✅ TAMAMLANDI | [log](../logs/IP-2.3-github-analiz.md) | 2026-06-18 |
| IP-2.4 | ItemExtractor + onay akışı | 2.2, 2.3 | ✅ TAMAMLANDI | [log](../logs/IP-2.4-itemextractor-onay.md) | 2026-06-18 |
| IP-2.5 | Graph 1 orkestrasyonu | 2.4 | ✅ TAMAMLANDI | [log](../logs/IP-2.5-graph1-orkestrasyon.md) | 2026-06-18 |
| IP-2.6 | Frontend: Havuz ekranı | 2.1, 1.4 | ✅ TAMAMLANDI | [log](../logs/IP-2.6-frontend-havuz.md) | 2026-06-18 |
| IP-3.1 | İlan girişi + JobParser | 2.0, 1.1 | ✅ TAMAMLANDI | [log](../logs/IP-3.1-jobparser.md) | 2026-06-18 |
| IP-3.2 | Selector | 3.1, 2.1 | ✅ TAMAMLANDI | [log](../logs/IP-3.2-selector.md) | 2026-06-18 |
| IP-3.3 | CVTailor | 3.2 | ✅ TAMAMLANDI | [log](../logs/IP-3.3-cvtailor.md) | 2026-06-18 |
| IP-3.4 | Evaluator (ATS skoru) | 3.3 | ✅ TAMAMLANDI | [log](../logs/IP-3.4-evaluator.md) | 2026-06-18 |
| IP-3.5 | TypstRenderer + render kuyruğu | 3.3 | ✅ TAMAMLANDI | [log](../logs/IP-3.5-typst-render.md) | 2026-06-18 |
| IP-3.6 | Graph 2 orkestrasyonu | 3.5 | ✅ TAMAMLANDI | [log](../logs/IP-3.6-graph2-orkestrasyon.md) | 2026-06-21 |
| IP-3.7 | Frontend: İlan girişi + CV sonucu | 3.6, 1.4 | ✅ TAMAMLANDI | [log](../logs/IP-3.7-frontend-cv-sonuc.md) | 2026-06-21 |
| IP-4.1 | KVKK rıza ve aydınlatma | 1.2 | ✅ TAMAMLANDI | [log](../logs/IP-4.1-kvkk-riza.md) | 2026-06-21 |
| IP-4.2 | Hesap silme (cascade) | 1.1 | ✅ TAMAMLANDI | [log](../logs/IP-4.2-hesap-silme.md) | 2026-06-21 |
| IP-4.3 | Veri saklama/güvenlik kontrolleri | 2.3 | ✅ TAMAMLANDI | [log](../logs/IP-4.3-veri-guvenlik.md) | 2026-06-21 |
| IP-5.1 | i18n (TR/EN arayüz) | 1.4 | ✅ TAMAMLANDI | [log](../logs/IP-5.1-i18n.md) | 2026-06-21 |
| IP-5.2 | Test ve kalite | 3.6 | ✅ TAMAMLANDI | [log](../logs/IP-5.2-test-kalite.md) | 2026-06-21 |
| IP-5.3 | Gözlemlenebilirlik ve dağıtım | 3.6 | ✅ TAMAMLANDI | [log](../logs/IP-5.3-gozlemlenebilirlik-dagitim.md) | 2026-06-21 |
