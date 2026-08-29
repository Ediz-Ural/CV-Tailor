# PROMPT — IP-0.4: Frontend temel kurulum (React + TS + Vite + Tailwind/shadcn)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-0.4-frontend-kurulum`
- **Bağımlılıklar:** IP-0.3
- **Referans:** PROJECT_CONTEXT §4, §9 · IS_PAKETLERI İP-0.4

---

## FAZ A — ÖN KONTROL (bir önceki işi DOĞRULA)
- [ ] `logs/IP-0.3-backend-kurulum.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte gerçekten var: `backend/app/main.py`, `backend/app/core/config.py`, Alembic dosyaları.
- [ ] `GET /health` çalışıyor (backend'i ayağa kaldırıp doğrula).
> ⛔ Eksikse: `logs/BLOCKED-IP-0.4.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] `frontend/` içinde Vite + React + TypeScript scaffold (`npm create vite@latest`).
- [ ] Tailwind CSS kur + yapılandır (dark-mode-first; `darkMode: 'class'`).
- [ ] shadcn/ui kur (init). Framer Motion bağımlılığını ekle.
- [ ] **Tasarım tokenları** (§9): renk paleti (koyu nötr zemin + tek canlı aksan + success/warning/danger),
      tipografi (Inter gövde + JetBrains Mono aksan), orta köşe yarıçapı — Tailwind config + CSS değişkenleri.
- [ ] Temel layout iskeleti (sidebar/topbar) + boş ama temalı bir sayfa.
- [ ] API client (`frontend/src/lib/api.ts`): base URL `.env`'den (`VITE_API_URL`), fetch/axios sarmalayıcı.
- [ ] `frontend/.env.example` (`VITE_API_URL=http://localhost:8000`).

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** `npm run dev` ile boş ama temalı (dark-mode) uygulama açılıyor; backend `/health`'e istek atabiliyor.
- [ ] Komut: `npm run build` hatasız (TS derleniyor).
- [ ] API client ile `/health` çağrısının çalıştığını göster (geçici bir test çağrısı/komponent veya konsol kanıtı).
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-0.4-frontend-kurulum.md` yaz (LOG_TEMPLATE; dev portu, kullanılan token'lar, build kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (dev portu, sonraki paket IP-1.4 frontend auth bunun üzerine kuracak). Temiz çık.
