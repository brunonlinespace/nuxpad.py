@echo off
setlocal
set "ROOT=%~dp0.."
python "%ROOT%\source\nuxpad.py" %*
