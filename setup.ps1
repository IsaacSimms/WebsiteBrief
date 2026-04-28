# == setup.ps1 == #
# Run once from the project root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File setup.ps1
#
# This script handles the full first-time setup:
#   1. PowerShell execution policy (allows running .ps1 scripts)
#   2. Python virtual environment
#   3. All Python dependencies
#   4. Playwright browser (Chromium)
#   5. Output directories
#   6. .env file from template

$ErrorActionPreference = "Stop"   # stop the script on any error

Write-Host ""
Write-Host "========================================"
Write-Host "  WebsiteBrief — First-Time Setup"
Write-Host "========================================"

# == 1. Execution Policy == #
# Windows blocks .ps1 scripts by default. RemoteSigned allows local scripts
# and signed remote scripts. Scope CurrentUser means no admin rights needed.
Write-Host "`n[1/7] Setting PowerShell execution policy to RemoteSigned..."
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
Write-Host "  --> Done."

# == 2. Virtual Environment == #
# A virtual environment is an isolated Python installation just for this project.
# Every package you install goes here, not into your system Python.
Write-Host "`n[2/7] Creating virtual environment (.venv)..."
if (Test-Path ".venv") {
    Write-Host "  --> .venv already exists. Skipping creation."
} else {
    python -m venv .venv
    Write-Host "  --> Created."
}

# Activate it for the remainder of this script.
# You will need to run this line yourself each time you open a new terminal:
#   .\.venv\Scripts\Activate.ps1
Write-Host "  --> Activating .venv for this session..."
. .\.venv\Scripts\Activate.ps1

# == 3. Python Dependencies == #
Write-Host "`n[3/7] Installing Python packages from requirements.txt..."
pip install -r requirements.txt --quiet
Write-Host "  --> Done."

# == 4. Playwright Browser == #
# Playwright needs a real browser binary to automate. We install Chromium,
# which is the open-source base for Google Chrome.
Write-Host "`n[4/7] Installing Playwright browser (Chromium)..."
python -m playwright install chromium
Write-Host "  --> Done."

# == 5. Output Directories == #
# -Force means "don't fail if they already exist".
Write-Host "`n[5/6] Creating output directories..."
New-Item -ItemType Directory -Force -Path "outputs\briefs"        | Out-Null
New-Item -ItemType Directory -Force -Path "outputs\conversations" | Out-Null
New-Item -ItemType Directory -Force -Path "outputs\logs"          | Out-Null
Write-Host "  --> outputs/briefs, outputs/conversations, outputs/logs created."

# == 6. Environment File == #
# .env holds your secret API keys. It must never be committed to Git.
# .env.example is the safe template that IS committed.
Write-Host "`n[6/6] Setting up .env file..."
if (-Not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  --> .env created from .env.example."
    Write-Host "  *** ACTION REQUIRED: Open .env and fill in your ANTHROPIC_API_KEY ***"
} else {
    Write-Host "  --> .env already exists. Skipping."
}

# == Done == #
Write-Host ""
Write-Host "========================================"
Write-Host "  Setup complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Open .env and add your ANTHROPIC_API_KEY"
Write-Host "  2. Open config.yaml and set scrapers.active to your scraper name"
Write-Host "  3. Each time you open a new terminal, activate the venv:"
Write-Host "       .\.venv\Scripts\Activate.ps1"
Write-Host "  4. Run the full pipeline:  python run.py"
Write-Host "  5. See all options:        python run.py --help"
Write-Host ""
