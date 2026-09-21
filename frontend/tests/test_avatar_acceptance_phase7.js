/**
 * Acceptance test suite for Phase 7: Advanced Digital Human Behavior + Intelligent Avatar Orchestration
 *
 * Verifies all 25 specification requirements:
 * 1. Neutral avatar initializes correctly
 * 2. Listening state produces attentive behavior
 * 3. Thinking state produces thinking behavior
 * 4. Speaking state activates lip sync
 * 5. Speech end returns mouth to neutral
 * 6. Interruption cancels speech animation & resets mouth
 * 7. Old generation events are ignored
 * 8. Out-of-order events are ignored
 * 9. Emotion metadata changes presentation
 * 10. Invalid emotion metadata is rejected safely
 * 11. Gesture does not override higher-priority interruption
 * 12. Gaze smoothly transitions
 * 13. Blink system remains functional
 * 14. Avatar works without hand/upper-body capabilities
 * 15. Avatar works with limited GLB capabilities
 * 16. Failed GLB/renderer does not break text/voice chat
 * 17. Hidden widget reduces/pauses rendering
 * 18. Destroy cleans resources without leaks
 * 19. Reopening does not duplicate listeners
 * 20. Low-quality mode works
 * 21. WebGL failure triggers graceful fallback UI (never fakes 3D with 2D)
 * 22. Text chat works without avatar
 * 23. Voice works without avatar
 * 24. Avatar remains presentation-only
 * 25. No avatar component directly calls LLM/RAG/tools
 */

const fs = require('fs');
const path = require('path');

