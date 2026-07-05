<?php
/**
 * Q-Mol SaaS API — User Auth, Mining, Datasets, Marketplace, Trials, Payments
 * SQLite backend (works on shared hosting, no MySQL needed)
 */

ini_set('session.gc_maxlifetime', 86400);
ini_set('session.cookie_lifetime', 86400);
ini_set('session.use_only_cookies', 1);

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: ' . ($_SERVER['HTTP_ORIGIN'] ?? '*'));
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');
header('Access-Control-Allow-Credentials: true');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(200); exit; }

session_start();

$DB_FILE = __DIR__ . '/../../data/saas.sqlite';
$DATA_DIR = dirname($DB_FILE);
if (!is_dir($DATA_DIR)) mkdir($DATA_DIR, 0755, true);

$db = new SQLite3($DB_FILE);
$db->busyTimeout(5000);

/* =========================================================
   TABLES
   ========================================================= */

$db->exec("CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password_hash TEXT,
    eth_address TEXT UNIQUE,
    display_name TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    total_molecules INTEGER DEFAULT 0,
    total_earnings REAL DEFAULT 0,
    trial_ends_at TEXT,
    paid_until TEXT,
    is_admin INTEGER DEFAULT 0
)");

$db->exec("CREATE TABLE IF NOT EXISTS molecules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    cid INTEGER,
    smiles TEXT NOT NULL,
    name TEXT,
    mw REAL,
    logp REAL,
    tpsa REAL,
    hbd INTEGER,
    hba INTEGER,
    rotatable INTEGER,
    qed REAL,
    lipinski_pass INTEGER DEFAULT 0,
    veber_pass INTEGER DEFAULT 0,
    pains_hit INTEGER DEFAULT 0,
    source TEXT DEFAULT 'pubchem',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)");

$db->exec("CREATE INDEX IF NOT EXISTS idx_mol_user ON molecules(user_id)");
$db->exec("CREATE INDEX IF NOT EXISTS idx_mol_smiles ON molecules(smiles)");

$db->exec("CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    filter_sql TEXT,
    molecule_count INTEGER DEFAULT 0,
    price_usd REAL DEFAULT 99,
    status TEXT DEFAULT 'draft',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)");

$db->exec("CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    dataset_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    molecule_count INTEGER DEFAULT 0,
    price_usd REAL DEFAULT 99,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sold_at TEXT,
    buyer_email TEXT,
    tx_hash TEXT
)");

$db->exec("CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER,
    buyer_email TEXT,
    tx_hash TEXT,
    amount_usd REAL,
    status TEXT DEFAULT 'pending',
    download_token TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)");

$db->exec("CREATE TABLE IF NOT EXISTS dataset_molecules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    molecule_id INTEGER NOT NULL
)");

/* =========================================================
   MIGRATIONS (add new columns if they don't exist)
   ========================================================= */

// Safely add trial_ends_at column if missing
$hasTrial = false;
$cols = $db->query("PRAGMA table_info(users)");
while ($c = $cols->fetchArray(SQLITE3_ASSOC)) {
    if ($c['name'] === 'trial_ends_at') { $hasTrial = true; break; }
}
if (!$hasTrial) {
    $db->exec("ALTER TABLE users ADD COLUMN trial_ends_at TEXT");
    $db->exec("UPDATE users SET trial_ends_at = datetime(created_at, '+7 days') WHERE trial_ends_at IS NULL");
}

$hasPaid = false;
$cols = $db->query("PRAGMA table_info(users)");
while ($c = $cols->fetchArray(SQLITE3_ASSOC)) {
    if ($c['name'] === 'paid_until') { $hasPaid = true; break; }
}
if (!$hasPaid) {
    $db->exec("ALTER TABLE users ADD COLUMN paid_until TEXT");
}

$hasAdmin = false;
$cols = $db->query("PRAGMA table_info(users)");
while ($c = $cols->fetchArray(SQLITE3_ASSOC)) {
    if ($c['name'] === 'is_admin') { $hasAdmin = true; break; }
}
if (!$hasAdmin) {
    $db->exec("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0");
}

