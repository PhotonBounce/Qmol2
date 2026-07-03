## QA Report: Cycle 2: Marketplace + Listings + Buy Flow
**Date:** 2026-07-03 13:55 PDT  
**Target:** http://photon-bounce.com/qmol  
**API Base:** http://photon-bounce.com/qmol/api  
**Tester:** QA Engineer (Automated + Manual Verification)

---

### Tests Run
1. **[C1]** POST /api/register — Register with new random email
2. **[C1]** POST /api/login — Login with registered email
3. **[C1]** GET /api/me — Verify session returns user object
4. **[C1]** POST /api/mine — Mine 3 sample molecules (Ethanol, Aspirin, Caffeine)
5. **[C1]** GET /api/stats — Verify molecule stats updated
6. **[C1]** POST /api/logout — Verify session termination
7. **[C1]** GET /miner.html — Verify page loads, scripts present, tags balanced
8. **[C1]** API Content-Type check — All endpoints return `application/json`
9. **[C2]** GET /api/listings — Verify active listings returned
10. **[C2]** POST /api/listings — Create listing with authenticated session
11. **[C2]** Verify listing on marketplace.html — Dynamically fetched and rendered
12. **[C2]** marketplace.html render check — Grid and cards display correctly
13. **[C2]** marketplace.html asset check — CSS, JS, images all return 200
14. **[C2]** Purchase button existence — "Buy with Crypto" and "Contact to Purchase"
15. **[C2]** 404 reference check — No broken references in page HTML
16. **[C3]** Full E2E flow — Register → Login → Mine 3 → Stats → List → Verify visible
17. **[C3]** HTML well-formedness — Balanced tags across all HTML pages
18. **[C3]** index.html navigation — Links to miner.html, marketplace.html, download.html
19. **[C3]** miner.html UI components — Login form, mining controls, stats display
20. **[C3]** CSS loading — External stylesheets load, minimal inline styles
21. **[C3]** JS syntax check — No unclosed quotes, balanced brackets
22. **[C3]** GET /api/download — Endpoint behavior with/without token

---

### Results

| Test | Status | Details |
|------|--------|---------|
| [C1] POST /api/register | PASS | Returns 200, `{"success":true,"user_id":N,"email":"..."}` |
| [C1] POST /api/login | PASS | Returns 200, `{"success":true,"user_id":N}`; sets `PHPSESSID` cookie |
| [C1] GET /api/me | PASS | Returns 200, nested structure `{"user":{"id":N,"email":"...",...}}` |
| [C1] POST /api/mine (×3) | PASS | All 3 molecules returned 200, `{"success":true,"molecule_id":N}` |
| [C1] GET /api/stats | PASS | Returns `{"total_molecules":N,"unique":N,"lipinski_pass":N,...}` |
| [C1] POST /api/logout | PASS | Returns 200, `{"success":true}` |
| [C1] GET /miner.html | PASS | 200 OK; 1 inline script; balanced `<div>` / `<script>` tags |
| [C1] API Content-Type | PASS | All endpoints return `Content-Type: application/json` |
| [C2] GET /api/listings | PASS | Returns 200, `{"listings":[...],"wallet":"0x..."}` (8 listings) |
| [C2] POST /api/listings | PARTIAL | Returns 200, creates listing, but **ignores `title`/`price`** fields |
| [C2] Listing on marketplace.html | PASS | JS fetches `/api/listings` and renders backend cards dynamically |
| [C2] marketplace.html render | PASS | Grid layout renders; seed + backend datasets both displayed |
| [C2] marketplace.html assets | PASS | All linked CSS/JS accessible; no 404s |
| [C2] Purchase buttons | PASS | "Buy with Crypto" and "Contact to Purchase" generated via JS |
| [C2] 404 reference check | PASS | No 404 text or error references in static HTML |
| [C3] Full E2E flow | PASS | Complete flow executed successfully; listing visible on marketplace |
| [C3] HTML well-formedness | PASS | index.html, miner.html, marketplace.html, download.html all balanced |
| [C3] index.html navigation | PASS | Contains links to `miner.html`, `marketplace.html`, `download.html` |
| [C3] miner.html UI | PASS | Login modal inputs, mine form, stats panel all present |
| [C3] CSS loading | PASS | All stylesheets load; 7 inline style blocks (acceptable) |
| [C3] JS syntax check | PASS | No unclosed quotes or brackets in inline scripts |
| [C3] GET /api/download | PARTIAL | Returns 400 `{"error":"Missing token"}` when no token; **500** on invalid token; valid-token CSV **unverified** |

---

### Issues Found

🔴 **[HIGH] Listing API field naming mismatch — `title` and `price` ignored**
- **Description:** POST `/api/listings` silently ignores the `title` and `price` fields. It requires `name` and `price_usd` instead. The listing is always created with `name: "Untitled"` unless `name` is explicitly provided. The `price` field is ignored entirely; without `price_usd` the listing defaults to `price_usd: 99`.
- **Reproduction:**
  ```bash
  curl -X POST http://photon-bounce.com/qmol/api/listings \
    -H "Content-Type: application/json" \
    -b "PHPSESSID=..." \
    -d '{"title":"My Title","description":"My Desc","price":99.99,"molecule_id":1}'
  # Returns: {"success":true,"listing_id":N,"price_usd":99}
  # Then GET /api/listings shows: name:"Untitled", price_usd:99
  ```
  ```bash
  curl -X POST http://photon-bounce.com/qmol/api/listings \
    -H "Content-Type: application/json" \
    -b "PHPSESSID=..." \
    -d '{"name":"My Title","description":"My Desc","price_usd":199,"molecule_id":1}'
  # Returns: {"success":true,"listing_id":N,"price_usd":199}
  # Then GET /api/listings shows: name:"My Title", price_usd:199
  ```
