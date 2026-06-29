# Q-Mol — Flutter App (Android / iOS)

A full-featured mobile client for the Q-Mol API: compute molecular descriptors, run batch jobs, manage your subscription via in-app purchases, and view results offline.

## What's here

```
mobile/
  pubspec.yaml                    # Dependencies
  analysis_options.yaml           # Dart lints
  lib/
    main.dart                     # Entry point
    app.dart                      # MaterialApp with dark/light themes
    router.dart                   # GoRouter navigation
    models/                       # Freezed + json_serializable models
      api_key.dart
      compute_result.dart
      job.dart
      property.dart
      molecule.dart
    providers/                    # Riverpod state management
      auth_provider.dart
      api_provider.dart
      compute_provider.dart
      jobs_provider.dart
    screens/
      splash_screen.dart
      login_screen.dart
      home_screen.dart
      compute_screen.dart
      batch_screen.dart
      jobs_screen.dart
      results_screen.dart
      molecule_detail_screen.dart
      settings_screen.dart
    widgets/
      property_card.dart
      molecule_card.dart
      smiles_input.dart
      job_list_item.dart
      loading_indicator.dart
    services/
      api_service.dart            # Dio client with interceptors, retries, offline queue
      storage_service.dart        # flutter_secure_storage + SharedPreferences
      notification_service.dart   # Local notifications for job completion
    utils/
      constants.dart
      validators.dart
  android/
    app/build.gradle              # minSdk 21, proguard
    app/proguard-rules.pro
    app/src/main/AndroidManifest.xml
  ios/Runner/Info.plist           # Camera + photo permissions
```

## Prerequisites

- Flutter SDK 3.19.0 or higher
- Dart SDK 3.3.0 or higher
- Android SDK (API 21+, compileSdk 35)
- Xcode 15+ (for iOS builds)

## Generate Platform Scaffolding

Run this once to create `android/`, `ios/`, gradle wrappers, etc. Then copy this kit's `lib/` + `pubspec.yaml` on top:

```bash
flutter create --org app.qmol --project-name qmol qmol_app
cp -r mobile/lib mobile/pubspec.yaml mobile/analysis_options.yaml qmol_app/
cd qmol_app
flutter pub get
```

## Configure API Base URL

Set the `QMOL_API` Dart define at build time:

```bash
# Production
flutter build apk --dart-define=QMOL_API=https://api.qmol.app/v1

# Local development
flutter run --dart-define=QMOL_API=http://localhost:8000/v1
```

Or edit `lib/utils/constants.dart` directly:

```dart
static const String baseUrl = 'https://api.qmol.app/v1';
```

## Android Build

### 1. Ensure minSdkVersion 21

In `android/app/build.gradle`:

```gradle
android {
    defaultConfig {
        applicationId = "app.qmol.android"
        minSdk = 21
        targetSdk = 35
        compileSdk = 35
    }
}
```

### 2. ProGuard (release builds)

A `proguard-rules.pro` is included. Ensure it's referenced in `build.gradle`:

```gradle
android {
    buildTypes {
        release {
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
        }
    }
}
```

### 3. Manifest permissions

Apply `android/app/src/main/AndroidManifest.xml` additions (INTERNET, queries, etc.).

### 4. Build release

```bash
flutter build appbundle --dart-define=QMOL_API=https://api.qmol.app/v1
# -> build/app/outputs/bundle/release/app-release.aab
```

## iOS Build

### 1. Install CocoaPods dependencies

```bash
cd ios
pod install
cd ..
```

### 2. Update Info.plist

Ensure `ios/Runner/Info.plist` includes camera and photo library permission descriptions:

```xml
<key>NSCameraUsageDescription</key>
<string>Q-Mol needs camera access to capture SMILES from images via OCR.</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>Q-Mol needs photo library access to select images for SMILES extraction.</string>
```

### 3. Build

```bash
flutter build ios --release --dart-define=QMOL_API=https://api.qmol.app/v1
```

## Run Tests

```bash
flutter test
```

## In-App Purchase Setup

### Google Play (Android)

1. Create subscription products in Play Console:
   - `qmol_research_monthly`
   - `qmol_commercial_monthly`

2. Set backend environment variables:
   ```
   ANDROID_PACKAGE_NAME=app.qmol.android
   GOOGLE_PLAY_SERVICE_ACCOUNT_JSON={...}
   PLAY_PRODUCT_RESEARCH=qmol_research_monthly
   PLAY_PRODUCT_COMMERCIAL=qmol_commercial_monthly
   ```

3. Test with a license tester account before release.

### App Store (iOS)

1. Create subscription products in App Store Connect.
2. Configure StoreKit configuration file for sandbox testing.
3. Match product IDs with backend `PLAY_PRODUCT_*` env vars (or add iOS-specific mapping).

## Code Generation

Models use `freezed` and `json_serializable`. Regenerate after model changes:

```bash
cd mobile
flutter pub run build_runner build --delete-conflicting-outputs
```

## QA Checklist Before Submitting

- [ ] `flutter analyze` clean
- [ ] `flutter test` passes
- [ ] Runs on Android device/emulator; free-key signup works
- [ ] Descriptors return for a valid SMILES
- [ ] License-tester account can complete a test subscription
- [ ] Account → Delete works and signs out
- [ ] Offline mode: queued requests sync when reconnecting
- [ ] Privacy/Terms links open
- [ ] Accessibility: TalkBack/VoiceOver labels present
- [ ] Cold start < 3s on mid-range device
- [ ] 60fps animations on scroll and transitions

## Features

- **Compute**: Single SMILES → full molecular descriptors (MW, logP, TPSA, QED, HBD, HBA, Lipinski, PAINS, ML predictions)
- **Batch**: Multi-line SMILES or CSV upload → async Celery job
- **Jobs**: Real-time progress polling, cancel, download results, local notifications
- **Offline**: POST requests queued when offline, synced on reconnect
- **History**: Local storage of last computations
- **3D Viewer**: Launch external web viewer with 3Dmol.js
- **Settings**: Theme toggle, API key management, clear history, about
- **Accessibility**: Screen reader labels, semantic widgets, high contrast
