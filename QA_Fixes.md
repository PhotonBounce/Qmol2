# Q-Mol QA — Fix Code for Issues Found

All fixes below are derived from the live-site behavior observed during QA. They assume a typical Python backend (Flask/FastAPI) and the inline HTML/JS frontend already deployed at `http://photon-bounce.com/qmol`.

---

## 1. HIGH — `/api/download` returns `500` on invalid token

### Problem
`GET /api/download?token=invalidtoken` → `500` server error. It should return `401` or `403`.

### Fix (Backend — Flask example)

```python
from flask import Flask, request, jsonify, send_file
import io
import csv

app = Flask(__name__)

@app.route('/api/download')
def download_csv():
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "Missing token"}), 400

    # === FIX: wrap token verification so auth errors don't become 500s ===
    try:
        user = verify_token(token)  # your existing JWT/session check
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 401
    except Exception:
        # If token parsing blows up, still return 401, never 500
        return jsonify({"error": "Invalid token"}), 401

    # ... generate CSV from user's molecules ...
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["smiles", "mw", "logp", "name"])
    for mol in user.molecules:
        writer.writerow([mol.smiles, mol.mw, mol.logp, mol.name])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="molecules.csv"
    )
```

### Verification curl
```bash
# Should return 401, not 500
curl -s -w "\nHTTP:%{http_code}\n" "http://photon-bounce.com/qmol/api/download?token=badtoken"
# Expected: HTTP:401
```

---

## 2. HIGH — `POST /api/listings` ignores all input fields

### Problem
Posting `{"title":"Custom","price":0.01,"currency":"ETH","molecule_ids":[14,15,16]}` returns `{"listing_id":8,"price_usd":99}` with `name:"Untitled"` and `molecule_count:0`.

### Fix (Backend — Flask example)

```python
@app.route('/api/listings', methods=['POST'])
def create_listing():
    if not current_user.is_authenticated:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json() or {}

    # === FIX: read all fields from the request body ===
    title = data.get('title', 'Untitled').strip()
    description = data.get('description', '').strip()
    price = data.get('price', 99)
    currency = data.get('currency', 'USD')
    molecule_ids = data.get('molecule_ids', []) or []

    # Validate molecule_ids belong to current user
    valid_molecules = Molecule.query.filter(
        Molecule.id.in_(molecule_ids),
        Molecule.user_id == current_user.id
    ).all()

    # === FIX: compute molecule_count from actual IDs ===
    molecule_count = len(valid_molecules)

    listing = Listing(
        user_id=current_user.id,
        name=title,                       # was hardcoded "Untitled"
        description=description,
        price_usd=float(price),           # was hardcoded 99
        currency=currency,
        molecule_count=molecule_count,      # was hardcoded 0
        status='active',
        # optionally store the relationship:
        molecules=valid_molecules
    )
    db.session.add(listing)
    db.session.commit()

    return jsonify({
        "success": True,
        "listing_id": listing.id,
        "price_usd": listing.price_usd,
        "name": listing.name,
        "molecule_count": listing.molecule_count
    }), 200
```

### Verification curl
```bash
# 1. Login first to get a session cookie
curl -s -c cookies.txt -X POST http://photon-bounce.com/qmol/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}'

# 2. Create a listing with custom fields
curl -s -b cookies.txt -X POST http://photon-bounce.com/qmol/api/listings \
  -H "Content-Type: application/json" \
  -d '{"title":"Custom QA Dataset","price":0.01,"currency":"ETH","molecule_ids":[14,15,16]}'

# 3. Verify the fields were persisted
curl -s -b cookies.txt -X GET http://photon-bounce.com/qmol/api/listings | python -m json.tool
# Expected: the new listing has name="Custom QA Dataset", price_usd=0.01, molecule_count=3
```

---

## 3. MEDIUM — `buyDataset()` in `marketplace.html` is a stub (no API call)

### Problem
Clicking "Buy with Crypto" only shows an `alert()`. No purchase is recorded on the backend.

### Fix (Frontend — replace `buyDataset` in `marketplace.html`)

