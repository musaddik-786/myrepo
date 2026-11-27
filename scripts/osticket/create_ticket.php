<?php
/**
 * Create one osTicket ticket from JSON on stdin, using osTicket's own Ticket::create (no API key needed).
 * Autoresponder and alerts are OFF, so no email is sent.
 *   echo '{"name":"..","email":"..","subject":"..","message":"..","topic":"PolicyCenter"}' | php create_ticket.php <osticket-dir>
 * Prints one JSON line: {"ok":true,"number":"123456"} or {"ok":false,"error":"..."}.
 */
if (PHP_SAPI !== 'cli') exit(1);
function out($a) { echo json_encode($a) . "\n"; exit(empty($a['ok']) ? 1 : 0); }

$root = rtrim($argv[1] ?? '', '/');
if (!$root || !is_file("$root/bootstrap.php")) out(['ok' => false, 'error' => 'osTicket directory not found']);
$in = json_decode(stream_get_contents(STDIN), true);
foreach (['name', 'email', 'subject', 'message'] as $k) {
    if (empty($in[$k]) || !is_string($in[$k])) out(['ok' => false, 'error' => "missing $k"]);
}
if (!filter_var($in['email'], FILTER_VALIDATE_EMAIL)) out(['ok' => false, 'error' => 'invalid email']);

chdir($root);
require_once 'bootstrap.php';
require_once CLI_DIR . 'cli.inc.php';
Bootstrap::loadConfig();
Bootstrap::defineTables(TABLE_PREFIX);
Bootstrap::loadCode();
Bootstrap::connect();
if (!($ost = osTicket::start()) || !($cfg = $ost->getConfig())) out(['ok' => false, 'error' => 'cannot start osTicket']);

// From the CLI, Ticket::create reuses an existing requester but will not create one.
if (!User::lookupByEmail($in['email'])) {
    $uf = UserForm::getUserForm()->getForm(['name' => $in['name'], 'email' => $in['email']]);
    $uf->isValid();
    if (!User::fromVars($uf->getClean(), true)) out(['ok' => false, 'error' => 'could not create requester']);
}
$topicId = Topic::getIdByName($in['topic'] ?? '', 0);
$data = ['name' => $in['name'], 'email' => $in['email'], 'subject' => $in['subject'],
         'message' => $in['message'], 'source' => 'API'];
if ($topicId) $data['topicId'] = $topicId;
$errors = [];
$ticket = Ticket::create($data, $errors, 'api', false, false);
if (!$ticket) out(['ok' => false, 'error' => json_encode($errors)]);
out(['ok' => true, 'number' => (string) $ticket->getNumber()]);
