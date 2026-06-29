# Q-Mol Google Play Store Submission Guide

> **Last updated:** 2026-06-29  
> **Application ID:** `app.qmol.android`  
> **Version:** 2.0.0+1

---

## Step 1: Generate Your Signing Key (CRITICAL — DO THIS FIRST)

The signing key is **PERMANENT**. Once you upload an app to Play Store with a key, that key cannot be changed. If you lose it, you cannot update your app.

### Option A: Generate a new keystore (recommended for new apps)

Open a terminal and run:

```bash
# Navigate to the mobile/android/app directory
cd mobile/android/app

# Generate the keystore
keytool -genkey -v -keystore qmol-release.keystore -alias qmol -keyalg RSA -keysize 2048 -validity 10000
```

When prompted, enter:

| Prompt | Recommended Value |
|--------|-------------------|
| **Keystore password** | Choose a strong password (save it in a password manager!) |
| **Key password** | Can be the same as keystore password |
| **First and Last Name** | Your name |
| **Organizational Unit** | Q-Mol |
| **Organization** | PhotonBounce |
| **City/Locality** | Your city |
| **State/Province** | Your state |
| **Country Code** | US (or your country code) |
| **Confirm** | yes |

**IMPORTANT:** Back up `qmol-release.keystore` in a secure location (password manager, encrypted USB drive, cloud storage). This file is your app's identity. Without it, you cannot update Q-Mol on Play Store.

### Option B: Use Google Play App Signing (recommended for Play Store)

Google Play App Signing is the modern approach. Google manages your app signing key while you keep your upload key.

1. Generate an upload key (same command as above, but name it `qmol-upload.keystore`)
2. In Play Console, enable **Google Play App Signing**
3. Google will generate and safeguard the app signing key
4. You use your upload key to sign AAB files before uploading

This is safer because if you lose your upload key, you can contact Google to reset it.

---

## Step 2: Configure Signing in build.gradle

The `build.gradle` is already configured to read from `key.properties`. Here's what it looks like:

```gradle
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    // ... existing config ...

    signingConfigs {
        release {
            keyAlias keystoreProperties['keyAlias'] ?: System.getenv("QMOL_KEY_ALIAS") ?: 'qmol'
            keyPassword keystoreProperties['keyPassword'] ?: System.getenv("QMOL_KEY_PASSWORD") ?: 'qmol123'
            storeFile keystoreProperties['storeFile'] ? file(keystoreProperties['storeFile']) : file(System.getenv("QMOL_KEYSTORE_PATH") ?: 'qmol.keystore')
            storePassword keystoreProperties['storePassword'] ?: System.getenv("QMOL_STORE_PASSWORD") ?: 'qmol123'
        }
    }

    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```

Create `mobile/android/key.properties` (template already provided):

```properties
storePassword=YOUR_STORE_PASSWORD
keyPassword=YOUR_KEY_PASSWORD
keyAlias=qmol
storeFile=app/qmol-release.keystore
```

**NEVER commit `key.properties` or `.keystore` to git!** They are already in `.gitignore`.

---

## Step 3: Build Android App Bundle (AAB)

```bash
# Navigate to mobile directory
cd mobile

# Get Flutter dependencies
flutter pub get

# Build AAB (Android App Bundle — required by Play Store)
flutter build appbundle --release --dart-define=QMOL_API=https://api.qmol.app/v1

# The output is at: build/app/outputs/bundle/release/app-release.aab
```

---

## Step 4: Verify the AAB

```bash
# Check the bundle contents with bundletool
bundletool build-apks \
  --bundle=build/app/outputs/bundle/release/app-release.aab \
  --output=app.apks \
  --ks=android/app/qmol-release.keystore \
  --ks-pass=pass:YOUR_PASSWORD \
  --ks-key-alias=qmol \
  --key-pass=pass:YOUR_PASSWORD

# Install on a connected device for testing
bundletool install-apks --apks=app.apks
```

Alternatively, verify signing with `jarsigner`:

```bash
jarsigner -verify -verbose -certs build/app/outputs/bundle/release/app-release.aab
```

---

## Step 5: Create Play Store Listing

### Required Assets

1. **App Icon**: 512 × 512 PNG, 32-bit with alpha
2. **Feature Graphic**: 1024 × 500 PNG or JPEG
3. **Screenshots**:
   - Phone: 2–8 screenshots, min 320 px, max 3840 px, 16:9 or 9:16 aspect ratio
   - 7-inch tablet: optional, same specs
   - 10-inch tablet: optional, same specs
4. **Short Description**: 80 characters max
5. **Full Description**: 4000 characters max
6. **Privacy Policy URL**: Required (e.g., `https://qmol.app/privacy.html`)

