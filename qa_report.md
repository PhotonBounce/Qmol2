## QA Report: Cycle 3: End-to-End Integration + Visual/HTML Check

**Test Date:** 2026-07-03T13:55:04-0700 (PDT)  
**Target URL:** http://photon-bounce.com/qmol  
**API Base:** http://photon-bounce.com/qmol/api  
**QA Engineer:** Q-Mol SaaS QA Cycle 3

---

### Tests Run

#### Cycle 1: Auth + Miner + API Backend
1. `POST /api/register` with new random email `qatester_20260703135504@example.com`
2. `POST /api/login` with registered credentials
3. `GET /api/me` with session cookie
4. `POST /api/mine` with 3 sample molecules (Ethanol, Aspirin, Caffeine)
5. `GET /api/stats` to verify molecule storage
6. `POST /api/logout`
7. Fetch `miner.html` and verify script tags, login modal, controls
8. Verify all API endpoints return proper JSON

#### Cycle 2: Marketplace + Listings + Buy Flow
9. `GET /api/listings` (unauthenticated) — returns active listings + wallet
10. `POST /api/listings` (authenticated) — create listing with 3 molecules
11. Verify listing appears on `marketplace.html` via JavaScript fetch
12. `GET /api/listings` — confirm listing is visible in API
13. Check `marketplace.html` for "Contact to Purchase" and "Buy with Crypto" buttons
14. Check `marketplace.html` for 404 errors in page assets

#### Cycle 3: End-to-End Integration + Visual/HTML
15. Full E2E flow: register → login → mine 3 molecules → check stats → create dataset → create listing → verify listing visible → logout
16. Full E2E consistency test with *second* random user to verify repeatability
17. HTML well-formedness check on all 4 pages (index, miner, marketplace, download)
18. Verify `index.html` links to `miner.html`, `marketplace.html`, `download.html`
19. Check `miner.html` has login modal, mining controls, stats display, hash rate, progress bar, log box
20. Check CSS loads (inline `<style>` tags present, no external 404s)
21. Verify no unclosed tags, broken quotes in JS, missing closing tags
22. Test `/api/download` with invalid token
23. Verify unauthenticated access to protected endpoints returns 401
24. Check for missing static assets (`demo_output.png`, `_onepager_preview.png`, `qmol-windows.zip`, `qmol.apk`)

---

### Results

| Test | Status | Details |
|------|--------|---------|
| 1. Register | **PASS** | HTTP 200, JSON response with `user_id`, `email`, `eth_address` |
| 2. Login | **PASS** | HTTP 200, JSON `{"success":true,"user_id":2}` |
| 3. /api/me (authed) | **PASS** | HTTP 200, returns user object with `total_molecules`, `total_earnings` |
| 4. /api/mine (3 molecules) | **PASS** | All 3 returned 200 with `molecule_id` (1, 2, 3) |
| 5. /api/stats | **PASS** | HTTP 200, `total_molecules:3`, `unique:3`, `last_7_days:3` |
| 6. /api/logout | **PASS** | HTTP 200, `{"success":true}` |
| 7. miner.html loads | **PASS** | HTTP 200, 1 `<script>` block, all required UI elements present |
| 8. API JSON validity | **PASS** | All endpoints return `Content-Type: application/json` |
| 9. GET /api/listings | **PASS** | HTTP 200, returns `listings` array + wallet address |
| 10. POST /api/listings | **PASS** | HTTP 200, `listing_id:1`, `price_usd:99` |
| 11. Listing on marketplace | **PASS** | Listing appears in `loadDatasets()` JS fetch + rendered in DOM |
| 12. Listings API consistency | **PASS** | New listing visible in GET /api/listings response |
| 13. Marketplace buttons | **PASS** | "Buy with Crypto" and "Contact to Purchase" buttons present in HTML/JS |
| 14. Marketplace 404s | **PASS** | No 404s in page HTML; all links valid |
| 15. Full E2E flow (user 1) | **PASS** | All steps completed successfully |
| 16. E2E consistency (user 2) | **PASS** | User `consistency_178311233530@example.com`: register→login→mine×3→stats→dataset→listing→verify→logout all 200 |
| 17. HTML well-formedness | **PASS** | Zero parser errors on all 4 pages; zero unclosed tags |
| 18. index.html links | **PASS** | Links to `miner.html`, `marketplace.html`, `download.html` confirmed |
| 19. miner.html UI elements | **PASS** | loginModal, btnMine/btnStop, dispTotal/dispUnique, hashRateDisplay, progFill, logBox all present |
| 20. CSS loading | **PASS** | All pages have inline `<style>` blocks; no external CSS 404s |
| 21. No broken JS tags | **PASS** | All `<script>` tags properly closed; all pages have `</body></html>` |
| 22. /api/download invalid token | **PASS** | Returns HTTP 400 `{"error":"Missing token"}` (proper rejection) |
| 23. Unauth access control | **PASS** | POST /mine=401, /me=401, /stats=401, /datasets=401; GET /listings=200 (public endpoint) |
| 24. Static assets | **PASS** | `demo_output.png`=200, `_onepager_preview.png`=200, `qmol-windows.zip`=200, `qmol.apk`=200 |

