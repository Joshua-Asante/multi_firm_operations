@echo off
setlocal
for /f "usebackq delims=" %%i in (`git rev-parse --show-toplevel`) do set "ROOT=%%i"
copy /Y "%ROOT%\scripts\githooks\pre-commit" "%ROOT%\.git\hooks\pre-commit" >nul
echo Installed %ROOT%\.git\hooks\pre-commit
echo Git for Windows runs this hook via sh; keep the POSIX shebang in the template.
