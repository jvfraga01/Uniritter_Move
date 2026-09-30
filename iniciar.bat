@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

rem Launcher com dois cliques: baixa Python portatil, instala dependencias,
rem baixa o modelo de pose e roda o programa. Nao toca nada em src/ --
rem so orquestra o setup. Depois da primeira vez, os passos ja feitos sao
rem pulados (funciona offline).

set "PYVER=3.11.9"
set "PYDIR=%~dp0runtime"
set "PYEXE=%PYDIR%\python.exe"
set "PYZIP=%~dp0_runtime_python.zip"
set "GETPIP=%~dp0_get-pip.py"
set "MODEL=%~dp0models\pose_landmarker_lite.task"

echo ==============================================
echo   Contador de Agachamentos - Instalador/Launcher
echo ==============================================
echo.

if exist "%PYEXE%" goto step2

echo [1/4] Python portatil nao encontrado. Baixando (uma vez so)...

where curl >nul 2>nul
if errorlevel 1 goto erro_ferramentas

curl.exe -L -o "%PYZIP%" "https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip"
if errorlevel 1 goto erro_download

mkdir "%PYDIR%" >nul 2>nul
powershell -NoProfile -Command "Expand-Archive -LiteralPath '%PYZIP%' -DestinationPath '%PYDIR%' -Force"
if errorlevel 1 goto erro_extract
del "%PYZIP%" >nul 2>nul

for %%F in ("%PYDIR%\python3*._pth") do (
    powershell -NoProfile -Command "(Get-Content -LiteralPath '%%~fF') -replace '#import site','import site' | Set-Content -LiteralPath '%%~fF'; Add-Content -LiteralPath '%%~fF' -Value '..'"
)

curl.exe -L -o "%GETPIP%" "https://bootstrap.pypa.io/get-pip.py"
if errorlevel 1 goto erro_download
"%PYEXE%" "%GETPIP%" --no-warn-script-location
if errorlevel 1 goto erro_pip
del "%GETPIP%" >nul 2>nul

echo Python portatil instalado com sucesso.
echo.

:step2
echo [2/4] Verificando dependencias Python...
"%PYEXE%" -c "import mediapipe, cv2, pytest" >nul 2>nul
if not errorlevel 1 goto step3

echo Instalando mediapipe, opencv e pytest -- pode demorar alguns minutos...
"%PYEXE%" -m pip install --no-warn-script-location -r "%~dp0requirements.txt"
if errorlevel 1 goto erro_pip

:step3
echo Dependencias OK.
echo.

echo [3/4] Verificando modelo de deteccao de pose...
if exist "%MODEL%" goto step4
echo Baixando modelo de pose -- arquivo unico de ~6MB...
"%PYEXE%" -m tools.download_model
if errorlevel 1 goto erro_model

:step4
echo Modelo OK.
echo.

echo [4/4] Iniciando o programa...
echo.
"%PYEXE%" "%~dp0main.py"
goto fim

:erro_ferramentas
echo.
echo ERRO: esta maquina nao tem "curl" no PATH.
echo Esse programa vem por padrao no Windows 10/11.
echo Se estiver faltando, instale o Python manualmente em
echo https://www.python.org/downloads/ e rode este arquivo de novo.
goto fim_erro

:erro_download
echo.
echo ERRO ao baixar arquivos. Verifique a conexao com a internet.
goto fim_erro

:erro_extract
echo.
echo ERRO ao extrair o Python portatil.
goto fim_erro

:erro_pip
echo.
echo ERRO ao instalar as dependencias Python (mediapipe/opencv/pytest).
goto fim_erro

:erro_model
echo.
echo ERRO ao baixar o modelo de pose.
goto fim_erro

:fim_erro
echo.
pause
exit /b 1

:fim
echo.
echo Programa encerrado.
pause
