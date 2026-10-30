@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
py app.py
pause

set DB_HOST=localhost
set DB_PORT=3306
set DB_USER=root
set DB_PASSWORD=mysqlpass@12
set DB_NAME=locallink