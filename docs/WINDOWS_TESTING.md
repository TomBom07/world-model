# Windows local testing

These commands assume Git and Python 3.11+ are installed.

## Fresh install

Open **PowerShell**:

```powershell
cd $HOME\Desktop
git clone https://github.com/TomBom07/world-model.git
cd world-model

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -e ".[dev]"

pytest
worldmodel doctor --seed 7
worldmodel frontier --seed 7
worldmodel serve --reload
```

Then open:

```text
http://127.0.0.1:8000
```

## If PowerShell blocks activation

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Updating an existing clone

```powershell
cd path\to\world-model
git fetch origin
git switch main
git pull --ff-only origin main
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
worldmodel doctor --seed 7
```

A successful doctor command ends with JSON containing `"status": "ok"`.
