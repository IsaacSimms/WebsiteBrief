@echo off
:: == setup.bat == ::
:: Run once from the project root:
::   setup.bat
::
:: This script handles the full first-time setup:
::   1. Python virtual environment
::   2. All Python dependencies
::   3. Playwright browser (Chromium)
::   4. Output directories
::   5. .env file from template
::   6. config.yaml from template

echo.
echo ========================================
echo   WebsiteBrief - First-Time Setup
echo ========================================

:: == 1. Virtual Environment == ::
echo.
echo [1/5] Creating virtual environment (.venv)...
if exist .venv (
    echo   --^> .venv already exists. Skipping creation.
) else (
    python -m venv .venv
    if errorlevel 1 ( echo ERROR: python -m venv failed. Is Python installed? & exit /b 1 )
    echo   --^> Created.
)

:: Activate for the remainder of this script.
:: To activate in future terminals run: .venv\Scripts\activate.bat
echo   --^> Activating .venv for this session...
call .venv\Scripts\activate.bat

:: == 2. Python Dependencies == ::
echo.
echo [2/5] Installing Python packages from requirements.txt...
pip install -r requirements.txt --quiet
if errorlevel 1 ( echo ERROR: pip install failed. & exit /b 1 )
echo   --^> Done.

:: == 3. Playwright Browser == ::
echo.
echo [3/5] Installing Playwright browser (Chromium)...
python -m playwright install chromium
if errorlevel 1 ( echo ERROR: Playwright install failed. & exit /b 1 )
echo   --^> Done.

:: == 4. Output Directories == ::
echo.
echo [4/6] Creating output directories...
if not exist outputs\briefs        mkdir outputs\briefs
if not exist outputs\conversations mkdir outputs\conversations
if not exist outputs\logs          mkdir outputs\logs
echo   --^> outputs/briefs, outputs/conversations, outputs/logs created.

:: == 5. Environment File == ::
echo.
echo [5/6] Setting up .env file...
if not exist .env (
    copy .env.example .env ^>nul
    echo   --^> .env created from .env.example.
    echo   *** ACTION REQUIRED: Open .env and fill in your ANTHROPIC_API_KEY ***
) else (
    echo   --^> .env already exists. Skipping.
)

:: == 6. Config File == ::
echo.
echo [6/6] Setting up config.yaml...
if not exist config.yaml (
    copy config.example.yaml config.yaml >nul
    echo   --^> config.yaml created from config.example.yaml.
    echo   *** ACTION REQUIRED: Open config.yaml and set your login_url ***
) else (
    echo   --^> config.yaml already exists. Skipping.
)

:: == Done == ::
echo.
echo ========================================
echo   Setup complete!
echo ========================================
echo.
echo Next steps:
echo   1. Open .env and add your ANTHROPIC_API_KEY
echo   2. Open config.yaml and set scrapers.active to your scraper name
echo   3. Each time you open a new terminal, activate the venv:
echo          .venv\Scripts\activate.bat
echo   4. Run the full pipeline:  python run.py
echo   5. See all options:        python run.py --help
echo.