### Store Listing Text (copy-ready)

**Title:** Q-Mol: Molecular Informatics & Drug Discovery

**Short Description:**
Compute molecular properties, predict ADMET, design new molecules, and analyze drug-target interactions from your phone.

**Full Description:**
Q-Mol is a professional molecular informatics platform for chemists, medicinal chemists, and drug discovery researchers.

**Key Features:**
• **Molecular Property Computation** — Calculate 50+ descriptors (MW, logP, TPSA, QED, Lipinski rules, etc.)
• **ADMET Prediction** — Predict solubility, BBB penetration, hERG inhibition, CYP450 metabolism, toxicity
• **Drug-Target Interactions** — Screen molecules against 10+ protein targets (EGFR, HER2, BACE1, etc.)
• **De Novo Design** — Generate novel molecules and optimize leads with AI
• **3D Conformers** — Generate and visualize 3D molecular structures
• **Similarity Search** — Find molecules similar to your query
• **Natural Language** — Query by typing "find molecules like aspirin with good BBB"
• **Batch Processing** — Upload CSV files and process thousands of molecules
• **Offline Mode** — Queue computations when offline, sync when connected
• **Collaboration** — Share molecule collections with your team
• **Export** — Download results in CSV, SDF, PDB, MOL2, FDA format

**Perfect for:**
- Medicinal chemists optimizing lead compounds
- Computational chemists running virtual screens
- Students learning molecular descriptors
- Pharma researchers analyzing ADMET profiles

**Privacy & Security:**
Your data is encrypted in transit and at rest. We never share your molecular structures with third parties.

**Subscription:**
Free tier: 500 molecules/month  
Pro tier: $20/month — unlimited molecules + advanced predictions  
Team tier: Contact us for enterprise pricing

Visit https://qmol.app for more information.

---

## Step 6: Content Rating Questionnaire

In Play Console, complete the content rating:

| Question | Answer |
|----------|--------|
| **Category** | Reference / Education / Science |
| **Violence** | No violence |
| **Sexual Content** | No sexual content |
| **Language** | No profanity |
| **Controlled Substances** | The app is for drug discovery research, not recreational drug use. Rate as "No" or explain it's a professional scientific tool. |
| **Gambling** | No gambling |

---

## Step 7: In-App Purchase Configuration

In Play Console:

1. Go to **Monetization → Products**
2. Create subscription products (these IDs must match the backend):
   - `qmol_research_monthly`
   - `qmol_commercial_monthly`
3. Set grace period: 3 days
4. Set free trial: 7 days
5. Add localized pricing for major markets (US, EU, UK, JP, KR, IN, BR, MX, CA, AU)

**Backend environment variables** (already configured in README):
```
ANDROID_PACKAGE_NAME=app.qmol.android
GOOGLE_PLAY_SERVICE_ACCOUNT_JSON={...}
PLAY_PRODUCT_RESEARCH=qmol_research_monthly
PLAY_PRODUCT_COMMERCIAL=qmol_commercial_monthly
```

---

## Step 8: Testing Tracks

### Internal Testing (1–100 testers)

1. Add your email and team members
2. Upload the AAB to Internal Testing
3. Share the opt-in link with testers
4. Collect feedback for 1–2 weeks

### Closed Testing (up to 2000 testers)

1. Create a Google Group for testers
2. Invite beta users (PhD students, researchers)
3. Collect feedback on:
   - SMILES input validation
   - Offline mode reliability
   - Computation accuracy
   - UI/UX on different devices

### Pre-Launch Report

After uploading to Closed Testing, Google will run:

- Security scan (no malware)
- Stability tests (crash rate < 1%)
- Accessibility checks
- Performance tests (cold start < 5s)

Fix any issues before promoting to Production.

---

## Step 9: Launch to Production

1. Go to **Production** track
2. Upload the AAB
3. Select countries: All countries (or start with US, UK, CA, AU, DE, FR, JP)
4. Set pricing: Free to download, subscriptions for premium features
5. Submit for review (1–3 days)
6. Once approved, your app is live!

---

## Step 10: Post-Launch

- Monitor crash reports in Play Console
- Respond to user reviews within 24 hours
- Update app every 2–4 weeks with bug fixes
- Run A/B tests on store listing graphics
- Use Google Play Console analytics to understand user acquisition

---

## Emergency: Lost Signing Key?

If you used **Google Play App Signing** (recommended):

1. Contact Google Play Support
2. Request a new upload key
3. Upload a new keystore
4. Continue updating normally

If you did **NOT** use Google Play App Signing:

1. You cannot update the app anymore
2. You must publish a new app with a different package name
3. Existing users will not receive updates

**Always use Google Play App Signing!**
