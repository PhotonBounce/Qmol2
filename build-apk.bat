@echo off
setlocal enabledelayedexpansion

title Q-Mol Android APK Builder

echo.
echo   ============================================
echo    Q-Mol Android APK Builder
echo   ============================================
echo.

:: Paths
set "FLUTTER_DIR=D:\flutter"
set "JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot"
set "ANDROID_SDK=C:\Users\fucktrumpandrednecks\AppData\Local\Android\Sdk"
set "PROJECT_DIR=D:\Qmol-3\mobile"

:: Check Flutter
if not exist "%FLUTTER_DIR%\bin\flutter.bat" (
    echo   [ERROR] Flutter not found at %FLUTTER_DIR%
    echo   Download from: https://docs.flutter.dev/get-started/install/windows
    pause
    exit /b 1
)

:: Check Java
if not exist "%JAVA_HOME%\bin\java.exe" (
    echo   [ERROR] Java JDK 17 not found at %JAVA_HOME%
    echo   Download from: https://adoptium.net
    pause
    exit /b 1
)

:: Check Android SDK
if not exist "%ANDROID_SDK%\platform-tools\adb.exe" (
    echo   [ERROR] Android SDK not found at %ANDROID_SDK%
    echo   Install Android Studio or SDK command line tools.
    pause
    exit /b 1
)

:: Set environment
set "PATH=%FLUTTER_DIR%\bin;%JAVA_HOME%\bin;%ANDROID_SDK%\platform-tools;%ANDROID_SDK%\build-tools\37.0.0;%PATH%"
set "ANDROID_SDK_ROOT=%ANDROID_SDK%"
set "ANDROID_HOME=%ANDROID_SDK%"

echo   [OK] Flutter: %FLUTTER_DIR%
echo   [OK] Java:   %JAVA_HOME%
echo   [OK] Android SDK: %ANDROID_SDK%

:: Configure Flutter
flutter config --no-analytics >nul 2>&1
flutter config --jdk-dir="%JAVA_HOME%" >nul 2>&1

:: Generate keystore if not exists
set "KEYSTORE=%PROJECT_DIR%\android\app\qmol-release.keystore"
if not exist "%KEYSTORE%" (
    echo.
    echo   [INFO] Generating release keystore...
    echo   You will be asked for a password. Remember it!
    "%JAVA_HOME%\bin\keytool" -genkey -v -keystore "%KEYSTORE%" -alias qmol -keyalg RSA -keysize 2048 -validity 10000
    if errorlevel 1 (
        echo   [WARNING] Keystore generation failed. Debug build only.
    )
)

:: Build
echo.
echo   ============================================
echo    Building APK...
echo    This may take 10-20 minutes on first run.
echo   ============================================
echo.

cd /d "%PROJECT_DIR%"

:: Try release build first
if exist "%KEYSTORE%" (
    flutter build apk --release
) else (
    echo   [INFO] No keystore found. Building debug APK...
    flutter build apk --debug
)

if errorlevel 1 (
    echo.
    echo   [ERROR] Build failed.
    pause
    exit /b 1
)

:: Find the APK
echo.
echo   [OK] Build successful!
for /f "delims=" %%a in ('dir /s /b "%PROJECT_DIR%\build\app\outputs\flutter-apk\*.apk"') do (
    echo   APK: %%a
    set "APK_PATH=%%a"
)

:: Copy to deploy
copy "%APK_PATH%" "%PROJECT_DIR%\..\deploy\qmol.apk" >nul 2>&1
if exist "%PROJECT_DIR%\..\deploy\qmol.apk" (
    echo   [OK] Copied to deploy\qmol.apk
)

echo.
pause
