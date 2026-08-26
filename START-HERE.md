# Start here — running the bot on Windows

Your `.env` file is already filled in. You do not need to edit anything
to see the admin UI working.

---

## Step 1 — Open a terminal in this folder

Open the `instagram-dm-bot` folder in File Explorer, click the address bar,
type `powershell` and press Enter.

You should see a prompt ending in `...\instagram-dm-bot>`.

---

## Step 2 — Check Python is installed

```powershell
python --version
```

Expect something like `Python 3.11.x` or higher.

If you get an error or the Microsoft Store opens, install Python from
https://www.python.org/downloads/ and **tick "Add python.exe to PATH"** on
the first screen of the installer. Then close and reopen PowerShell.

---

## Step 3 — Create a virtual environment

This keeps the bot's packages separate from the rest of your system.

```powershell
python -m venv venv
```

Runs for a few seconds, creates a `venv` folder. You only do this once.

---

## Step 4 — Activate it

```powershell
venv\Scripts\Activate.ps1
```

Your prompt should now start with `(venv)`.

**If you get a red error about "running scripts is disabled":**

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then run the activate command again. This only affects the current window.

You need to do Step 4 every time you open a new terminal.

---

## Step 5 — Install the packages

```powershell
pip install -r requirements.txt
```

Takes a minute. Lots of scrolling text is normal.

---

## Step 6 — Run it

```powershell
python app.py
```

You should see:

```
INFO Using file rules backend (rules.json)
INFO Admin UI enabled at /admin
 * Running on http://127.0.0.1:5000
```

**"Admin UI enabled" is the line that matters.** If it says DISABLED
instead, your `.env` file isn't being read — check it's in this same
folder and named exactly `.env` (not `.env.txt`).

---

## Step 7 — Open the editor

Go to: **http://localhost:5000/admin**

Password: whatever you set as `ADMIN_PASSWORD` in `.env`

You can now add keywords and replies, set up per-post rules, and save.
Changes apply instantly.

To stop the server, press `Ctrl+C` in the terminal.

---

## What works right now vs. what needs Meta

| | Status |
|---|---|
| Admin UI, editing rules, saving | Works now |
| Actually replying on Instagram | Needs Meta credentials |

The three `placeholder-replace-me` values in `.env` are your Meta app
credentials. Until you fill those in, the bot can't talk to Instagram —
but everything else runs fine, so you can set up all your rules first.

See `README.md` for how to get those credentials, and `DEPLOY.md` for
putting it online free.

---

## Quick reference — every time after the first

```powershell
venv\Scripts\Activate.ps1
python app.py
```

Then open http://localhost:5000/admin