$method = $_SERVER['REQUEST_METHOD'];
$path = $_SERVER['REQUEST_URI'] ?? '';
$path = parse_url($path, PHP_URL_PATH);
$path = str_replace('/qmol/api/index.php', '', $path);
$path = str_replace('/qmol/api/', '', $path);
$path = str_replace('/api/index.php', '', $path);
$path = str_replace('/api/', '', $path);
$path = rtrim($path, '/');

$input = json_decode(file_get_contents('php://input'), true) ?: [];

/* =========================================================
   HELPERS
   ========================================================= */

function authUser($db) {
    if (isset($_SESSION['user_id'])) {
        $stmt = $db->prepare("SELECT id, email, eth_address, display_name, total_molecules, total_earnings, trial_ends_at, paid_until, is_admin, created_at FROM users WHERE id = ?");
        $stmt->bindValue(1, $_SESSION['user_id'], SQLITE3_INTEGER);
        $res = $stmt->execute();
        return $res->fetchArray(SQLITE3_ASSOC) ?: null;
    }
    return null;
}

function jsonOut($data, $code=200) {
    http_response_code($code);
    echo json_encode($data);
    exit;
}

function getTrialStatus($user) {
    $now = new DateTime('now');
    $trialEnds = null;
    $paidUntil = null;

    if (!empty($user['trial_ends_at'])) {
        try { $trialEnds = new DateTime($user['trial_ends_at']); } catch (Exception $e) {}
    }
    if (!empty($user['paid_until'])) {
        try { $paidUntil = new DateTime($user['paid_until']); } catch (Exception $e) {}
    }

    $trialActive = false;
    $daysLeft = 0;
    $expiresAt = null;

    if ($paidUntil && $now <= $paidUntil) {
        $trialActive = true;
        $daysLeft = (int)$now->diff($paidUntil)->format('%r%a');
        if ($daysLeft < 0) $daysLeft = 0;
        $expiresAt = $user['paid_until'];
    } elseif ($trialEnds && $now <= $trialEnds) {
        $trialActive = true;
        $daysLeft = (int)$now->diff($trialEnds)->format('%r%a');
        if ($daysLeft < 0) $daysLeft = 0;
        $expiresAt = $user['trial_ends_at'];
    } else {
        $trialActive = false;
        $daysLeft = 0;
        $expiresAt = $trialEnds ? $user['trial_ends_at'] : null;
    }

    return [
        'active' => $trialActive,
        'days_left' => $daysLeft,
        'expires_at' => $expiresAt,
        'is_paid' => ($paidUntil && $now <= $paidUntil)
    ];
}

function requireTrialOrPaid($db, $user) {
    $status = getTrialStatus($user);
    if (!$status['active']) {
        jsonOut(['error' => 'Trial expired. Please upgrade to continue.', 'trial_status' => $status], 403);
    }
}

/* =========================================================
   AUTH
   ========================================================= */

if ($path === 'register' && $method === 'POST') {
    $email = filter_var($input['email'] ?? '', FILTER_VALIDATE_EMAIL);
    $password = $input['password'] ?? '';
    $ethAddress = $input['eth_address'] ?? null;
    $displayName = $input['display_name'] ?? ($email ? explode('@', $email)[0] : 'User');

    if (!$email && !$ethAddress) {
        jsonOut(['error' => 'Email or MetaMask address required'], 400);
    }

    $pwHash = $password ? password_hash($password, PASSWORD_DEFAULT) : null;
    $trialEnd = date('Y-m-d H:i:s', strtotime('+7 days'));

    $stmt = $db->prepare("INSERT INTO users (email, password_hash, eth_address, display_name, trial_ends_at) VALUES (?, ?, ?, ?, ?)");
    $stmt->bindValue(1, $email, SQLITE3_TEXT);
    $stmt->bindValue(2, $pwHash, SQLITE3_TEXT);
    $stmt->bindValue(3, $ethAddress, SQLITE3_TEXT);
    $stmt->bindValue(4, $displayName, SQLITE3_TEXT);
    $stmt->bindValue(5, $trialEnd, SQLITE3_TEXT);

    if ($stmt->execute()) {
        $userId = $db->lastInsertRowID();
        $_SESSION['user_id'] = $userId;
        jsonOut([
            'success' => true,
            'user_id' => $userId,
            'email' => $email,
            'eth_address' => $ethAddress,
            'trial_ends_at' => $trialEnd,
            'days_left' => 7
        ]);
    } else {
        jsonOut(['error' => 'User already exists'], 409);
    }
}

