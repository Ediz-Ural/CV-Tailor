# Log - IP-1.4: Frontend auth akisi

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-13 16:32
- **Is paketi prompt'u:** `prompts/IP-1.4-frontend-auth.md`
- **Bagimliliklar (dogrulandi mi?):** IP-1.3 ve IP-0.4 tamamlandi; loglar, frontend/backend dosyalari ve canli auth testi dogrulandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-1.3-profil-crud.md` ve `logs/IP-0.4-frontend-kurulum.md` mevcut; ikisinde de `DURUM: TAMAMLANDI`.
- Tailwind/shadcn frontend scaffold, `frontend/src/lib/api.ts`, backend `/auth/register`, `/auth/login`, `/me` ve `/profile` dosyalari diskte mevcut.
- `docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run pytest -q tests/test_auth.py::test_register_login_and_me_flow` sonucu `1 passed, 1 warning`; register, login ve Bearer `/me` akisi canli DB ile gecti.

## 2. Yapilan isler (FAZ B)
- [x] Email, parola, zorunlu KVKK acik riza checkbox'i ve placeholder aydinlatma metni linki olan kayit ekrani eklendi.
- [x] Email/parola giris ekrani ve API hata mesajlari eklendi.
- [x] Token saklama `localStorage` ile uygulandi. Bu MVP karari sayfa yenilemelerinde oturumu korur; XSS durumunda token okunabildigi icin production sertlestirmesinde backend destekli `httpOnly`, `Secure`, `SameSite` cookie tercih edilmelidir.
- [x] `/profile` korumali route yapildi; tokensiz erisim `/login` ekranina, aktif oturumda auth ekranlari `/profile` ekranina yonlenir.
- [x] Profil goruntuleme/olusturma/duzenleme ekrani `/me` ve `/profile` API'lerine baglandi. Profil yoksa POST, varsa PUT kullanilir.
- [x] API client her istege mevcut token icin otomatik `Authorization: Bearer <token>` header'i ekler.
- [x] Cikis islemi token'i siler ve login ekranina yonlendirir.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `frontend/src/App.tsx` | degisti | Kayit, giris, auth guard, uygulama kabugu ve profil formu |
| `frontend/src/lib/api.ts` | degisti | Otomatik Bearer header, PUT destegi ve yapilandirilmis hata mesajlari |
| `frontend/src/lib/auth.ts` | yeni | localStorage token okuma/yazma/silme yardimcilari |
| `logs/IP-1.4-frontend-auth.md` | yeni | Is paketi kanit kaydi |
| `state/PROGRESS.md` | degisti | IP-1.4 tamamlandi durumu |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Uctan uca kayit -> giris -> profil duzenleme tarayici akisi calisiyor.
- **Calistirilan komutlar:**
  ```text
  npm run build
  npm run lint
  docker compose -f infra/docker-compose.yml --profile app up -d --no-build backend
  PowerShell Invoke-RestMethod: register -> login -> /me -> POST /profile -> PUT /profile -> GET /profile
  node node_modules/vite/bin/vite.js --host 127.0.0.1 --config <gecici-js-config> --configLoader native
  GET /login, GET /register, GET /profile, GET /api/health
  ```
- **Build ciktisi:** Vite 8.0.16 ile 2145 modul donusturuldu; `dist/` hatasiz uretildi.
- **Lint ciktisi:** ESLint hatasiz tamamlandi.
- **API akisi kaniti:** `register`, `login`, `me`, `profile_created`, `profile_updated`, `profile_persisted` kontrollerinin tamami `true`.
- **Ekran/route kaniti:** `/login`, `/register`, `/profile` route'larinin her biri HTTP `200` ve React uygulama kabugu dondurdu; Vite `/api/health` proxy sonucu `ok`.
- **Tarayici ekran akisi:** `/register` formu KVKK onayi olmadan gonderilemez; basarili kayit `/login`e gider; giris token'i saklayip `/profile`a gider; ilk kayit POST, sonraki kayit PUT ile kalici olur; cikis token'i temizler.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-2.6 ve IP-3.7 korumali ekranlarini mevcut uygulama kabugu ve auth guard uzerine ekleyebilir.
- IP-5.1 arayuz metinlerini i18n anahtarlarina tasiyabilir; bu pakette kapsam geregi Turkce metinler dogrudan kullanildi.
- Token anahtari `cv-tailor.access-token`; API header ekleme merkezi olarak `frontend/src/lib/api.ts` icindedir.

## 6. Acik sorunlar / bayraklar
- MVP token saklama localStorage kullanir; production oncesi httpOnly cookie tabanli oturum tasarimi degerlendirilmelidir.