```javascript
// OLD (stub)
function buyDataset(id, price) {
  const email = prompt('Enter your email for delivery:');
  if (!email) return;
  const txHash = prompt('Enter your crypto transaction hash (0x...):');
  if (!txHash) return;
  alert('Payment submitted for review. We will verify the transaction and email your CSV within 24 hours.');
}

// NEW (wired to backend)
async function buyDataset(id, price) {
  const email = prompt('Enter your email for delivery:');
  if (!email) return;
  const txHash = prompt('Enter your crypto transaction hash (0x...):');
  if (!txHash) return;

  try {
    const r = await fetch(API_URL + '/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ listing_id: id, price: price, email: email, tx_hash: txHash })
    });
    const data = await r.json();
    if (data.success) {
      alert('Purchase recorded! Order #' + data.order_id + '. We will email your CSV within 24 hours.');
    } else {
      alert('Purchase failed: ' + (data.error || 'Unknown error'));
    }
  } catch (e) {
    alert('Network error: ' + e.message);
  }
}
```

### Backend endpoint to add

```python
@app.route('/api/orders', methods=['POST'])
def create_order():
    if not current_user.is_authenticated:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json() or {}
    listing_id = data.get('listing_id')
    email = data.get('email', '').strip()
    tx_hash = data.get('tx_hash', '').strip()

    if not listing_id or not email or not tx_hash:
        return jsonify({"error": "Missing required fields"}), 400

    listing = Listing.query.get(listing_id)
    if not listing or listing.status != 'active':
        return jsonify({"error": "Listing not found or not active"}), 404

    order = Order(
        buyer_id=current_user.id,
        listing_id=listing_id,
        buyer_email=email,
        tx_hash=tx_hash,
        status='pending_verification'
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({"success": True, "order_id": order.id}), 200
```

---

## 4. MEDIUM — `sendContact()` in `marketplace.html` is a stub (no API call)

### Problem
Clicking "Send Inquiry" only updates the DOM with a fake success message. Nothing is sent to the backend.

### Fix (Frontend — replace `sendContact` in `marketplace.html`)

```javascript
// OLD (stub)
function sendContact() {
  const email = document.getElementById('contactEmail').value;
  const type = document.getElementById('contactType').value;
  const details = document.getElementById('contactDetails').value;
  if (!email || !details) { document.getElementById('contactResult').innerHTML = '<span style="color:#f87171">Please fill in email and details.</span>'; return; }
  document.getElementById('contactResult').innerHTML = '<span style="color:#4ade80">Inquiry sent! We will contact you at ' + email + ' within 24 hours.</span>';
}

// NEW (wired to backend)
async function sendContact() {
  const email = document.getElementById('contactEmail').value.trim();
  const type = document.getElementById('contactType').value;
  const details = document.getElementById('contactDetails').value.trim();
  if (!email || !details) {
    document.getElementById('contactResult').innerHTML = '<span style="color:#f87171">Please fill in email and details.</span>';
    return;
  }

  try {
    const r = await fetch(API_URL + '/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email: email, type: type, details: details })
    });
    const data = await r.json();
    if (data.success) {
      document.getElementById('contactResult').innerHTML = '<span style="color:#4ade80">Inquiry sent! We will contact you at ' + email + ' within 24 hours.</span>';
    } else {
      document.getElementById('contactResult').innerHTML = '<span style="color:#f87171">Failed: ' + (data.error || 'Unknown error') + '</span>';
    }
  } catch (e) {
    document.getElementById('contactResult').innerHTML = '<span style="color:#f87171">Network error: ' + e.message + '</span>';
  }
}
```

### Backend endpoint to add

```python
@app.route('/api/contact', methods=['POST'])
def contact_inquiry():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    inquiry_type = data.get('type', 'custom')
    details = data.get('details', '').strip()

    if not email or not details:
        return jsonify({"error": "Email and details are required"}), 400

    inquiry = Inquiry(
        email=email,
        inquiry_type=inquiry_type,
        details=details,
        user_id=current_user.id if current_user.is_authenticated else None
    )
    db.session.add(inquiry)
    db.session.commit()

    # Optional: send notification email to admin here
    return jsonify({"success": True, "inquiry_id": inquiry.id}), 200
```

---

