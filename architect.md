# architect.md — CV-Tailor Codex Çalışma Anayasası

> Bu dosya Codex'in **her oturumda ilk okuması gereken** kuraldır. Her prompt dosyası
> seni buraya yönlendirir. Buradaki protokole **istisnasız** uy.

---

## 0. Sen kimsin, ne yapıyorsun?

Sen, `cv-tailor` projesini **iş paketi (İP) bazında, tek tek** inşa eden bir mühendislik
ajanısın. Projenin ne olduğu `PROJECT_CONTEXT.md` dosyasında, iş paketlerinin tamamı
`IS_PAKETLERI.md` dosyasında tanımlıdır.

Her seferinde sana **tek bir prompt dosyası** verilir (ör. `prompts/IP-1.2-auth-jwt.md`).
O dosyadaki **tek bir iş paketini** baştan sona bitirirsin ve oturumu kapatırsın.

---

## 1. TEMEL İLKE: Temiz oturum + kanıt temelli süreklilik

Her prompt **sıfırdan, temiz bir Codex oturumunda** çalışır. Senin **hafızan yoktur**:
- Bir önceki oturumda ne yaptığını **hatırlamazsın**.
- Bu yüzden süreklilik **hafızadan değil, KANITTAN** sağlanır.
- Kanıt = `logs/` altındaki log dosyaları + diskteki **gerçek dosyalar** + geçen testler.

**Kural:** Bir önceki işin "yapıldı" yazması yeterli DEĞİLDİR. O işin ürettiği dosyaların
gerçekten var olduğunu ve (varsa) testlerin geçtiğini **kendi gözünle doğrularsın.**

---

## 2. HER OTURUMUN DEĞİŞMEZ AKIŞI (5 Faz)

Her prompt dosyası aşağıdaki 5 fazı içerir. Sırayı asla bozma:

### FAZ A — ÖN KONTROL (Pre-flight / Doğrulama)
Bu iş paketinin **bağımlılıklarını** doğrula:
1. İlgili `logs/IP-<bağımlılık>.md` dosyaları **var mı**?
2. İçlerinde `DURUM: TAMAMLANDI` satırı **var mı**?
3. O loglarda "üretildi" denen **anahtar dosyalar diskte gerçekten var mı**? (prompt'ta listelenir)
4. Varsa o paketin **doğrulama komutu** (test/health) hâlâ **geçiyor mu**?

> ⛔ Eğer bu kontrollerden biri başarısızsa: **DUR. Hiçbir şey yazma/değiştirme.**
> `logs/BLOCKED-IP-<bu paket>.md` dosyasına neyin eksik olduğunu yaz ve oturumu bitir.

### FAZ B — GÖREV (Task)
Prompt'taki görev checklist'ini **madde madde** uygula. Her maddeyi bitirince zihnindeki
kutuyu işaretle. Maddeyi atlama, birleştirme veya kapsam dışına çıkma.

### FAZ C — DOĞRULAMA (Verify)
Bu iş paketinin "Definition of Done" (DoD) kriterini **fiilen** doğrula:
- Komut çalıştır (build/test/health/migration), çıktısını gör.
- Kanıtı (komut + çıktı özeti) bir sonraki faza taşımak üzere not et.

> ⛔ DoD doğrulanamıyorsa paket **TAMAMLANDI sayılmaz**. Sorunu çöz veya `BLOCKED` yaz.

### FAZ D — KAYIT (Log)
`templates/LOG_TEMPLATE.md` şablonunu kullanarak `logs/IP-<bu paket>.md` dosyasını yaz/güncelle.
Logda **abartma yok, sadece kanıt**: hangi dosyalar oluştu, hangi komut çalıştı, çıktı ne oldu.
Sonra `state/PROGRESS.md` içinde bu paketin satırını güncelle.

### FAZ E — ÇIKIŞ (Clean exit)
Çalışmayı özetleyen tek bir mesaj ver ve **dur**. Oturum kapanır; cache/artık durum bırakma.
(Geçici dosyalar, yarım bırakılmış değişiklik, açık process bırakma.)

---

## 3. LOG DOSYASI KURALLARI

- Konum: `logs/IP-<numara>-<slug>.md` (prompt dosyasıyla aynı slug).
- Şablon: `templates/LOG_TEMPLATE.md`.
- Zorunlu alanlar: `DURUM` (TAMAMLANDI | BLOCKED | KISMİ), tarih, üretilen/değişen dosya listesi,
  çalıştırılan doğrulama komutları + çıktı özeti, sonraki paket için notlar.
- **Asla** bir paketi gerçekten doğrulamadan `DURUM: TAMAMLANDI` yazma. Bu en kritik kuraldır.
- Engellenmişsen `logs/BLOCKED-IP-<numara>.md` yaz (neyin eksik olduğu + önerilen düzeltme).

---

## 4. PROJE GENELİ DEĞİŞMEZ KURALLAR (PROJECT_CONTEXT.md'den)

Hangi paketi yaparsan yap bunlara uy:
- **Multi-tenant her zaman:** her tablo ve her sorgu `user_id` ile izole. Her veri erişimi testinde
  "başka kullanıcının verisine erişilemez" kontrolü.
- **Uydurma bilgi yok:** otomatik çıkarımlar (PDF/GitHub) `verified_by_user=false` başlar;
  kullanıcı onayı olmadan CV'ye girmez.
- **Dil birinci sınıf:** TR + EN + karma. Teknik terimler çevrilmez. Türkçe'de ATS eşleşmesi
  exact string match ile DEĞİL, lemmatization/semantic ile yapılır.
- **Güvenlik:** GitHub token asla plaintext (şifreli saklanır). Parolalar bcrypt hash.
- **Render:** Typst CLI subprocess, izole geçici dizin + timeout, arka plan kuyruğunda.
- **Teknoloji yığını sabit:** FastAPI + PostgreSQL/pgvector + LangGraph + Typst + React/TS/Vite/Tailwind/shadcn.
  Kapsam kararlarını (scraping yok vb.) değiştirme.

---

## 5. KAPSAM DİSİPLİNİ

- Sadece o prompt'taki iş paketini yap. Başka paketin işini yapma ("bu arada şunu da ekleyeyim" YOK).
- Bir sonraki paketin işini görürsen bile **dokunma**; logda "sonraki paket için not" olarak bırak.
- Mimari kararları (PROJECT_CONTEXT.md) değiştirme; uyumsuzluk görürsen logda bayrak kaldır, kendi başına değiştirme.

---

## 6. DİZİN HARİTASI

```
repo-koku/
  architect.md            <- bu dosya (önce oku)
  AGENTS.md               <- Codex'i architect.md'ye yönlendiren ince işaretçi
  README.md               <- insan için kullanım talimatı
  run-ip.ps1              <- tek bir prompt'u temiz oturumda çalıştırır
  run-all.ps1             <- tüm paketleri sırayla, her biri temiz oturumda
  templates/
    LOG_TEMPLATE.md       <- her log bu şablonla yazılır
  prompts/
    IP-*.md               <- her iş paketi için bir prompt (çalıştırılacak girdi)
  logs/
    IP-*.md               <- her tamamlanan paketin kanıt kaydı (Codex yazar)
    BLOCKED-IP-*.md       <- engellenen paketler (Codex yazar)
  state/
    PROGRESS.md           <- tüm paketlerin durum tablosu (Codex günceller)
```

Proje kodu aynı repo kökünde (`backend/`, `frontend/`, `infra/`) üretilir.

---

## 7. ÖZET (her oturumda kendine hatırlat)

1. `architect.md`'yi okudum.
2. Bağımlılıkları KANITLA doğruladım (log + dosya + test). Olmadıysa DURDUM.
3. Görevi checklist'e göre madde madde yaptım.
4. DoD'u fiilen doğruladım.
5. Log yazdım + PROGRESS güncelledim (sadece kanıt).
6. Temiz çıktım.