if ($path === 'login' && $method === 'POST') {
    $email = $input['email'] ?? null;
    $ethAddress = $input['eth_address'] ?? null;

    if ($email) {
        $stmt = $db->prepare("SELECT id, password_hash FROM users WHERE email = ?");
        $stmt->bindValue(1, $email, SQLITE3_TEXT);
        $res = $stmt->execute();
        $user = $res->fetchArray(SQLITE3_ASSOC);
        if (!$user || !password_verify($input['password'] ?? '', $user['password_hash'])) {
            jsonOut(['error' => 'Invalid credentials'], 401);
        }
        $_SESSION['user_id'] = $user['id'];
        jsonOut(['success' => true, 'user_id' => $user['id']]);
    } elseif ($ethAddress) {
        $stmt = $db->prepare("SELECT id FROM users WHERE eth_address = ?");
        $stmt->bindValue(1, $ethAddress, SQLITE3_TEXT);
        $res = $stmt->execute();
        $user = $res->fetchArray(SQLITE3_ASSOC);
        if (!$user) {
            $trialEnd = date('Y-m-d H:i:s', strtotime('+7 days'));
            $stmt = $db->prepare("INSERT INTO users (eth_address, display_name, trial_ends_at) VALUES (?, ?, ?)");
            $stmt->bindValue(1, $ethAddress, SQLITE3_TEXT);
            $stmt->bindValue(2, substr($ethAddress, 0, 6) . '...' . substr($ethAddress, -4), SQLITE3_TEXT);
            $stmt->bindValue(3, $trialEnd, SQLITE3_TEXT);
            $stmt->execute();
            $userId = $db->lastInsertRowID();
            $_SESSION['user_id'] = $userId;
            jsonOut(['success' => true, 'user_id' => $userId, 'new_user' => true, 'trial_ends_at' => $trialEnd]);
        } else {
            $_SESSION['user_id'] = $user['id'];
            jsonOut(['success' => true, 'user_id' => $user['id']]);
        }
    }
    jsonOut(['error' => 'Email or eth_address required'], 400);
}

if ($path === 'me' && $method === 'GET') {
    $user = authUser($db);
    if (!$user) jsonOut(['error' => 'Not logged in'], 401);
    $trial = getTrialStatus($user);
    jsonOut([
        'user' => $user,
        'trial' => $trial
    ]);
}

if ($path === 'logout' && $method === 'POST') {
    session_destroy();
    jsonOut(['success' => true]);
}

/* =========================================================
   TRIAL & PROFILE
   ========================================================= */

if ($path === 'trial-status' && $method === 'GET') {
    $user = authUser($db);
    if (!$user) jsonOut(['error' => 'Not logged in'], 401);
    jsonOut(getTrialStatus($user));
}

