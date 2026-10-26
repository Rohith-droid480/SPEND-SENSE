@echo off
REM =========================================================================
REM SpendSense — Local Web Application Launcher (Windows)
REM =========================================================================

echo =========================================================================
echo  SpendSense — Expense Pattern & Anomaly Detector
echo  Starting local web server at http://127.0.0.1:8080...
echo =========================================================================
echo.

REM Open default browser to the SpendSense dashboard
start http://127.0.0.1:8080

REM Start the SpendSense standard-library web server
python server.py --port 8080

echo.
echo Server stopped.
pause
