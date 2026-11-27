<?php
/**
 * Seed the three demo tickets for the "Suggested fix" panel into an osTicket install.
 *   1. GL final audit, premium moved the wrong way  -> expect card PC-AUD-01
 *   2. Policy locked after an approved OOS change   -> expect card PC-OOS-02
 *   3. ClaimCenter login loop                       -> expect "No KB match"
 *
 * Idempotent (a ticket whose subject already exists is skipped). Uses osTicket's own Ticket::create,
 * with autoresponder and alerts OFF so no email is sent.
 *
 * Usage: php seed_demo_tickets.php <osticket-dir> [--dry-run]
 */
if (PHP_SAPI !== 'cli') exit(1);

$root = rtrim($argv[1] ?? '', '/');
$dry  = in_array('--dry-run', $argv, true);
if (!$root || !is_file("$root/bootstrap.php")) {
    fwrite(STDERR, "Usage: php seed_demo_tickets.php <osticket-dir> [--dry-run]\n");
    exit(2);
}

$tickets = [
    [
        'topic'   => 'PolicyCenter',
        'subject' => 'Final audit gave a credit though payroll went up',
        'message' => "Commercial general liability policy, final audit.\n"
            . "Estimated payroll was \$400,000 and the auditor reported \$440,000, so we expected an additional premium.\n"
            . "PolicyCenter shows a credit of -\$156 on the audit premium summary. The audit bill has not been sent yet.\n"
            . "No mid-term changes on the term. Keyed by the auditor.",
    ],
    [
        'topic'   => 'PolicyCenter',
        'subject' => 'Policy locked after approved OOS endorsement',
        'message' => "A backdated endorsement was approved by underwriting but never reached Bound.\n"
            . "The policy now shows as locked and no further transactions can be started. "
            . "The job's workflow shows an error. Only this policy is affected so far.",
    ],
    [
        'topic'   => 'ClaimCenter',
        'subject' => 'ClaimCenter login page redirects in a loop',
        'message' => "Adjusters cannot sign in to ClaimCenter since this morning. "
            . "The login page redirects back to itself and never opens the desktop. Several adjusters see the same behaviour.",
    ],
];

chdir($root);
require_once 'bootstrap.php';
require_once CLI_DIR . 'cli.inc.php';
Bootstrap::loadConfig();
Bootstrap::defineTables(TABLE_PREFIX);
Bootstrap::loadCode();
Bootstrap::connect();
if (!($ost = osTicket::start()) || !($cfg = $ost->getConfig())) {
    fwrite(STDERR, "Unable to start osTicket (check include/ost-config.php)\n");
    exit(1);
}
$say = function ($m) use ($dry) { echo ($dry ? '[dry-run] ' : '') . $m . "\n"; };

// Ticket::create only reuses an existing requester when run from the CLI (it will not create one), so make sure it exists.
if (!$dry && !User::lookupByEmail('demo.requester@clientdemo.test')) {
    $uf = UserForm::getUserForm()->getForm(['name' => 'Demo Requester', 'email' => 'demo.requester@clientdemo.test']);
    $uf->isValid();
    if (!User::fromVars($uf->getClean(), true)) {
        fwrite(STDERR, "Could not create the demo requester user\n");
        exit(1);
    }
}

foreach ($tickets as $t) {
    $topicId = Topic::getIdByName($t['topic'], 0);
    if (!$topicId) { $say("SKIP (help topic '{$t['topic']}' missing; run scripts/osticket_setup_taxonomy.py): {$t['subject']}"); continue; }

    $exists = db_result(db_query('SELECT COUNT(*) FROM ' . TABLE_PREFIX . 'ticket__cdata WHERE subject = ' . db_input($t['subject'])));
    if ($exists) { $say("exists:  {$t['subject']}"); continue; }
    if ($dry)    { $say("would create ({$t['topic']}): {$t['subject']}"); continue; }

    $errors = [];
    $ticket = Ticket::create([
        'name'    => 'Demo Requester',
        'email'   => 'demo.requester@clientdemo.test',
        'subject' => $t['subject'],
        'message' => $t['message'],
        'topicId' => $topicId,
        'source'  => 'API',
    ], $errors, 'api', false, false);
    if ($ticket) $say("created #{$ticket->getNumber()} ({$t['topic']}): {$t['subject']}");
    else         $say("FAILED: {$t['subject']} -> " . json_encode($errors));
}