if ($path === 'user-profile' && $method === 'GET') {
    $user = authUser($db);
    if (!$user) jsonOut(['error' => 'Not logged in'], 401);

    $total = $db->querySingle("SELECT COUNT(DISTINCT smiles) FROM molecules WHERE user_id = {$user['id']}");
    $lipinski = $db->querySingle("SELECT COUNT(DISTINCT smiles) FROM molecules WHERE user_id = {$user['id']} AND lipinski_pass = 1");
    $qed = $db->querySingle("SELECT COUNT(DISTINCT smiles) FROM molecules WHERE user_id = {$user['id']} AND qed >= 0.7");
    $last7d = $db->querySingle("SELECT COUNT(*) FROM molecules WHERE user_id = {$user['id']} AND created_at >= datetime('now', '-7 days')");
    $datasetCount = $db->querySingle("SELECT COUNT(*) FROM datasets WHERE user_id = {$user['id']}");
    $listingCount = $db->querySingle("SELECT COUNT(*) FROM listings WHERE user_id = {$user['id']}");

    $trial = getTrialStatus($user);

    jsonOut([
        'user_id' => $user['id'],
        'email' => $user['email'],
        'eth_address' => $user['eth_address'],
        'display_name' => $user['display_name'],
        'created_at' => $user['created_at'],
        'total_molecules' => (int)$total,
        'total_earnings' => (float)$user['total_earnings'],
        'datasets_count' => (int)$datasetCount,
        'listings_count' => (int)$listingCount,
        'lipinski_pass' => (int)$lipinski,
        'qed_good' => (int)$qed,
        'last_7_days' => (int)$last7d,
        'trial' => $trial
    ]);
}

if ($path === 'extend-trial' && $method === 'POST') {
    $user = authUser($db);
    if (!$user || !$user['is_admin']) {
        jsonOut(['error' => 'Admin access required'], 403);
    }

    $targetUserId = $input['user_id'] ?? 0;
    $extraDays = max(1, (int)($input['days'] ?? 7));
    $setPaidUntil = $input['set_paid_until'] ?? false;

    $target = $db->querySingle("SELECT id, trial_ends_at, paid_until FROM users WHERE id = " . intval($targetUserId), true);
    if (!$target) {
        jsonOut(['error' => 'User not found'], 404);
    }

    if ($setPaidUntil) {
        $newPaid = date('Y-m-d H:i:s', strtotime("+$extraDays days"));
        $db->exec("UPDATE users SET paid_until = '$newPaid' WHERE id = " . intval($targetUserId));
        jsonOut(['success' => true, 'paid_until' => $newPaid, 'days_extended' => $extraDays]);
    } else {
        $baseDate = !empty($target['trial_ends_at']) ? $target['trial_ends_at'] : date('Y-m-d H:i:s');
        $newTrial = date('Y-m-d H:i:s', strtotime($baseDate . " +$extraDays days"));
        $db->exec("UPDATE users SET trial_ends_at = '$newTrial' WHERE id = " . intval($targetUserId));
        jsonOut(['success' => true, 'trial_ends_at' => $newTrial, 'days_extended' => $extraDays]);
    }
}

/* =========================================================
   MINING
   ========================================================= */

