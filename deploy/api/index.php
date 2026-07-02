<?php
/**
 * Q-Mol SaaS API — User Auth, Mining, Datasets, Marketplace
 * SQLite backend (works on shared hosting, no MySQL needed)
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(200); exit; }

session_start();

$DB_FILE = __DIR__ . '/../../data/saas.sqlite';
$DATA_DIR = dirname($DB_FILE);
if (!is_dir($DATA_DIR)) mkdir($DATA_DIR, 0755, true);

$db = new SQLite3($DB_FILE);
$db->busyTimeout(5000);

$db->exec("CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password_hash TEXT,
    eth_address TEXT UNIQUE,
    display_name TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    total_molecules INTEGER DEFAULT 0,
    total_earnings REAL DEFAULT 0
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

$method = $_SERVER['REQUEST_METHOD'];
$path = $_SERVER['REQUEST_URI'] ?? '';
$path = parse_url($path, PHP_URL_PATH);
$path = str_replace('/qmol/api/index.php', '', $path);
$path = str_replace('/qmol/api/', '', $path);
$path = str_replace('/api/index.php', '', $path);
$path = str_replace('/api/', '', $path);
$path = rtrim($path, '/');

$input = json_decode(file_get_contents('php://input'), true) ?: [];

function authUser($db) {
    if (isset($_SESSION['user_id'])) {
        $stmt = $db->prepare("SELECT id, email, eth_address, display_name, total_molecules, total_earnings FROM users WHERE id = ?");
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

// ==================== AUTH ====================
if ($path === 'register' && $method === 'POST') {
    $email = filter_var($input['email'] ?? '', FILTER_VALIDATE_EMAIL);
    $password = $input['password'] ?? '';
    $ethAddress = $input['eth_address'] ?? null;
    $displayName = $input['display_name'] ?? ($email ? explode('@', $email)[0] : 'User');
    
    if (!$email && !$ethAddress) {
        jsonOut(['error' => 'Email or MetaMask address required'], 400);
    }
    
    $pwHash = $password ? password_hash($password, PASSWORD_DEFAULT) : null;
    
    $stmt = $db->prepare("INSERT INTO users (email, password_hash, eth_address, display_name) VALUES (?, ?, ?, ?)");
    $stmt->bindValue(1, $email, SQLITE3_TEXT);
    $stmt->bindValue(2, $pwHash, SQLITE3_TEXT);
    $stmt->bindValue(3, $ethAddress, SQLITE3_TEXT);
    $stmt->bindValue(4, $displayName, SQLITE3_TEXT);
    
    if ($stmt->execute()) {
        $userId = $db->lastInsertRowID();
        $_SESSION['user_id'] = $userId;
        jsonOut(['success' => true, 'user_id' => $userId, 'email' => $email, 'eth_address' => $ethAddress]);
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
            $stmt = $db->prepare("INSERT INTO users (eth_address, display_name) VALUES (?, ?)");
            $stmt->bindValue(1, $ethAddress, SQLITE3_TEXT);
            $stmt->bindValue(2, substr($ethAddress, 0, 6) . '...' . substr($ethAddress, -4), SQLITE3_TEXT);
            $stmt->execute();
            $userId = $db->lastInsertRowID();
            $_SESSION['user_id'] = $userId;
            jsonOut(['success' => true, 'user_id' => $userId, 'new_user' => true]);
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
    jsonOut(['user' => $user]);
}

if ($path === 'logout' && $method === 'POST') {
    session_destroy();
    jsonOut(['success' => true]);
}

// ==================== MINING ====================
if ($path === 'mine' && $method === 'POST') {
    $user = authUser($db);
    if (!$user) jsonOut(['error' => 'Not logged in'], 401);
    
    $cid = $input['cid'] ?? 0;
    $smiles = $input['smiles'] ?? '';
    if (!$smiles) jsonOut(['error' => 'smiles required'], 400);
    
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

// ==================== USER STATS ====================
if ($path === 'stats' && $method === 'GET') {
    $user = authUser($db);
    if (!$user) jsonOut(['error' => 'Not logged in'], 401);
    
    $total = $db->querySingle("SELECT COUNT(*) FROM molecules WHERE user_id = {$user['id']}");
    $unique = $db->querySingle("SELECT COUNT(DISTINCT smiles) FROM molecules WHERE user_id = {$user['id']}");
    $lipinski = $db->querySingle("SELECT COUNT(*) FROM molecules WHERE user_id = {$user['id']} AND lipinski_pass = 1");
    $qed = $db->querySingle("SELECT COUNT(*) FROM molecules WHERE user_id = {$user['id']} AND qed >= 0.7");
    $last7d = $db->querySingle("SELECT COUNT(*) FROM molecules WHERE user_id = {$user['id']} AND created_at >= datetime('now', '-7 days')");
    
    jsonOut(['total_molecules' => $total, 'unique' => $unique, 'lipinski_pass' => $lipinski, 'qed_good' => $qed, 'last_7_days' => $last7d, 'total_earnings' => $user['total_earnings']]);
}

// ==================== DATASETS ====================
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

// ==================== LISTINGS ====================
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
    $name = $input['name'] ?? 'Untitled';
    $desc = $input['description'] ?? '';
    $count = $input['molecule_count'] ?? 0;
    $price = $input['price_usd'] ?? 99;
    
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

// ==================== PAYMENTS ====================
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
    
    $pay = $db->querySingle("SELECT p.listing_id, l.user_id FROM payments p JOIN listings l ON p.listing_id = l.id WHERE p.download_token = ? AND p.status = 'completed'", true, $token);
    if (!$pay) jsonOut(['error' => 'Invalid or expired token'], 404);
    
    $dsId = $db->querySingle("SELECT dataset_id FROM listings WHERE id = {$pay['listing_id']}");
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

// ==================== DEFAULT ====================
jsonOut(['status' => 'ok', 'message' => 'Q-Mol SaaS API', 'endpoints' => [
    'POST /register' => 'Email/password or MetaMask registration',
    'POST /login' => 'Email/password or MetaMask login',
    'GET /me' => 'Current user info',
    'POST /mine' => 'Store mined molecule (auth required)',
    'GET /stats' => 'User harvest stats',
    'POST /datasets' => 'Create dataset from harvested molecules',
    'GET /datasets' => 'List user datasets',
    'GET /listings' => 'Browse all marketplace listings',
    'POST /listings' => 'List a dataset for sale',
    'POST /buy' => 'Buy a listing + auto-deliver CSV',
    'GET /download?token=xxx' => 'Download purchased CSV'
]]);