## 5. MEDIUM — `fetchPubChem()` in `miner.html` uses non-standard `fetch` option

### Problem
`await fetch(..., { timeout: 15000 })` — the `fetch` API does not support a `timeout` option. The option is silently ignored.

### Fix (Frontend — replace `fetchPubChem` in `miner.html`)

```javascript
// OLD
async function fetchPubChem(cid) {
  try {
    const r = await fetch(`${PUBCHEM}/${cid}/property/.../JSON`, { timeout: 15000 });
    ...
  }
}

// NEW — use AbortController for real timeout
async function fetchPubChem(cid) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);
    const r = await fetch(
      `${PUBCHEM}/${cid}/property/IsomericSMILES,MolecularWeight,XLogP,TPSA,HydrogenBondDonorCount,HydrogenBondAcceptorCount,RotatableBondCount,IUPACName/JSON`,
      { signal: controller.signal }
    );
    clearTimeout(timeoutId);
    ...
  } catch (e) {
    if (e.name === 'AbortError') {
      log('PubChem timeout for CID ' + cid, 'err');
    } else {
      log('PubChem fetch failed: ' + e.message, 'err');
    }
  }
}
```

---

## 6. LOW — `setAuthTab()` relies on implicit global `event`

### Problem
`event.target.classList.add('active')` works in some browsers but uses the deprecated implicit global `event`. Modern browsers may deprecate this.

### Fix (Frontend — update in `miner.html`)

```javascript
// OLD
function setAuthTab(tab) {
  AUTH_TAB = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  ...
}

// NEW — pass event explicitly
function setAuthTab(tab, evt) {
  AUTH_TAB = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  evt.target.classList.add('active');
  document.getElementById('authForm').classList.toggle('hidden', tab === 'metamask');
  document.getElementById('metamaskBtn').classList.toggle('hidden', tab !== 'metamask');
}
```

Also update the HTML inline handlers:
```html
<!-- OLD -->
<button class="tab-btn active" onclick="setAuthTab('login')">Login</button>

<!-- NEW -->
<button class="tab-btn active" onclick="setAuthTab('login', event)">Login</button>
<button class="tab-btn" onclick="setAuthTab('register', event)">Register</button>
<button class="tab-btn" onclick="setAuthTab('metamask', event)">MetaMask</button>
```

---

## 7. LOW — Missing `favicon.ico`

### Problem
`GET /favicon.ico` → `404`.

### Fix
Add a favicon file to the static root, or add a `<link>` in the `<head>` of every HTML page:

```html
<link rel="icon" type="image/png" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==">
```

Or simply place a real `favicon.ico` in the static folder served at `/`.

---

## Quick Verification Checklist (curl commands)

Run these after deploying fixes to confirm resolution:

```bash
# 1. Verify register/login/logout cycle
curl -s -X POST http://photon-bounce.com/qmol/api/register -H "Content-Type: application/json" -d '{"email":"verify_123@test.com","password":"Pass123!","name":"Verify"}' | python -m json.tool
curl -s -c cookies.txt -X POST http://photon-bounce.com/qmol/api/login -H "Content-Type: application/json" -d '{"email":"verify_123@test.com","password":"Pass123!"}' | python -m json.tool
curl -s -b cookies.txt -X GET http://photon-bounce.com/qmol/api/me | python -m json.tool
curl -s -b cookies.txt -X POST http://photon-bounce.com/qmol/api/logout | python -m json.tool
curl -s -b cookies.txt -X GET http://photon-bounce.com/qmol/api/me  # expect 401

# 2. Verify download error handling
curl -s -w "\nHTTP:%{http_code}\n" "http://photon-bounce.com/qmol/api/download?token=badtoken"
# expect HTTP:401, not 500

# 3. Verify listing fields are persisted
curl -s -b cookies.txt -X POST http://photon-bounce.com/qmol/api/listings -H "Content-Type: application/json" -d '{"title":"Fixed","price":0.01,"currency":"ETH","molecule_ids":[]}' | python -m json.tool
curl -s -b cookies.txt -X GET http://photon-bounce.com/qmol/api/listings | python -m json.tool
# expect name="Fixed", price_usd=0.01
```
