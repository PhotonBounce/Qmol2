<?php
/**
 * Q-Mol Payment Confirmation Handler
 */

// === CHANGE THIS TO YOUR EMAIL ===
$to_email = 'qmol@photon-bounce.com';  // Where confirmations go
$from_email = 'noreply@photon-bounce.com';

// Response headers
header('Content-Type: application/json');

// Only accept POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

// Get form data
$email = filter_input(INPUT_POST, 'email', FILTER_VALIDATE_EMAIL);
$txhash = filter_input(INPUT_POST, 'txhash', FILTER_SANITIZE_SPECIAL_CHARS);
$plan = filter_input(INPUT_POST, 'plan', FILTER_SANITIZE_SPECIAL_CHARS);
$notes = filter_input(INPUT_POST, 'notes', FILTER_SANITIZE_SPECIAL_CHARS);

// Validate
if (!$email || !$txhash || !$plan) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing required fields: email, txhash, plan']);
    exit;
}

// Validate txhash format (basic Ethereum check)
if (!preg_match('/^0x[a-fA-F0-9]{64}$/', $txhash)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid transaction hash format']);
    exit;
}

// Build email
$subject = "Q-Mol Payment Confirmation — $plan";
$body = "New Q-Mol payment confirmation:\n\n";
$body .= "Plan: $plan\n";
$body .= "Email: $email\n";
$body .= "TX Hash: $txhash\n";
$body .= "Etherscan: https://etherscan.io/tx/$txhash\n";
$body .= "Notes: " . ($notes ?: 'None') . "\n";
$body .= "\n---\n";
$body .= "Sent from: " . $_SERVER['REMOTE_ADDR'] . "\n";
$body .= "Time: " . date('Y-m-d H:i:s T') . "\n";

$headers = "From: $from_email\r\n";
$headers .= "Reply-To: $email\r\n";
$headers .= "X-Mailer: PHP/" . phpversion();

// Send email
$sent = mail($to_email, $subject, $body, $headers);

if ($sent) {
    echo json_encode([
        'success' => true,
        'message' => 'Payment confirmation received. We will verify and send your API key within 24 hours.',
        'txhash' => $txhash,
        'plan' => $plan,
    ]);
} else {
    http_response_code(500);
    echo json_encode([
        'error' => 'Failed to send email. Please contact us directly at ' . $to_email,
    ]);
}
