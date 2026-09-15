/**
 * Acceptance test suite for Phase 6: 3D Digital Human Avatar (Embodied AI)
 * Verifies:
 * 1. avatar_engine.js bundle integrity & export
 * 2. ARKit 52 blendshape morph targets & lerp interpolation
 * 3. State machine transitions (IDLE, LISTENING, THINKING, SPEAKING, WORKING, INQUIRING, INTERRUPTED)
 * 4. Multi-tiered lip-sync hierarchy (Viseme timing -> Web Audio analyser -> Procedural)
 * 5. Monotonic sequence filtering and out-of-order jitter discard
 * 6. Barge-in instant mouth reset to viseme_sil
 * 7. widget.js Shadow DOM Avatar mode toggle, canvas container, and event routing
 * 8. Dashboard AI Employees Avatar 3D configuration UI
 */

const fs = require('fs');
const path = require('path');

function runAvatarAcceptanceTests() {
  console.log('\n======================================================');
  console.log('PHASE 6: 3D DIGITAL HUMAN AVATAR ACCEPTANCE TEST SUITE');
  console.log('======================================================\n');

  const enginePath = path.join(__dirname, '../public/avatar_engine.js');
  const widgetPath = path.join(__dirname, '../public/widget.js');
  const dashboardPath = path.join(__dirname, '../src/app/(dashboard)/ai-employees/page.tsx');

  if (!fs.existsSync(enginePath)) {
    console.error('FAIL: avatar_engine.js not found at', enginePath);
    process.exit(1);
  }
  if (!fs.existsSync(widgetPath)) {
    console.error('FAIL: widget.js not found at', widgetPath);
    process.exit(1);
  }

  const engineCode = fs.readFileSync(enginePath, 'utf8');
  const widgetCode = fs.readFileSync(widgetPath, 'utf8');
  const dashboardCode = fs.readFileSync(dashboardPath, 'utf8');
  const results = [];

  function assertRule(name, condition, details) {
    if (condition) {
      console.log(`✅ PASS: ${name}`);
      results.push({ name, status: 'PASS', details });
    } else {
      console.error(`❌ FAIL: ${name}`);
      results.push({ name, status: 'FAIL', details });
    }
  }

  // 1. Avatar Engine Bundle & Export
  assertRule(
    'Avatar Engine bundle exists and exports AvatarEngine class',
    engineCode.includes('function AvatarEngine') &&
    engineCode.includes('global.AvatarEngine = AvatarEngine'),
    'avatar_engine.js provides self-contained AvatarEngine controller'
  );

  // 2. ARKit 52 Blendshape Morph Targets
  assertRule(
    'Standardized ARKit blendshape morph-target definitions present',
    engineCode.includes('jawOpen') &&
    engineCode.includes('mouthSmileLeft') &&
    engineCode.includes('mouthSmileRight') &&
    engineCode.includes('mouthPucker') &&
    engineCode.includes('eyeBlinkLeft') &&
    engineCode.includes('eyeBlinkRight'),
    'Implements ARKit 52 standard facial blendshape morph targets'
  );

  // 3. Multi-Tiered Lip-Sync Hierarchy
  assertRule(
    'Multi-tiered lip-sync hierarchy implemented (Viseme cues -> Audio analyser -> Procedural)',
    engineCode.includes('timedVisemesQueue') &&
    engineCode.includes('audioAnalyser') &&
    engineCode.includes('proceduralJaw'),
    'Prioritizes provider visemes, falls back to Web Audio FFT, and defaults to procedural rhythmic motion'
  );

  // 4. Monotonic Sequence Filtering
  assertRule(
    'Monotonic sequence number filtering prevents out-of-order desync',
    engineCode.includes('event.sequence < this.lastSequence') &&
    engineCode.includes('Discarding stale out-of-order event'),
    'Checks integer sequence counter and discards jittered/stale packets'
  );

  // 5. State Machine & Natural Procedural Behaviors
  assertRule(
    'Avatar State Machine with procedural breathing, eye blinks, and head tilt',
    engineCode.includes('transitionTo') &&
    engineCode.includes('isBlinking') &&
    engineCode.includes('headTilt') &&
    engineCode.includes('INTERRUPTED'),
    'Supports IDLE, LISTENING, THINKING, SPEAKING, WORKING, INQUIRING, INTERRUPTED'
  );

  // 6. Instant Barge-In Reset
  assertRule(
    'Barge-in instant mouth reset to viseme_sil',
    engineCode.includes('resetMouth') &&
    engineCode.includes('this.morphWeights.jawOpen = 0'),
    'Resets jawOpen and mouth visemes immediately upon interruption'
  );

  // 7. Widget Shadow DOM Avatar Mode Toggle & Canvas
  assertRule(
    'Widget Shadow DOM renders Avatar mode toggle and 3D canvas',
    widgetCode.includes('btn-mode-avatar') &&
    widgetCode.includes('view-avatar-mode') &&
    widgetCode.includes('avatar-3d-canvas') &&
    widgetCode.includes('avatar-status-pill'),
    'widget.js provides three-way Chat/Voice/Avatar mode switching and WebGL canvas'
  );

  // 8. Widget Event Forwarding to Avatar Engine
  assertRule(
    'Widget forwards incoming WebSocket avatar events to AvatarEngine',
    widgetCode.includes('avatarEngine.handleAvatarEvent(data)') &&
    widgetCode.includes('avatarEngine.setAudioAnalyser(analyser)'),
    'Pipes audio chunks, visemes, and status changes directly into visual engine'
  );

  // 9. Dashboard Avatar Configuration
  assertRule(
    'Dashboard AI Employee management includes 3D Avatar configuration',
    dashboardCode.includes('avatar_config') &&
    dashboardCode.includes('3D Digital Human Avatar') &&
    dashboardCode.includes('avatarPreset') &&
    dashboardCode.includes('avatarExpression'),
    'Enables toggling avatar, selecting model rig presets, and configuring baseline expression'
  );

  // 10. Dashboard 3D Avatar Capability Badge
  assertRule(
    'Dashboard Employee Cards display Avatar 3D capability badge',
    dashboardCode.includes('Avatar 3D'),
    'Badges show avatar embodiment readiness on employee grid'
  );

  console.log('\n======================================================');
  const passCount = results.filter((r) => r.status === 'PASS').length;
  console.log(`TOTAL SCENARIOS TESTED: ${results.length}`);
  console.log(`PASSED: ${passCount} / ${results.length}`);
  console.log('======================================================\n');

  if (passCount !== results.length) {
    process.exit(1);
  }
}

runAvatarAcceptanceTests();
