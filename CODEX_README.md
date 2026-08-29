# CV-Tailor İş Paketi Çalıştırma Ortamı

Bu klasör, `IS_PAKETLERI.md` içindeki her iş paketini **Codex'e tek tek, temiz oturumda**
yaptırmak için tasarlanmış bir çalışma alanıdır.

## Tasarım mantığı

1. **Her iş paketi = bir prompt dosyası** (`prompts/IP-*.md`). Her dosya tek bir paketi bitirir.
2. **Her çalıştırma temiz (cache'siz) bir Codex oturumudur.** `run-ip.ps1` her seferinde
   yeni bir `codex exec` process'i başlatır; oturum hafızası / cache bir sonrakine taşınmaz.
3. **Süreklilik kanıtla sağlanır.** Codex'in hafızası olmadığı için, her prompt işe başlamadan
   önce bağımlılık paketlerinin `logs/IP-*.md` kayıtlarını **ve diskteki gerçek dosyaları**
   doğrular. "Yapıldı" demek yetmez; kanıt aranır.
4. **Her işten sonra log yazılır** (`logs/IP-*.md`) ve `state/PROGRESS.md` güncellenir.
5. **Kurallar `architect.md`'de.** `AGENTS.md` Codex'i otomatik oraya yönlendirir.

## Önkoşullar

- [Codex CLI](https://github.com/openai/codex) kurulu ve PATH'te: `npm i -g @openai/codex`
- Codex'in oturum açmış olması (`codex login` veya API key).
- Docker, Python ve Node — iş paketleri bunları kullanır (Faz 0'da kurulur).

## Kullanım

### Tek bir paketi çalıştır
```powershell
cd C:\Users\LENOVO\OneDrive\Desktop\cv-tailor
.\run-ip.ps1 -Prompt prompts\IP-0.1-repo-iskelet.md
```

### Tüm paketleri sırayla çalıştır (her biri temiz oturum)
```powershell
cd C:\Users\LENOVO\OneDrive\Desktop\cv-tailor
.\run-all.ps1
```
`run-all.ps1` her paketten sonra logun `DURUM: TAMAMLANDI` içerdiğini kontrol eder;
içermiyorsa zinciri **durdurur**.

### Belirli bir paketten devam et
```powershell
.\run-all.ps1 -StartAt IP-2.1
```

### Manuel / interaktif çalıştırmak istersen
`prompts\IP-*.md` dosyasının içeriğini kopyalayıp interaktif `codex` oturumuna yapıştır.
Yine de **her paket için oturumu kapatıp yeniden aç** (temizlik ilkesi).

## Akış (tek bir paket için)

```
run-ip.ps1  ─►  codex exec (TEMIZ)  ─►  architect.md oku
                                       ─►  FAZ A: bağımlılıkları KANITLA doğrula  (yoksa BLOCKED yaz, dur)
                                       ─►  FAZ B: görevi checklist'e göre yap
                                       ─►  FAZ C: DoD'u fiilen doğrula
                                       ─►  FAZ D: logs/IP-*.md yaz + PROGRESS güncelle
                                       ─►  FAZ E: temiz çıkış
                          oturum kapanır (cache yok)
```

## Dizinler
- `prompts/` — çalıştırılacak iş paketi promptları (girdi).
- `logs/` — Codex'in ürettiği kanıt kayıtları (çıktı). `BLOCKED-IP-*.md` engelleri gösterir.
- `state/PROGRESS.md` — tüm paketlerin canlı durum tablosu.
- `templates/LOG_TEMPLATE.md` — log formatı.
- `architect.md` — Codex'in uyduğu ana kural seti.

## İlerlemeyi görmek
`state/PROGRESS.md` dosyasına bak; veya `logs/` içindeki dosya sayısına.
