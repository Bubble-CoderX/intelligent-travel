@echo off
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo Killing PID %%a on port 8000...
    taskkill /pid %%a /f 2>nul
)
echo Port 8000 cleared.
