# Lichi Hair — Setup (flat, easy version)

Everything is in ONE folder. Two of the files run the backend; the rest are the
website. You upload the whole folder to GitHub, then:

- **PythonAnywhere** uses only `app.py` + `requirements.txt` (the backend).
- **Vercel** serves the website files and ignores the backend (via `.vercelignore`).

```
app.py              backend  -> PythonAnywhere
requirements.txt    backend  -> PythonAnywhere
index.html          website  -> Vercel   (the shop, at / )
admin.html          website  -> Vercel   (admin, at /admin )
config.js           website  -> Vercel   (you edit this: the backend URL)
manifest.json       website  -> Vercel   (install the shop app)
manifest-admin.json website  -> Vercel   (install the admin app)
service-worker.js   website  -> Vercel
icon-192.png / icon-512.png / apple-touch-icon.png / favicon.png   (app icons)
vercel.json / .vercelignore / .gitignore
uploads/            (created on PythonAnywhere; product photos live here)
```

---

## STEP 1 — Put the folder on GitHub
Create an empty repo (e.g. `lichi-hair`) and push everything:
```bash
git init
git add .
git commit -m "Lichi Hair"
git branch -M main
git remote add origin https://github.com/YOURNAME/lichi-hair.git
git push -u origin main
```
(Or use GitHub's web "upload files" and drag the whole folder in.)

## STEP 2 — Backend on PythonAnywhere (do this first)
1. Bash console:
   ```bash
   git clone https://github.com/YOURNAME/lichi-hair.git
   pip3.10 install --user Flask
   ```
   The code is now at `/home/YOURUSER/lichi-hair`.
2. **Web** tab -> **Add a new web app** -> **Manual configuration** -> **Python 3.10**.
3. Open the **WSGI configuration file** link and replace everything with:
   ```python
   import sys
   path = "/home/YOURUSER/lichi-hair"
   if path not in sys.path:
       sys.path.insert(0, path)
   from app import app as application
   ```
4. **Static files** (optional but faster for photos):
   - URL: `/uploads/`  ->  Directory: `/home/YOURUSER/lichi-hair/uploads/`
5. **Environment variables**:
   - `LICHI_ADMIN_PASSWORD` = your admin password
   - (`LICHI_ALLOWED_ORIGINS` comes later, in Step 4)
6. **Reload**. Visit `https://YOURUSER.pythonanywhere.com/` — you should see
   `{"service": "Lichi Hair API", "ok": true}`. **Copy this URL.**

## STEP 3 — Tell the website where the backend is
Edit `config.js`, set your backend URL (no trailing slash), then push:
```js
window.API_BASE = "https://YOURUSER.pythonanywhere.com";
```
```bash
git add config.js && git commit -m "Set backend URL" && git push
```

## STEP 4 — Website on Vercel
1. Vercel -> **Add New Project** -> import your GitHub repo.
2. **Root Directory:** leave as the repo root (it's flat — nothing to change).
   **Framework Preset:** **Other**. No build command. Deploy.
3. You get a URL like `https://lichi-hair.vercel.app`
   - Shop: `/`   ·   Admin: `/admin`
4. Put that URL into PythonAnywhere -> Environment variables ->
   `LICHI_ALLOWED_ORIGINS = https://lichi-hair.vercel.app`, then **Reload**.

## STEP 5 — First setup in admin
Open `/admin`, log in, then:
1. **Brand & Contact:** brand name, WhatsApp number (country code, digits only,
   e.g. `2348012345678`), tagline, Instagram. Save.
2. **Add Hair:** add as many products as you want; mark them *Show on homepage*
   to feature them (no limit). Choose price mode and currency per item.

## Install to home screen (any device)
- **Phone (Android/Chrome):** open the site or `/admin` — an "Install" bar
  appears; tap it. Or use the browser menu -> *Install app / Add to Home screen*.
- **iPhone (Safari):** open the page -> Share -> **Add to Home Screen**.
- **Desktop (Chrome/Edge):** an install icon shows in the address bar.
The shop and the admin install as **two separate apps** with the Lichi icon.

## Troubleshooting
- Admin won't load / products blank + a **CORS** error in the browser console
  (F12): your Vercel URL isn't in `LICHI_ALLOWED_ORIGINS`. Add it, Reload.
- Always-blank shop: `config.js` points at the wrong backend URL.
- Photos missing: check the `/uploads/` static mapping in Step 2.4.
- Note: on PythonAnywhere's free tier, disk is limited — fine for a few hundred
  photos. For a big catalog, use a paid plan or an external image host.