if ($path === 'mine' && $method === 'POST') {
    $user = authUser($db);
    if (!$user && isset($input['user_id'])) {
        $uid = intval($input['user_id']);
        $res = $db->query("SELECT id, email, display_name, total_molecules, total_earnings, trial_ends_at, paid_until, is_admin FROM users WHERE id = $uid");
        $user = $res->fetchArray(SQLITE3_ASSOC);
    }
    if (!$user) jsonOut(['error' => 'Not logged in', 'debug' => ['has_session' => isset($_SESSION['user_id']), 'input_keys' => array_keys($input), 'user_id_present' => isset($input['user_id'])]], 401);

    requireTrialOrPaid($db, $user);

    $cid = $input['cid'] ?? 0;
    $smiles = $input['smiles'] ?? '';
    if (!$smiles) jsonOut(['error' => 'smiles required'], 400);

    $check = $db->prepare("SELECT id FROM molecules WHERE user_id = ? AND smiles = ?");
    $check->bindValue(1, $user['id'], SQLITE3_INTEGER);
    $check->bindValue(2, $smiles, SQLITE3_TEXT);
    $res = $check->execute();
    if ($res->fetchArray(SQLITE3_ASSOC)) {
        jsonOut(['success' => true, 'duplicate' => true, 'message' => 'Molecule already harvested']);
    }

    $stmt = $db->prepare("INSERT INTO molecules (user_id, cid, smiles, name, mw, logp, tpsa, hbd, hba, rotatable, qed, lipinski_pass, veber_pass, pains_hit, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    $stmt->bindValue(1, $user['id'], SQLITE3_INTEGER);
    $stmt->bindValue(2, $cid, SQLITE3_INTEGER);
    $stmt->bindValue(3, $smiles, SQLITE3_TEXT);
    $stmt->bindValue(4, $input['name'] ?? '', SQLITE3_TEXT);
    $stmt->bindValue(5, $input['mw'] ?? 0, SQLITE3_FLOAT);
    $stmt->bindValue(6, $input['logp'] ?? 0, SQLITE3_FLOAT);
    $stmt->bindValue(7, $input['tpsa'] ?? 0, SQLITE3_FLOAT);
    $stmt->bindValue(8, $input['hbd'] ?? 0, SQLITE3_INTEGER);
    $stmt->bindValue(9, $input['hba'] ?? 0, SQLITE3_INTEGER);
    $stmt->bindValue(10, $input['rotatable'] ?? 0, SQLITE3_INTEGER);
    $stmt->bindValue(11, $input['qed'] ?? 0, SQLITE3_FLOAT);
    $stmt->bindValue(12, $input['lipinski_pass'] ?? 0, SQLITE3_INTEGER);
    $stmt->bindValue(13, $input['veber_pass'] ?? 0, SQLITE3_INTEGER);
    $stmt->bindValue(14, $input['pains_hit'] ?? 0, SQLITE3_INTEGER);
    $stmt->bindValue(15, $input['source'] ?? 'pubchem', SQLITE3_TEXT);
    $stmt->execute();

    $db->exec("UPDATE users SET total_molecules = total_molecules + 1 WHERE id = {$user['id']}");

    jsonOut(['success' => true, 'molecule_id' => $db->lastInsertRowID()]);
}

/* =========================================================
   USER STATS
   ========================================================= */

if ($path === 'stats' && $method === 'GET') {
    $user = authUser($db);
    if (!$user && isset($_GET['user_id'])) {
        $uid = intval($_GET['user_id']);
        $res = $db->query("SELECT id, email, display_name, total_molecules, total_earnings, trial_ends_at, paid_until, is_admin FROM users WHERE id = $uid");
        $user = $res->fetchArray(SQLITE3_ASSOC);
    }
    if (!$user) jsonOut(['error' => 'Not logged in'], 401);

    $total = $db->querySingle("SELECT COUNT(DISTINCT smiles) FROM molecules WHERE user_id = {$user['id']}");
    $unique = $total;
    $lipinski = $db->querySingle("SELECT COUNT(DISTINCT smiles) FROM molecules WHERE user_id = {$user['id']} AND lipinski_pass = 1");
    $qed = $db->querySingle("SELECT COUNT(DISTINCT smiles) FROM molecules WHERE user_id = {$user['id']} AND qed >= 0.7");
    $last7d = $db->querySingle("SELECT COUNT(*) FROM molecules WHERE user_id = {$user['id']} AND created_at >= datetime('now', '-7 days')");

    $trial = getTrialStatus($user);

    jsonOut([
        'total_molecules' => $total,
        'unique' => $unique,
        'lipinski_pass' => $lipinski,
        'qed_good' => $qed,
        'last_7_days' => $last7d,
        'total_earnings' => $user['total_earnings'],
        'trial' => $trial
    ]);
}

/* =========================================================
   DATASETS
   ========================================================= */

if ($path === 'datasets' && $method === 'POST') {
    $user = authUser($db);
    if (!$user) jsonOut(['error' => 'Not logged in'], 401);

    $name = $input['name'] ?? 'Untitled Dataset';
    $desc = $input['description'] ?? '';
    $filter = $input['filter_sql'] ?? '';
    $maxMols = $input['max_molecules'] ?? 10000;
    $price = $input['price_usd'] ?? 99;

    $stmt = $db->prepare("INSERT INTO datasets (user_id, name, description, filter_sql, price_usd) VALUES (?, ?, ?, ?, ?)");
    $stmt->bindValue(1, $user['id'], SQLITE3_INTEGER);
    $stmt->bindValue(2, $name, SQLITE3_TEXT);
    $stmt->bindValue(3, $desc, SQLITE3_TEXT);
    $stmt->bindValue(4, $filter, SQLITE3_TEXT);
    $stmt->bindValue(5, $price, SQLITE3_FLOAT);
    $stmt->execute();
    $dsId = $db->lastInsertRowID();

    $sql = "SELECT id FROM molecules WHERE user_id = {$user['id']}";
    if ($filter) $sql .= " AND ($filter)";
    $sql .= " ORDER BY qed DESC LIMIT $maxMols";

    $res = $db->query($sql);
    $count = 0;
    while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
        $db->exec("INSERT INTO dataset_molecules (dataset_id, molecule_id) VALUES ($dsId, {$row['id']})");
        $count++;
    }
    $db->exec("UPDATE datasets SET molecule_count = $count WHERE id = $dsId");

    jsonOut(['success' => true, 'dataset_id' => $dsId, 'molecule_count' => $count, 'price_usd' => $price]);
}