- **Fix:** Update the backend to accept `title` as an alias for `name` (or vice versa) and `price` as an alias for `price_usd`, OR update API documentation to clearly specify required fields.

🔴 **[HIGH] Molecule-to-listing linkage completely broken**
- **Description:** Every listing returns `dataset_id: 0` and `molecule_count: 0` regardless of how many `molecule_id`s were provided during creation. The `molecule_id` sent in POST is not persisted into the dataset relationship.
- **Reproduction:**
  ```bash
  curl -X POST http://photon-bounce.com/qmol/api/listings \
    -b "PHPSESSID=..." \
    -d '{"name":"Linked Molecule","price_usd":99,"molecule_id":13}'
  curl http://photon-bounce.com/qmol/api/listings
  # Response shows: molecule_count:0, dataset_id:0 for every listing
  ```
- **Fix:** In the PHP backend, ensure the POST handler reads `molecule_id` (or `molecule_ids`), creates a `dataset` record linking those molecules, and stores the `dataset_id` in the `listings` table. Update the GET handler to JOIN the datasets table and return the real `molecule_count`.

🟡 **[MEDIUM] Buy flow is non-functional — no API call, no transaction verification**
- **Description:** The "Buy with Crypto" button calls `buyDataset(id, price)` which only opens `prompt()` dialogs for email and transaction hash, then calls `alert()`. No HTTP request is made. The purchase is never recorded in the backend.
- **Reproduction:**
  1. Open http://photon-bounce.com/qmol/marketplace.html
  2. Click "Buy with Crypto" on any dataset
  3. Enter email and fake txHash → alert says "Payment submitted for review"
  4. Check backend — no new record in `listings` sold/buyer fields
- **Fix:** Implement `buyDataset()` to POST to a new `/api/purchase` endpoint:
  ```javascript
  async function buyDataset(id, price) {
    const email = prompt('Enter your email for delivery:');
    if (!email) return;
    const txHash = prompt('Enter your crypto transaction hash:');
    if (!txHash) return;
    const res = await fetch(`${API_URL}/purchase`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({listing_id:id, email, tx_hash:txHash})
    });
    const data = await res.json();
    alert(data.message || 'Purchase recorded.');
  }
  ```
  Then create a PHP endpoint that validates the txHash, marks the listing as sold, and stores `buyer_email` and `tx_hash`.

🟡 **[MEDIUM] Download endpoint returns 500 on invalid token instead of 401**
- **Description:** `/api/download` correctly returns 400 `{"error":"Missing token"}` when no token is provided. However, when an invalid/non-existent token is supplied, it returns HTTP 500 with an empty body instead of a proper 401/403 JSON error.
- **Reproduction:**
  ```bash
  curl -w "\n%{http_code}" "http://photon-bounce.com/qmol/api/download?token=invalid"
  # Returns: (empty body) + 500
  ```
- **Fix:** Wrap token validation in a try/catch or explicit check. Return `401 Unauthorized` with `{"error":"Invalid token"}` instead of letting an unhandled exception bubble up.

🟢 **[LOW] Backend listings show "Preview not available" because molecule array is empty**
- **Description:** In `marketplace.html`, the JS maps backend listings with `molecules: []` hardcoded. Since `molecule_count` is also 0 (due to the linkage bug), every backend listing shows the fallback preview message instead of molecule data.
- **Reproduction:** Create any listing, open marketplace, and see the preview card says "Preview not available."
- **Fix:** After fixing the molecule linkage, update the frontend to either (a) embed preview molecules in the `/api/listings` response, or (b) fetch `/api/listings/{id}/molecules` on card hover/expand.

🟢 **[LOW] Cannot verify CSV download with valid token — no token generation path documented**
- **Description:** No API endpoint (register, login, stats, listings) returns a `download_token`. Without a documented way to generate a valid token, the CSV download flow could not be fully end-to-end verified.
- **Reproduction:** Review all API responses — none contain a `token` or `download_token` field.
- **Fix:** Either (a) add a `download_token` to the login/session response, (b) create `/api/datasets/{id}/token` endpoint, or (c) document how tokens are generated.

---

### Overall Cycle Status

**PASS WITH WARNINGS ⚠️**

- **Total Tests:** 22
- **Passed:** 19
- **Partial / Needs Attention:** 3 (POST listing field mapping, download token verification, buy flow functionality)
- **High Severity Issues:** 2 (Molecule linkage broken; API field naming mismatch)
- **Medium Severity Issues:** 2 (Buy flow fake; Download 500 on bad token)
- **Low Severity Issues:** 2 (Preview missing; Token generation undocumented)

**Bottom line:** The core infrastructure (auth, mining, stats, HTML rendering, CSS, E2E registration flow) is solid. However, the **marketplace buy flow and listing molecule linkage are broken in production** and need immediate backend fixes before the marketplace can be considered functional.
