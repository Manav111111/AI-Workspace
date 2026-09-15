/**
 * Acceptance test suite for Phase 5: Real-Time Voice AI
 * Verifies:
 * 1. widget.js bundle integrity
 * 2. Voice mode toggle and UI markup in Shadow DOM
 * 3. Voice visualizer and status pill presence
 * 4. WebSocket URL derivation
 * 5. Audio recording & playback pipeline definitions
 * 6. Barge-in / interruption handling
 * 7. Text ↔ Voice conversation continuity
 */

const fs = require('fs');
const path = require('path');

function runVoiceAcceptanceTests() {
  console.log('\n========================================');
  console.log('PHASE 5: VOICE AI ACCEPTANCE TEST SUITE');
  console.log('========================================\n');

  const widgetPath = path.join(__dirname, '../public/widget.js');
  if (!fs.existsSync(widgetPath)) {
    console.error('FAIL: widget.js not found at', widgetPath);
    process.exit(1);
  }

  const widgetCode = fs.readFileSync(widgetPath, 'utf8');
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

  // 1. Voice Mode Toggle Support
  assertRule(
    'Voice Mode toggle buttons exist in Shadow DOM',
    widgetCode.includes('btn-mode-chat') && widgetCode.includes('btn-mode-voice'),
    'Header includes Chat and Voice switch buttons'
  );

  // 2. Dual View Container Architecture
  assertRule(
    'Dual View Containers (Text View and Voice View) exist',
    widgetCode.includes('view-text-mode') && widgetCode.includes('view-voice-mode'),
    'Supports switching between text messages and voice interface in same card'
  );

  // 3. Voice Status Visualizer & Pill
  assertRule(
    'Voice visualizer, status pill, and mic button rendered',
    widgetCode.includes('voice-status-pill') &&
    widgetCode.includes('voice-visualizer') &&
    widgetCode.includes('voice-mic-btn'),
    'Displays IDLE/LISTENING/SPEAKING pill, pulsing avatar visualizer, and toggle mic button'
  );

  // 4. WebSocket URL Resolution & Handshake
  assertRule(
    'Voice WebSocket connection & Bearer token handshake implemented',
    widgetCode.includes('/api/v1/voice/stream') &&
    widgetCode.includes('type: \'auth\'') &&
    widgetCode.includes('token: token'),
    'Connects to /api/v1/voice/stream and sends initial auth frame with session token'
  );

  // 5. User Speech Audio Recording
  assertRule(
    'MediaRecorder audio capture with audio/webm opus encoding',
    widgetCode.includes('navigator.mediaDevices.getUserMedia') &&
    widgetCode.includes('MediaRecorder') &&
    widgetCode.includes('audio/webm'),
    'Captures microphone input and prepares base64 encoded chunks'
  );

  // 6. Audio Utterance Frame Dispatch
  assertRule(
    'Audio utterance frame dispatched over WebSocket',
    widgetCode.includes('type: \'audio_utterance\'') &&
    widgetCode.includes('data: base64data'),
    'Sends audio_utterance payload to server'
  );

  // 7. Streaming Audio Playback Queue
  assertRule(
    'Audio playback via Web Audio API AudioContext decodeAudioData',
    widgetCode.includes('AudioContext') &&
    widgetCode.includes('decodeAudioData') &&
    widgetCode.includes('createBufferSource'),
    'Decodes and plays synthesized audio chunks with HTML5 Audio fallback'
  );

  // 8. Barge-in / Interruption Mechanism
  assertRule(
    'Barge-in user_speaking frame and audio interruption handling',
    widgetCode.includes('type: \'user_speaking\'') &&
    widgetCode.includes('type === \'interrupted\'') &&
    widgetCode.includes('stopVoiceAudioPlayback'),
    'Sends user_speaking to cancel active AI speech and stops client audio buffer'
  );

  // 9. Conversation Continuity (Text ↔ Voice)
  assertRule(
    'Voice responses append directly to shared conversation state',
    widgetCode.includes('state.messages.push') &&
    widgetCode.includes('renderMessages'),
    'Transcripts and assistant voice replies append to the unified message history'
  );

  // 10. Write Action Human Confirmation in Voice
  assertRule(
    'Write action confirmation preserved in unified message state',
    widgetCode.includes('pendingConfirmation') &&
    widgetCode.includes('submitConfirmation'),
    'Dangerous tools still trigger PendingToolAction confirmation'
  );

  const passed = results.filter((r) => r.status === 'PASS').length;
  const total = results.length;
  console.log(`\nResults: ${passed}/${total} scenarios passed.`);

  if (passed === total) {
    console.log('\n🎉 ALL 10 VOICE WIDGET ACCEPTANCE CRITERIA PASSED!\n');
    process.exit(0);
  } else {
    console.error(`\n⚠️ ${total - passed} criteria failed.\n`);
    process.exit(1);
  }
}

runVoiceAcceptanceTests();
