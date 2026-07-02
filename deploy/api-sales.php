<?php
/**
 * Q-Mol Auto-Sales & Payment Processor
 * 
 * Handles:
 * - Listing datasets for sale (POST /list-dataset)
 * - Recording payments (POST /confirm-payment)  
 * - Auto-delivering CSV files (GET /download/{dataset_id})
 * 
 * All data stored in SQLite for persistence.
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$DB_FILE = __DIR__ . '/../../data/marketplace.sqlite';
$DATASET_DIR = __DIR__ . '/../../data/datasets';
$ADMIN_TOKEN = getenv('QMOL_ADMIN_TOKEN') ?: 'e7486611d2f8a0faf0bf7bd696a444fa49b9eda24ed4b654a988408939e9de3c';
$WALLET = '0x75B30d0dE751D9628510f3cb273F09f7137f9E3F';

// Ensure directories exist
if (!is_dir(dirname($DB_FILE))) {
    mkdir(dirname($DB_FILE), 0755, true);
}
if (!is_dir($DATASET_DIR)) {
    mkdir($DATASET_DIR, 0755, true);
}

// Init database
$db = new SQLite3($DB_FILE);
$db->exec("CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    molecule_count INTEGER,
    price_usd REAL,
    csv_path TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sold_at TEXT,
    buyer_email TEXT,
    tx_hash TEXT
)");

$db->exec("CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER,
    tx_hash TEXT NOT NULL,
    amount_usd REAL,
    buyer_email TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)");

$method = $_SERVER['REQUEST_METHOD'];
$path = $_SERVER['REQUEST_URI'] ?? '';
$path = parse_url($path, PHP_URL_PATH);
$path = str_replace('/qmol/api-sales.php', '', $path);
$path = str_replace('/api-sales.php', '', $path);
$path = rtrim($path, '/');

$input = json_decode(file_get_contents('php://input'), true) ?: [];

// === ROUTE: LIST DATASET ===
if ($method === 'POST' && $path === '/list-dataset') {
    $adminToken = $_SERVER['HTTP_X_ADMIN_TOKEN'] ?? '';
    if ($adminToken !== $ADMIN_TOKEN) {
        http_response_code(401);
        echo json_encode(['error' => 'Admin token required']);
        exit;
    }
    
    $datasetId = $input['dataset_id'] ?? 'ds_' . time();
    $name = $input['name'] ?? 'Untitled Dataset';
    $description = $input['description'] ?? '';
    $count = $input['molecule_count'] ?? 0;
    $price = $input['price_usd'] ?? 99;
    $csvData = $input['csv_data'] ?? '';
    
    // Save CSV file
    $csvPath = $DATASET_DIR . '/' . $datasetId . '.csv';
    file_put_contents($csvPath, $csvData);
    
    // Insert listing
    $stmt = $db->prepare("INSERT OR REPLACE INTO listings (dataset_id, name, description, molecule_count, price_usd, csv_path, status) VALUES (?, ?, ?, ?, ?, ?, 'active')");
    $stmt->bindValue(1, $datasetId, SQLITE3_TEXT);
    $stmt->bindValue(2, $name, SQLITE3_TEXT);
    $stmt->bindValue(3, $description, SQLITE3_TEXT);
    $stmt->bindValue(4, $count, SQLITE3_INTEGER);
    $stmt->bindValue(5, $price, SQLITE3_FLOAT);
    $stmt->bindValue(6, $csvPath, SQLITE3_TEXT);
    $stmt->execute();
    
    echo json_encode([
        'success' => true,
        'dataset_id' => $datasetId,
        'price_usd' => $price,
        'wallet' => $WALLET,
        'buy_url' => 'http://photon-bounce.com/qmol/marketplace.html?dataset=' . $datasetId
    ]);
    exit;
}

// === ROUTE: GET LISTINGS ===
if ($method === 'GET' && $path === '/listings') {
    $result = $db->query("SELECT * FROM listings WHERE status = 'active' ORDER BY created_at DESC");
    $listings = [];
    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
        unset($row['csv_path']); // Don't expose server path
        $listings[] = $row;
    }
    echo json_encode(['listings' => $listings, 'wallet' => $WALLET]);
    exit;
}

// === ROUTE: GET SINGLE LISTING ===
if ($method === 'GET' && preg_match('#^/listing/(.+)$#', $path, $matches)) {
    $datasetId = $matches[1];
    $stmt = $db->prepare("SELECT * FROM listings WHERE dataset_id = ? AND status = 'active'");
    $stmt->bindValue(1, $datasetId, SQLITE3_TEXT);
    $result = $stmt->execute();
    $row = $result->fetchArray(SQLITE3_ASSOC);
    
    if (!$row) {
        http_response_code(404);
        echo json_encode(['error' => 'Dataset not found']);
        exit;
    }
    
    unset($row['csv_path']);
    echo json_encode(['listing' => $row, 'wallet' => $WALLET]);
    exit;
}

// === ROUTE: CONFIRM PAYMENT (BUY) ===
if ($method === 'POST' && $path === '/confirm-payment') {
    $datasetId = $input['dataset_id'] ?? '';
    $txHash = $input['tx_hash'] ?? '';
    $buyerEmail = $input['buyer_email'] ?? '';
    $amount = $input['amount_usd'] ?? 0;
    
    if (empty($datasetId) || empty($txHash) || empty($buyerEmail)) {
        http_response_code(400);
        echo json_encode(['error' => 'Missing dataset_id, tx_hash, or buyer_email']);
        exit;
    }
    
    // Check listing exists
    $stmt = $db->prepare("SELECT * FROM listings WHERE dataset_id = ? AND status = 'active'");
    $stmt->bindValue(1, $datasetId, SQLITE3_TEXT);
    $result = $stmt->execute();
    $listing = $result->fetchArray(SQLITE3_ASSOC);
    
    if (!$listing) {
        http_response_code(404);
        echo json_encode(['error' => 'Dataset not found or already sold']);
        exit;
    }
    
    // Record payment
    $stmt = $db->prepare("INSERT INTO payments (listing_id, tx_hash, amount_usd, buyer_email, status) VALUES (?, ?, ?, ?, 'pending')");
    $stmt->bindValue(1, $listing['id'], SQLITE3_INTEGER);
    $stmt->bindValue(2, $txHash, SQLITE3_TEXT);
    $stmt->bindValue(3, $amount, SQLITE3_FLOAT);
    $stmt->bindValue(4, $buyerEmail, SQLITE3_TEXT);
    $stmt->execute();
    $paymentId = $db->lastInsertRowID();
    
    // Auto-verify: In production, you'd verify the tx on-chain. For now, accept with review.
    // Auto-approve for demo (in real setup, manual review or on-chain verification)
    $autoApprove = true; // Set to false for manual review
    
    if ($autoApprove) {
        // Mark as sold
        $stmt = $db->prepare("UPDATE listings SET status = 'sold', sold_at = CURRENT_TIMESTAMP, buyer_email = ?, tx_hash = ? WHERE id = ?");
        $stmt->bindValue(1, $buyerEmail, SQLITE3_TEXT);
        $stmt->bindValue(2, $txHash, SQLITE3_TEXT);
        $stmt->bindValue(3, $listing['id'], SQLITE3_INTEGER);
        $stmt->execute();
        
        // Update payment status
        $db->exec("UPDATE payments SET status = 'completed' WHERE id = $paymentId");
        
        // Generate download token
        $downloadToken = bin2hex(random_bytes(16));
        $db->exec("UPDATE payments SET download_token = '$downloadToken' WHERE id = $paymentId");
        
        // Send email (if mail() is available)
        $subject = "Your Q-Mol Dataset Purchase - " . $listing['name'];
        $downloadUrl = 'http://photon-bounce.com/qmol/download-dataset.php?token=' . $downloadToken;
        $message = "Thank you for your purchase!\n\n";
        $message .= "Dataset: " . $listing['name'] . "\n";
        $message .= "Molecules: " . $listing['molecule_count'] . "\n";
        $message .= "Transaction: " . $txHash . "\n\n";
        $message .= "Download your CSV:\n" . $downloadUrl . "\n\n";
        $message .= "This link is valid for 7 days.\n";
        
        @mail($buyerEmail, $subject, $message, 'From: qmol@photon-bounce.com');
        
        echo json_encode([
            'success' => true,
            'status' => 'completed',
            'download_url' => $downloadUrl,
            'message' => 'Payment confirmed. Check your email for the download link.'
        ]);
    } else {
        echo json_encode([
            'success' => true,
            'status' => 'pending_review',
            'message' => 'Payment submitted for review. You will receive your dataset within 24 hours.'
        ]);
    }
    exit;
}

// === ROUTE: DOWNLOAD DATASET ===
if ($method === 'GET' && preg_match('#^/download-dataset#', $path)) {
    $token = $_GET['token'] ?? '';
    if (empty($token)) {
        http_response_code(400);
        echo json_encode(['error' => 'Missing download token']);
        exit;
    }
    
    $stmt = $db->prepare("SELECT p.*, l.csv_path, l.name FROM payments p JOIN listings l ON p.listing_id = l.id WHERE p.download_token = ? AND p.status = 'completed'");
    $stmt->bindValue(1, $token, SQLITE3_TEXT);
    $result = $stmt->execute();
    $row = $result->fetchArray(SQLITE3_ASSOC);
    
    if (!$row || !file_exists($row['csv_path'])) {
        http_response_code(404);
        echo json_encode(['error' => 'Invalid or expired download link']);
        exit;
    }
    
    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="' . basename($row['csv_path']) . '"');
    readfile($row['csv_path']);
    exit;
}

// === DEFAULT: Test endpoint ===
echo json_encode([
    'status' => 'ok',
    'message' => 'Q-Mol Auto-Sales API',
    'wallet' => $WALLET,
    'endpoints' => [
        'POST /list-dataset' => 'List a dataset for sale (admin)',
        'GET /listings' => 'Get all active listings',
        'GET /listing/{id}' => 'Get single listing',
        'POST /confirm-payment' => 'Submit payment + auto-deliver',
        'GET /download-dataset?token=xxx' => 'Download purchased dataset'
    ]
]);