if ($path === 'datasets' && $method === 'GET') {
    $user = authUser($db);
    if (!$user) jsonOut(['error' => 'Not logged in'], 401);

    $res = $db->query("SELECT * FROM datasets WHERE user_id = {$user['id']} ORDER BY created_at DESC");
    $sets = [];
    while ($row = $res->fetchArray(SQLITE3_ASSOC)) $sets[] = $row;
    jsonOut(['datasets' => $sets]);
}

/* =========================================================
   LISTINGS
   ========================================================= */

if ($path === 'listings' && $method === 'GET') {
    $res = $db->query("SELECT l.*, u.display_name as seller FROM listings l JOIN users u ON l.user_id = u.id WHERE l.status = 'active' ORDER BY l.created_at DESC");
    $listings = [];
    while ($row = $res->fetchArray(SQLITE3_ASSOC)) $listings[] = $row;
    jsonOut(['listings' => $listings, 'wallet' => '0x75B30d0dE751D9628510f3cb273F09f7137f9E3F']);
}

if ($path === 'listings' && $method === 'POST') {
    $user = authUser($db);
    if (!$user) jsonOut(['error' => 'Not logged in'], 401);

    $dsId = $input['dataset_id'] ?? 0;
    $name = $input['name'] ?? $input['title'] ?? 'Untitled';
    $desc = $input['description'] ?? $input['desc'] ?? '';
    $count = $input['molecule_count'] ?? 0;
    $price = $input['price_usd'] ?? $input['price'] ?? 99;

    $stmt = $db->prepare("INSERT INTO listings (user_id, dataset_id, name, description, molecule_count, price_usd) VALUES (?, ?, ?, ?, ?, ?)");
    $stmt->bindValue(1, $user['id'], SQLITE3_INTEGER);
    $stmt->bindValue(2, $dsId, SQLITE3_INTEGER);
    $stmt->bindValue(3, $name, SQLITE3_TEXT);
    $stmt->bindValue(4, $desc, SQLITE3_TEXT);
    $stmt->bindValue(5, $count, SQLITE3_INTEGER);
    $stmt->bindValue(6, $price, SQLITE3_FLOAT);
    $stmt->execute();

    jsonOut(['success' => true, 'listing_id' => $db->lastInsertRowID(), 'price_usd' => $price]);
}

/* =========================================================
   PAYMENTS
   ========================================================= */