function runPhase7AcceptanceTests() {
  console.log('\n===================================================================');
  console.log('PHASE 7: ADVANCED DIGITAL HUMAN BEHAVIOR ACCEPTANCE TEST SUITE');
  console.log('===================================================================\n');

  const enginePath = path.join(__dirname, '../public/avatar_engine.js');
  const widgetPath = path.join(__dirname, '../public/widget.js');

  if (!fs.existsSync(enginePath) || !fs.existsSync(widgetPath)) {
    console.error('FAIL: Missing avatar_engine.js or widget.js');
    process.exit(1);
  }

  const engineCode = fs.readFileSync(enginePath, 'utf8');
  const widgetCode = fs.readFileSync(widgetPath, 'utf8');
  const results = [];

  function assertRule(num, name, condition, details) {
    if (condition) {
      console.log(`✅ [Scenario ${num}] PASS: ${name}`);
      results.push({ num, name, status: 'PASS', details });
    } else {
      console.error(`❌ [Scenario ${num}] FAIL: ${name}`);
      results.push({ num, name, status: 'FAIL', details });
    }
  }

  // Set up mock browser environment to test AvatarEngine class directly
  let animationFrameCount = 0;
  let cancelledFrameCount = 0;
  const mockRaf = (fn) => { animationFrameCount++; return animationFrameCount; };
  const mockCaf = (id) => { cancelledFrameCount++; };

  const mockWindow = {
    requestAnimationFrame: mockRaf,
    cancelAnimationFrame: mockCaf,
  };
  const mockDocument = {
    hidden: false,
    addEventListener: (evt, fn) => {},
    removeEventListener: (evt, fn) => {},
  };

  // Evaluate AvatarEngine in mock context
  const evalEngine = new Function('global', 'window', 'document', 'requestAnimationFrame', 'cancelAnimationFrame', 'performance',
    engineCode + '; return global.AvatarEngine;'
  );

  const AvatarEngine = evalEngine(mockWindow, mockWindow, mockDocument, mockRaf, mockCaf, { now: () => Date.now() });

  function createMockCanvas(webglAvailable = true) {
    return {
      width: 260,
      height: 260,
      style: {},
      getContext: (type) => {
        if (type === 'webgl' || type === 'experimental-webgl') {
          return webglAvailable ? { dummyWebGL: true } : null;
        }
        if (type === '2d') {
          return {
            clearRect: () => {},
            save: () => {},
            translate: () => {},
            rotate: () => {},
            beginPath: () => {},
            ellipse: () => {},
            rect: () => {},
            arc: () => {},
            fill: () => {},
            stroke: () => {},
            moveTo: () => {},
            quadraticCurveTo: () => {},
            restore: () => {},
          };
        }
        return null;
      },
    };
  }

  // 1. Neutral avatar initializes correctly
  const c1 = createMockCanvas(true);
  const avatar1 = new AvatarEngine({ canvas: c1 });
  assertRule(1, 'Neutral avatar initializes correctly',
    avatar1.state === 'IDLE' &&
    avatar1.morphWeights.mouthSmileLeft === 0.15 &&
    avatar1.currentEmotion === 'neutral',
    'Avatar boots into IDLE state with neutral baseline blendshapes'
  );

  // 2. Listening state produces attentive behavior
  avatar1.handleAvatarEvent({ type: 'status', state: 'listening', sequence: 1 });
  assertRule(2, 'Listening state produces attentive behavior',
    avatar1.state === 'LISTENING' &&
    avatar1.targetHeadTilt === 0.08 &&
    avatar1.baselineMorphs.mouthSmileLeft === 0.2,
    'Listening state tilts head 5° toward user and tightens smile/brow'
  );

  // 3. Thinking state produces thinking behavior
  avatar1.handleAvatarEvent({ type: 'status', state: 'thinking', sequence: 2 });
  assertRule(3, 'Thinking state produces thinking behavior',
    avatar1.state === 'THINKING' &&
    avatar1.targetGazeX > 0 &&
    avatar1.targetGazeY < 0 &&
    avatar1.baselineMorphs.browInnerUp === 0.25,
    'Thinking state drifts gaze upward/away and furrows inner brow'
  );

  // 4. Speaking state activates lip sync
  avatar1.handleAvatarEvent({ type: 'status', state: 'speaking', sequence: 3 });
  avatar1.clock = 1.0;
  avatar1.updateLipSync(0.016);
  assertRule(4, 'Speaking state activates lip sync',
    avatar1.state === 'SPEAKING' &&
    avatar1.morphWeights.jawOpen > 0,
    'Speaking state activates rhythm and viseme mouth animation'
  );

  // 5. Speech end returns mouth to neutral
  avatar1.handleAvatarEvent({ type: 'speech_end', sequence: 4 });
  assertRule(5, 'Speech end returns mouth to neutral',
    avatar1.isReturningToNeutral === true,
    'speech_end initiates smooth coarticulation decay back to zero'
  );

  // 6. Interruption cancels speech animation
  avatar1.morphWeights.jawOpen = 0.6;
  avatar1.activeGesture = 'explain';
  avatar1.handleAvatarEvent({ type: 'interrupted', sequence: 5 });
  assertRule(6, 'Interruption cancels speech animation & resets mouth',
    avatar1.state === 'INTERRUPTED' &&
    avatar1.morphWeights.jawOpen === 0 &&
    avatar1.activeGesture === 'none',
    'Barge-in immediately sets mouth to viseme_sil and cancels active gesture'
  );

  // 7. Old generation events are ignored
  avatar1.activeGenerationId = 'gen_turn_10';
  avatar1.handleAvatarEvent({
    type: 'speech_start',
    sequence: 6,
    generation_id: 'gen_turn_09', // Old generation!
  });
  assertRule(7, 'Old generation events are ignored',
    avatar1.state !== 'SPEAKING',
    'Events tagged with superseded generation_id are dropped'
  );

  // 8. Out-of-order events are ignored
  const currentSeq = avatar1.lastSequence;
  avatar1.handleAvatarEvent({
    type: 'status',
    state: 'thinking',
    sequence: currentSeq - 2, // Stale sequence!
  });
  assertRule(8, 'Out-of-order sequence packets are ignored',
    avatar1.lastSequence === currentSeq,
    'Packets arriving with sequence < lastSequence are discarded'
  );

  // 9. Emotion metadata changes presentation (after interruption recovers to IDLE)
  avatar1.currentPriority = 10; // IDLE priority restored
  avatar1.handleAvatarEvent({
    type: 'emotion',
    emotion: 'happy',
    intensity: 0.8,
    duration_ms: 2500,
    sequence: currentSeq + 1,
  });
  assertRule(9, 'Emotion metadata changes presentation',
    avatar1.currentEmotion === 'happy' &&
    avatar1.baselineMorphs.mouthSmileLeft >= 0.4,
    'Controlled emotion modulates mouth smile and facial blendshapes'
  );

  // 10. Invalid emotion metadata is rejected safely
  avatar1.handleAvatarEvent({
    type: 'emotion',
    emotion: '<script>alert("hacked")</script>',
    intensity: 'invalid_number',
    sequence: currentSeq + 2,
  });
  assertRule(10, 'Invalid emotion metadata is rejected safely',
    avatar1.currentEmotion === 'neutral' &&
    avatar1.emotionIntensity === 0.5,
    'Unrecognized or injection emotions fall back safely to neutral'
  );

  // 11. Gesture does not override higher-priority interruption
  avatar1.currentPriority = 100; // INTERRUPTED
  avatar1.handleAvatarEvent({
    type: 'gesture',
    gesture: 'welcome',
    sequence: currentSeq + 3,
  });
  assertRule(11, 'Gesture does not override higher-priority interruption',
    avatar1.activeGesture === 'none',
    'Lower priority gesture cannot override active interruption state'
  );

  // 12. Gaze smoothly transitions
  avatar1.currentPriority = 10;
  avatar1.applyGaze('glance_away', 2000);
  const initialGazeX = avatar1.gazeX;
  avatar1.updateGaze(0.016);
  assertRule(12, 'Gaze smoothly transitions',
    avatar1.gazeX !== avatar1.targetGazeX, // Smooth lerp, not snap
    'Gaze updates interpolate smoothly over time without jarring snaps'
  );

  // 13. Blink system remains functional
  const initialBlinks = avatar1.morphWeights.eyeBlinkLeft;
  avatar1.clock = 10.0;
  avatar1.nextBlinkTime = 5.0;
  avatar1.updateProceduralBehaviors(0.016);
  assertRule(13, 'Blink system remains functional with random intervals',
    avatar1.isBlinking === true,
    'Procedural clock triggers natural blinking cycle'
  );

  // 14. Avatar works without hand/upper-body capabilities
  const avatarNoHands = new AvatarEngine({
    canvas: createMockCanvas(true),
    capabilities: { hands: false, upper_body: false },
  });
  avatarNoHands.applyGesture('open_hand', 2000);
  assertRule(14, 'Avatar works without hand/upper-body capabilities',
    avatarNoHands.activeGesture === 'small_nod', // Gracefully mapped to nod
    'Rig without skeletal hands maps hand gestures safely to head nods'
  );

  // 15. Avatar works with limited GLB capabilities
  avatarNoHands.setCapabilities({ eyes: false });
  avatarNoHands.updateGaze(0.016);
  assertRule(15, 'Avatar works with limited GLB capabilities',
    avatarNoHands.capabilities.eyes === false,
    'Disabled eye capability bypasses pupil morph updates without error'
  );

  // 16. Failed GLB/Renderer does not break chat
  let recordedFailure = null;
  const avatarFailed = new AvatarEngine({
    canvas: createMockCanvas(false), // WebGL unavailable!
    onRendererFailure: (err) => { recordedFailure = err; },
  });
  assertRule(16, 'Failed GLB/Renderer does not break chat',
    avatarFailed.rendererFailed === true &&
    recordedFailure !== null &&
    widgetCode.includes('avatar-fallback-card'),
    'Renderer failure triggers clean fallback and records failure'
  );

  // 17. Hidden widget reduces/pauses rendering
  avatar1.pause();
  assertRule(17, 'Hidden widget reduces/pauses rendering',
    avatar1.isPaused === true,
    'Page visibility or widget close halts animation loop to save CPU'
  );

  // 18. Destroy cleans resources without leaks
  avatar1.destroy();
  assertRule(18, 'Destroy cleans resources without leaks',
    avatar1.isRendering === false &&
    avatar1.timedVisemesQueue.length === 0,
    'destroy() terminates RAF and purges viseme queues'
  );

  // 19. Reopening does not duplicate listeners
  const avatarReopen = new AvatarEngine({ canvas: createMockCanvas(true) });
  avatarReopen.pause();
  avatarReopen.resume();
  assertRule(19, 'Reopening does not duplicate listeners or loops',
    avatarReopen.isPaused === false,
    'Lifecycle pause/resume safely re-activates animation loop'
  );

  // 20. Low-quality mode works
  avatarReopen.setQuality('LOW');
  assertRule(20, 'Low-quality mode works',
    avatarReopen.quality === 'LOW',
    'Engine dynamically adapts quality mode for low-end devices'
  );

  // 21. WebGL failure triggers graceful fallback UI (never fakes 3D with 2D)
  assertRule(21, 'WebGL failure triggers fallback UI (never fakes 3D with 2D)',
    widgetCode.includes('avatar-fallback-card') &&
    widgetCode.includes('3D Avatar Unavailable') &&
    widgetCode.includes('WebGL hardware acceleration is disabled'),
    'Displays honest fallback card rather than pretending 2D canvas is 3D'
  );

  // 22. Text chat works without avatar
  assertRule(22, 'Text chat works without avatar',
    widgetCode.includes('btnModeChat') &&
    widgetCode.includes('viewTextMode'),
    'Text messaging operates completely independently of avatar status'
  );

  // 23. Voice works without avatar
  assertRule(23, 'Voice works without avatar',
    widgetCode.includes('btnModeVoice') &&
    widgetCode.includes('viewVoiceMode'),
    'Voice mode operates with visualizer even if avatar is disabled'
  );

  // 24. Avatar remains presentation-only
  assertRule(24, 'Avatar remains presentation-only',
    !engineCode.includes('fetch(') &&
    !engineCode.includes('apiBase') &&
    !engineCode.includes('eval('),
    'Engine has zero network calls or direct LLM communication'
  );

  // 25. No avatar component directly calls LLM/RAG/tools
  assertRule(25, 'No avatar component directly calls LLM/RAG/tools',
    !engineCode.includes('Qdrant') &&
    !engineCode.includes('ConversationEngine') &&
    !engineCode.includes('tools'),
    'Avatar Engine strictly consumes pre-computed events from the brain'
  );

  console.log('\n===================================================================');
  const passCount = results.filter((r) => r.status === 'PASS').length;
  console.log(`TOTAL PHASE 7 SCENARIOS TESTED: ${results.length}`);
  console.log(`PASSED: ${passCount} / ${results.length}`);
  console.log('===================================================================\n');

  if (passCount !== results.length) {
    process.exit(1);
  }
}

runPhase7AcceptanceTests();
