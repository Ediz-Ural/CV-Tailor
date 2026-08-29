# Log - IP-5.1: i18n (TR/EN arayuz)

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-21 13:20
- **Is paketi prompt'u:** `prompts/IP-5.1-i18n.md`
- **Bagimliliklar (dogrulandi mi?):** IP-1.4 dogrulandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-1.4-frontend-auth.md` mevcut ve `DURUM: TAMAMLANDI`.
- Frontend temel ekran dosyalari diskte mevcut: `frontend/src/App.tsx`, `frontend/src/lib/api.ts`, `frontend/src/lib/auth.ts`.
- On kontrol komutu:
  ```text
  npm run build
  ```
- Cikti ozeti: Vite 8.0.16 ile 2145 modul donusturuldu; `dist/` hatasiz uretildi.

## 2. Yapilan isler (FAZ B)
- [x] Frontend i18n altyapisi kuruldu: `i18next`, `react-i18next`, `i18next-browser-languagedetector`.
- [x] TR + EN ceviri kaynaklari eklendi: `frontend/src/i18n/resources.ts`.
- [x] i18n baslatma ve dil algilama eklendi: `frontend/src/i18n/index.ts`; tercih sirasi `localStorage`, `navigator`, `htmlTag`.
- [x] Mevcut ekran metinleri i18n anahtarlarina tasindi: auth, workspace nav, profil, havuz, CV uretim ve sonuc ekranlari.
- [x] Dil degistirici UI eklendi: auth ekraninda ve workspace header'inda TR/EN segmented control.
- [x] Karma icerik kaniti eklendi: havuz ekraninda TR/EN aciklama degisirken `FastAPI`, `React`, `PostgreSQL` teknik terimleri `TECH_TERMS` sabitlerinden korunur.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `frontend/package.json` | degisti | i18n kutuphaneleri eklendi |
| `frontend/package-lock.json` | degisti | i18n bagimlilik kilidi guncellendi |
| `frontend/src/i18n/index.ts` | yeni | i18next init, dil algilama ve localStorage tercih saklama |
| `frontend/src/i18n/resources.ts` | yeni | TR/EN ceviri kaynaklari ve cevrilmeyen teknik terim sabitleri |
| `frontend/src/main.tsx` | degisti | i18n init import edildi |
| `frontend/src/App.tsx` | degisti | UI metinleri `t()` anahtarlarina tasindi; dil degistirici eklendi |
| `logs/IP-5.1-i18n.md` | yeni | Is paketi kanit kaydi |
| `state/PROGRESS.md` | degisti | IP-5.1 tamamlandi durumu |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Arayuz dili degistirilebiliyor, karma icerik duzgun gosteriliyor.
- **Calistirilan komutlar:**
  ```text
  npm run build
  npm run lint
  Select-String -Path frontend\src\i18n\resources.ts -Pattern "Yetkinlik havuzu|Capability pool|FastAPI|React|PostgreSQL|Hesabina giris yap|Sign in to your account|Pipeline baslat|Start"
  rg -n "changeLanguage|cv-tailor.language|navigator|LanguageSwitcher|termsNote" frontend\src
  ```
- **Cikti ozeti:**
  - `npm run build`: TypeScript + Vite build hatasiz; 2175 modul donusturuldu; `dist/` uretildi.
  - `npm run lint`: ESLint hatasiz tamamlandi.
  - TR/EN kaynak kaniti: `Hesabina giris yap` / `Sign in to your account`, `Yetkinlik havuzu` / `Capability pool`, `pipeline baslat` / `Start pipeline` kaynaklarda mevcut.
  - Teknik terim kaniti: `FastAPI`, `React`, `PostgreSQL` iki dilde de `TECH_TERMS` sabitlerinden geliyor; cevrilmiyor.
  - Dil degistirme kaniti: `LanguageSwitcher` `i18n.changeLanguage(...)` cagiriyor; dil tercihi `cv-tailor.language` localStorage anahtarinda saklaniyor, varsayilan algilama `navigator` destekli.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- i18n kaynak konumu: `frontend/src/i18n/resources.ts`.
- i18n baslatma konumu: `frontend/src/i18n/index.ts`.
- Teknik terimler yeni ekranlarda da `TECH_TERMS` veya ayni yaklasimla korunmali.

## 6. Acik sorunlar / bayraklar
- Backend'den gelen KVKK metni API icerigi oldugu icin bu paket kapsaminda ceviri kaynagina tasinmadi.