if ($path === 'buy' && $method === 'POST') {
    $listingId = $input['listing_id'] ?? 0;
    $email = filter_var($input['email'] ?? '', FILTER_VALIDATE_EMAIL);
    $txHash = $input['tx_hash'] ?? '';

    if (!$listingId || !$email || !$txHash) {
        jsonOut(['error' => 'listing_id, email, tx_hash required'], 400);
    }

    $listing = $db->querySingle("SELECT * FROM listings WHERE id = $listingId AND status = 'active'", true);
    if (!$listing) jsonOut(['error' => 'Listing not found or sold'], 404);

    $token = bin2hex(random_bytes(16));
    $stmt = $db->prepare("INSERT INTO payments (listing_id, buyer_email, tx_hash, amount_usd, status, download_token) VALUES (?, ?, ?, ?, 'completed', ?)");
    $stmt->bindValue(1, $listingId, SQLITE3_INTEGER);
    $stmt->bindValue(2, $email, SQLITE3_TEXT);
    $stmt->bindValue(3, $txHash, SQLITE3_TEXT);
    $stmt->bindValue(4, $listing['price_usd'], SQLITE3_FLOAT);
    $stmt->bindValue(5, $token, SQLITE3_TEXT);
    $stmt->execute();

    $db->exec("UPDATE listings SET status = 'sold', sold_at = datetime('now'), buyer_email = '$email', tx_hash = '$txHash' WHERE id = $listingId");
    $db->exec("UPDATE users SET total_earnings = total_earnings + {$listing['price_usd']} WHERE id = {$listing['user_id']}");

    $downloadUrl = 'http://' . $_SERVER['HTTP_HOST'] . '/qmol/api/download.php?token=' . $token;

    @mail($email, 'Your Q-Mol Dataset Purchase', "Thank you!\n\nDataset: {$listing['name']}\nDownload: $downloadUrl\n\nThis link is valid for 7 days.", 'From: qmol@photon-bounce.com');

    jsonOut(['success' => true, 'download_url' => $downloadUrl, 'message' => 'Payment confirmed. Check your email.']);
}

if ($path === 'download' && $method === 'GET') {
    $token = $_GET['token'] ?? '';
    if (!$token) jsonOut(['error' => 'Missing token'], 400);

    $stmt = $db->prepare("SELECT p.listing_id, l.user_id, l.dataset_id FROM payments p JOIN listings l ON p.listing_id = l.id WHERE p.download_token = :token AND p.status = 'completed'");
    $stmt->bindValue(':token', $token, SQLITE3_TEXT);
    $res = $stmt->execute();
    $pay = $res->fetchArray(SQLITE3_ASSOC);
    if (!$pay) {
        jsonOut(['error' => 'Invalid or expired token'], 401);
    }

    $dsId = $pay['dataset_id'];
    if (!$dsId || $dsId == 0) {
        jsonOut(['error' => 'Dataset not linked to this listing'], 404);
    }

    $res = $db->query("SELECT m.* FROM molecules m JOIN dataset_molecules dm ON m.id = dm.molecule_id WHERE dm.dataset_id = $dsId");

    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="dataset_' . $pay['listing_id'] . '.csv"');
    echo "cid,smiles,name,mw,logp,tpsa,hbd,hba,qed,lipinski_pass,veber_pass,pains_hit\n";
    while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
        echo implode(',', array_map(function($v) { return is_string($v) ? '"' . str_replace('"', '""', $v) . '"' : $v; }, [
            $row['cid'], $row['smiles'], $row['name'], $row['mw'], $row['logp'], $row['tpsa'],
            $row['hbd'], $row['hba'], $row['qed'], $row['lipinski_pass'], $row['veber_pass'], $row['pains_hit']
        ])) . "\n";
    }
    exit;
}

/* =========================================================
   STRIPE WEBHOOK
   ========================================================= */

if ($path === 'webhook/stripe' && $method === 'POST') {
    $payload = @file_get_contents('php://input');
    $sigHeader = $_SERVER['HTTP_STRIPE_SIGNATURE'] ?? '';

    // Placeholder: validate signature with Stripe endpoint secret in production
    $event = null;
    try {
        $event = json_decode($payload, true);
    } catch (Exception $e) {
        jsonOut(['error' => 'Invalid payload'], 400);
    }

    if (!$event) {
        jsonOut(['error' => 'Invalid payload'], 400);
    }

    $type = $event['type'] ?? 'unknown';
    $obj = $event['data']['object'] ?? [];

    switch ($type) {
        case 'checkout.session.completed':
            $customerEmail = $obj['customer_email'] ?? '';
            $metadata = $obj['metadata'] ?? [];
            $userId = $metadata['user_id'] ?? 0;
            $plan = $metadata['plan'] ?? 'monthly';
            $duration = ($plan === 'yearly') ? 365 : 30;

            if ($userId) {
                $paidUntil = date('Y-m-d H:i:s', strtotime("+$duration days"));
                $db->exec("UPDATE users SET paid_until = '$paidUntil' WHERE id = " . intval($userId));
            }
            break;

        case 'invoice.payment_succeeded':
            // Recurring subscription payment succeeded
            break;

        case 'invoice.payment_failed':
            // Payment failed, could notify user
            break;
    }

    jsonOut(['received' => true, 'type' => $type]);
}

