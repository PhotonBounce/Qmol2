# Quick Signing Walkthrough (5 minutes)

## Prerequisites

- Java JDK 8+ (for `keytool`)
- Flutter SDK 3.19+
- Android SDK

---

## Commands

```bash
# 1. Generate signing key
cd mobile/android/app
keytool -genkey -v -keystore qmol-release.keystore -alias qmol -keyalg RSA -keysize 2048 -validity 10000

# 2. Create key.properties
cd ../..
cat > android/key.properties << 'EOF'
storePassword=YOUR_PASSWORD
keyPassword=YOUR_PASSWORD
keyAlias=qmol
storeFile=app/qmol-release.keystore
EOF

# 3. Build AAB
flutter build appbundle --release --dart-define=QMOL_API=https://api.qmol.app/v1

# 4. Verify signing
jarsigner -verify -verbose -certs build/app/outputs/bundle/release/app-release.aab
```

---

## Play Store Upload Checklist

- [ ] Generate keystore (`qmol-release.keystore`)
- [ ] Create `key.properties` with real passwords
- [ ] Build AAB (`flutter build appbundle --release`)
- [ ] Verify signing (`jarsigner -verify`)
- [ ] Upload to Play Console
- [ ] Complete content rating
- [ ] Set up subscriptions (`qmol_research_monthly`, `qmol_commercial_monthly`)
- [ ] Add screenshots (phone + tablet)
- [ ] Write store listing (title, short description, full description)
- [ ] Submit for review

---

## Quick Reference: File Locations

| File | Path | Purpose |
|------|------|---------|
| Keystore | `mobile/android/app/qmol-release.keystore` | Signing key (DO NOT COMMIT) |
| Key properties | `mobile/android/key.properties` | Signing credentials (DO NOT COMMIT) |
| Build config | `mobile/android/app/build.gradle` | Signing + build settings |
| ProGuard rules | `mobile/android/app/proguard-rules.pro` | Code obfuscation rules |
| Manifest | `mobile/android/app/src/main/AndroidManifest.xml` | Permissions & app metadata |
| AAB output | `mobile/build/app/outputs/bundle/release/app-release.aab` | Play Store upload artifact |

---

## Environment Variable Fallback

If `key.properties` is missing, the build falls back to environment variables:

```bash
export QMOL_KEY_ALIAS=qmol
export QMOL_KEY_PASSWORD=your_password
export QMOL_STORE_PASSWORD=your_password
export QMOL_KEYSTORE_PATH=/absolute/path/to/qmol-release.keystore
```

This is useful for CI/CD pipelines (GitHub Actions, GitLab CI, etc.).
