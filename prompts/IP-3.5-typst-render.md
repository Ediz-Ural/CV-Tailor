# PROMPT — IP-3.5: TypstRenderer + render kuyruğu

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-3.5-typst-render`
- **Bağımlılıklar:** IP-3.3
- **Referans:** PROJECT_CONTEXT §4 (Render notu), §7 (Graph 2) · IS_PAKETLERI İP-3.5

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-3.3-cvtailor.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: CVTailor yapılandırılmış CV içeriği + `output_language` üretiyor; `generated_cvs` tablosu var.
- [ ] Typst CLI kurulu/erişilebilir (yoksa Dockerfile'a ekle ve logla).
> ⛔ Eksikse: `logs/BLOCKED-IP-3.5.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] "Jake's Resume" tarzı CV şablonunu **Typst**'e taşı (`backend/app/render/templates/`).
- [ ] CV içeriğini Typst kaynağına basan üretici (`typst_source` üret).
- [ ] Typst CLI'yi **subprocess** ile çağır: **izole geçici dizin + timeout** (bozuk girdi sonsuz döngüye sokmasın).
- [ ] Render **arka plan kuyruğunda** (Celery/RQ veya başlangıçta FastAPI BackgroundTasks) — senkron HTTP'de değil.
- [ ] Çıktı `generated_cvs`'e: `typst_source`, `pdf_path`, `selected_pool_item_ids[]`, `ats_score` (IP-3.4'ten), `output_language`.
- [ ] PDF indirme endpoint'i.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Pipeline sonunda indirilebilir bir PDF üretiliyor.
- [ ] Test: örnek içerik → PDF dosyası oluşuyor, `pdf_path` kaydediliyor, indirilebiliyor.
- [ ] Test: bozuk/aşırı girdi timeout'a takılıyor, process'i kilitlemiyor; geçici dizin temizleniyor.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-3.5-typst-render.md` yaz (kuyruk seçimi, timeout değeri, şablon yolu, PDF kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (IP-3.6 tüm node'ları graph'a bağlayacak). Temiz çık.