/* =========================================================
   APK INFO
   ========================================================= */

if ($path === 'apks' && $method === 'GET') {
    $apkPath = __DIR__ . '/../qmol.apk';
    $size = 0;
    $modified = null;

    if (file_exists($apkPath)) {
        $size = filesize($apkPath);
        $modified = date('c', filemtime($apkPath));
    }

    $host = ($_SERVER['HTTP_HOST'] ?? 'photon-bounce.com');
    $apkUrl = 'https://' . $host . '/qmol/qmol.apk';

    jsonOut([
        'apk' => [
            'url' => $apkUrl,
            'size_bytes' => $size,
            'size_mb' => $size ? round($size / 1048576, 2) : 0,
            'modified_at' => $modified,
            'version' => '1.0.0',
            'qr_url' => 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' . urlencode($apkUrl)
        ]
    ]);
}

/* =========================================================
   EXPORT
   ========================================================= */

if ($path === 'export' && $method === 'GET') {
    $user = authUser($db);
    if (!$user) jsonOut(['error' => 'Not logged in'], 401);

    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="molecules.csv"');
    echo "cid,smiles,name,mw,logp,tpsa,hbd,hba,qed,lipinski_pass,veber_pass,pains_hit\n";

    $res = $db->query("SELECT * FROM molecules WHERE user_id = {$user['id']} ORDER BY qed DESC");
    while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
        echo implode(',', array_map(function($v) { return is_string($v) ? '"' . str_replace('"', '""', $v) . '"' : $v; }, [
            $row['cid'], $row['smiles'], $row['name'], $row['mw'], $row['logp'], $row['tpsa'],
            $row['hbd'], $row['hba'], $row['qed'], $row['lipinski_pass'], $row['veber_pass'], $row['pains_hit']
        ])) . "\n";
    }
    exit;
}

/* =========================================================
   PING (Session Keep-Alive)
   ========================================================= */

if ($path === 'ping' && $method === 'GET') {
    $user = authUser($db);
    if (!$user) jsonOut(['error' => 'Not logged in'], 401);
    jsonOut(['status' => 'ok', 'timestamp' => time(), 'user_id' => $user['id']]);
}

/* =========================================================
   DEFAULT
   ========================================================= */

jsonOut(['status' => 'ok', 'message' => 'Q-Mol SaaS API', 'endpoints' => [
    'POST /register' => 'Email/password or MetaMask registration (7-day trial auto-set)',
    'POST /login' => 'Email/password or MetaMask login',
    'GET /me' => 'Current user info + trial status',
    'POST /mine' => 'Store mined molecule (checks trial/paid status)',
    'GET /stats' => 'User harvest stats + trial status',
    'POST /datasets' => 'Create dataset from harvested molecules',
    'GET /datasets' => 'List user datasets',
    'GET /listings' => 'Browse all marketplace listings',
    'POST /listings' => 'List a dataset for sale',
    'POST /buy' => 'Buy a listing + auto-deliver CSV',
    'GET /download?token=xxx' => 'Download purchased CSV',
    'GET /export' => 'Export all user molecules as CSV',
    'GET /trial-status' => 'Get current trial status',
    'GET /user-profile' => 'Full user profile with stats',
    'POST /extend-trial' => 'Admin-only: extend trial or set paid_until',
    'POST /webhook/stripe' => 'Stripe payment webhook handler',
    'GET /apks' => 'APK download info and QR code'
]]);
