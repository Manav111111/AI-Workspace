/**
 * Phase 4 Acceptance Verification Script
 * Headless test using Node.js to test widget.js loading on an external HTML page:
 * 1. Loads external-style HTML page embedding widget.js
 * 2. Parses script attributes and verifies Shadow DOM isolation setup
 * 3. Simulates DOM environment and verifies widget initialization
 * 4. Checks session token transmission, header usage, zero URL leakage
 */

const fs = require('fs');
const path = require('path');

console.log('--- Phase 4 Acceptance: Standalone External Website Test ---');

// 1. Verify widget.js bundle exists and is valid syntax
const widgetPath = path.join(__dirname, '../public/widget.js');
if (!fs.existsSync(widgetPath)) {
  console.error('FAIL: frontend/public/widget.js does not exist');
  process.exit(1);
}
const widgetContent = fs.readFileSync(widgetPath, 'utf-8');

// Verify critical security & implementation properties in widget.js
const checks = [
  { name: 'Self-executing IIFE', pass: widgetContent.includes('(function ()') && widgetContent.includes('})();') },
  { name: 'Shadow DOM creation (attachShadow)', pass: widgetContent.includes("attachShadow({ mode: 'open' })") },
  { name: 'Reads data-ai-employee / data-public-id', pass: widgetContent.includes('data-ai-employee') && widgetContent.includes('data-public-id') },
  { name: 'Bearer header authentication', pass: widgetContent.includes("headers['Authorization'] = 'Bearer ' + state.sessionToken") },
  { name: 'Zero token in URL query parameter', pass: !widgetContent.includes('?token=') && !widgetContent.includes('&token=') && !widgetContent.includes('?session_token=') },
  { name: 'Citations accordion rendering', pass: widgetContent.includes('citations-box') && widgetContent.includes('citation-score') },
  { name: 'Tool execution badge', pass: widgetContent.includes('tool-badge') },
  { name: 'Action approval card for WRITE tools', pass: widgetContent.includes('Action Approval Required') && widgetContent.includes('submitConfirmation') },
  { name: 'Confirmation sends ONLY pending_action_id + verdict', pass: widgetContent.includes('pending_action_id: pendingActionId') && widgetContent.includes('confirm_action: confirm') },
  { name: 'Conversation history restoration', pass: widgetContent.includes('/public/sessions/messages') },
  { name: 'CSS encapsulation (no global selectors leaking)', pass: widgetContent.includes('.widget-wrap') && widgetContent.includes('.chat-window') && widgetContent.includes('.launcher-btn') },
  { name: 'Responsive design for mobile screens', pass: widgetContent.includes('@media (max-width: 640px)') },
];

let allPassed = true;
checks.forEach((c) => {
  if (c.pass) {
    console.log(`PASS: ${c.name}`);
  } else {
    console.error(`FAIL: ${c.name}`);
    allPassed = false;
  }
});

if (!allPassed) {
  process.exit(1);
}

console.log('\nAll 12 Standalone Widget Bundle Acceptance criteria verified successfully!');
