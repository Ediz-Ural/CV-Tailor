# PROMPT — IP-0.1: Repo ve monorepo yapısı

> Codex: Bu dosya TEK bir iş paketidir. **ÖNCE `architect.md` oku**, sonra aşağıdaki 5 fazı
> (A→E) sırayla uygula. Temiz oturum kuralı geçerli: işini bitir, logla, çık. Kapsam dışına çıkma.

- **Slug:** `IP-0.1-repo-iskelet`
- **Bağımlılıklar:** YOK (ilk paket)
- **Referans:** PROJECT_CONTEXT §11 · IS_PAKETLERI İP-0.1

---

## FAZ A — ÖN KONTROL (başlangıç durumu temiz mi?)
Bu ilk pakettir, bağımlılık yok. Yine de kontrol et:
- [ ] Repo kökünde `PROJECT_CONTEXT.md` ve `IS_PAKETLERI.md` mevcut.
- [ ] Henüz `backend/ frontend/ infra/` klasörleri **yoksa** (varsa içeriğe dokunma, logda bayrak kaldır).
- [ ] `logs/` dizininde IP-0.1 logu **yok** (yoksa yeni iş; varsa önce mevcut logu oku, tekrar üretme).

## FAZ B — GÖREV (checklist)
- [ ] Repo kökünde `git init` (zaten git yoksa).
- [ ] `.gitignore` oluştur: Python (`__pycache__`, `*.pyc`, `.venv`), Node (`node_modules`, `dist`),
      ortam (`.env`, `.env.local`), IDE, OS dosyaları.
- [ ] Klasör iskeleti oluştur (boş klasörler için `.gitkeep`):
  ```
  backend/        # FastAPI uygulaması
  frontend/       # React + TS + Vite
  infra/          # docker-compose, Dockerfile'lar
  docs/           # buraya PROJECT_CONTEXT.md + IS_PAKETLERI.md kopyala VEYA referans bırak
  ```
- [ ] Repo kökünde `README.md` oluştur: proje adı, kısa açıklama (PROJECT_CONTEXT §1'den 2-3 cümle),
      "Kurulum" başlığı altında ileride doldurulacak placeholder.
- [ ] (Kapsam dışına çıkma: kod yazma, bağımlılık kurma — onlar sonraki paketlerin işi.)

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Repo klonlanınca `backend/ frontend/ infra/ docs/` klasörleri ve `.gitignore`, `README.md` görülüyor.
- [ ] Komut: `git status` çalışır ve yeni dosyalar listelenir. Çıktıyı not et.
- [ ] `git ls-files` veya klasör listesi ile yapı doğrulanır.

## FAZ D — KAYIT
- [ ] `templates/LOG_TEMPLATE.md`'yi kullanarak `logs/IP-0.1-repo-iskelet.md` yaz. Üretilen tüm dosyaları listele.
- [ ] `state/PROGRESS.md`'de IP-0.1 satırını `✅ TAMAMLANDI`, log linki ve tarih ile güncelle.

## FAZ E — ÇIKIŞ
- [ ] Tek paragraf özet ver (ne oluşturuldu, sonraki paket IP-0.2). Temiz çık, yarım dosya bırakma.
