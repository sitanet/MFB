@echo off
echo ================================
echo Deploying to Production Server
echo ================================
echo.
echo Connecting to 164.90.217.87...
echo.
ssh bayo@164.90.217.87 "cd /home/bayo/MFB_NEW && git pull origin main && sudo systemctl restart gunicorn"
echo.
echo ================================
echo Deployment Complete!
echo ================================
pause