---

### Issues Found

#### 1. [MEDIUM] `fetch()` timeout option not supported in standard Fetch API
**Location:** `miner.html`, line 230 (`fetchPubChem` function)  
**Reproduction:**
```javascript
const r = await fetch(`${PUBCHEM}/${cid}/property/.../JSON`, { timeout: 15000 });
```
**Impact:** The `timeout` property is **not** part of the standard `fetch()` API. In strict browsers, this will be silently ignored; in some environments it may throw a `TypeError`. The PubChem fetch will hang indefinitely if the network stalls.  
**Fix:** Replace with `AbortController`:
```javascript
const controller = new AbortController();
const timer = setTimeout(() => controller.abort(), 15000);
try {
  const r = await fetch(`${PUBCHEM}/${cid}/property/.../JSON`, { signal: controller.signal });
  clearTimeout(timer);
  // ...
} catch (e) {
  clearTimeout(timer);
  return null;
}
```

#### 2. [LOW] Marketplace listings show `molecule_count: 0` for all user-created listings
**Location:** API `/api/listings` and `/api/listings` (POST)  
**Reproduction:**
```bash
curl -s http://photon-bounce.com/qmol/api/listings
```
All listings (including the one created in this test) show `"molecule_count":0` even though molecules were mined and associated.  
**Impact:** The marketplace UI displays "0 molecules" for user-created listings, which may confuse buyers. The seed datasets have hardcoded `count` values, but backend listings do not reflect actual molecule counts.  
**Fix:** The backend listing creation logic should populate `molecule_count` from the associated dataset or molecule IDs provided in the POST body.

#### 3. [LOW] Listing `name` field is ignored; always saved as "Untitled"
**Location:** API `/api/listings` (POST)  
**Reproduction:**
```bash
curl -s -b cookies.txt -X POST http://photon-bounce.com/qmol/api/listings \
  -H "Content-Type: application/json" \
  -d '{"title":"My Custom Title","description":"...","price":0.001,"currency":"ETH","molecule_ids":[1,2,3]}'
```
Response shows `listing_id:9` but GET `/api/listings` returns `"name":"Untitled"`.  
**Impact:** The `title` field from POST is not persisted; `name` is always "Untitled". This makes listings hard to distinguish.  
**Fix:** Map the `title` JSON field to the `name` DB column in the backend POST handler, or accept `name` as an alternative key.

#### 4. [INFO] `/api/download` requires a token; no documented token generation path
**Location:** `/api/download` endpoint  
**Reproduction:**
```bash
curl -s "http://photon-bounce.com/qmol/api/download?token=invalid"
# → 400 {"error":"Missing token"}
```
Neither dataset creation nor listing creation returns a download token. The endpoint appears to require a purchase/payment confirmation token.  
**Impact:** QA cannot verify CSV payload without a purchase flow. The endpoint correctly rejects invalid tokens, which is acceptable behavior.  
**Fix:** Document the token generation mechanism, or add a `dataset_id` parameter as a fallback for owner downloads.

---

### Overall Cycle Status

**PASS**

All critical paths (registration, authentication, mining, stats, dataset creation, listing creation, marketplace visibility, logout) executed successfully across two independent user accounts. All HTML pages are well-formed, all required UI elements are present, all static assets resolve, and authentication gates correctly reject unauthorized requests. The 4 issues found are all non-blocking: 1 medium-severity JavaScript compatibility issue, 2 low-severity data-display bugs, and 1 informational gap around download tokens. No regressions or blocking defects were detected.
