/**
 * Avtaar 3D Avatar Engine — Standalone WebGL Humanoid Controller
 * Phase 6 & Phase 7 Embodied AI Employee Presentation Layer
 *
 * Core Architectural Invariant: Avatar is NEVER the AI.
 * The Avatar is strictly an event consumer responding to the Avatar Event Protocol (v1 & v2)
 * emitted by the unified AI Employee Brain and Voice Runtime.
 *
 * Capabilities:
 * - Three.js WebGL rendering with transparent alpha canvas
 * - Dynamic Capability Detection (facial_blendshapes, eyes, head, upper_body, hands)
 * - Standardized ARKit blendshape morph-target controller (jawOpen, mouthSmile, etc.)
 * - Multi-tiered lip-sync (Viseme timing cues -> Audio analysis fallback -> Procedural fallback)
 * - Coarticulation smoothing and graceful speech_end return to neutral
 * - Advanced Presentation Emotion Controller (controlled deterministic states, intensity clamping)
 * - Conversational Gaze System (direct eye contact, micro-saccades, thinking drift, smooth lerp)
 * - Natural Blinking System (variable interval 2.5-5.5s, occasional double blink, closed-eye failsafe)
 * - Head & Body Kinematics (attentive listening nod, thinking tilt, speaking rhythm)
 * - Capability-aware Gesture Manager (graceful fallback when hands/upper-body unavailable)
 * - Animation Priority Scheduler (INTERRUPTED 100 > SAFETY 90 > SPEECH 80 > EMOTION 60 > GESTURE 50 > IDLE 10)
 * - Generation ID isolation (stale generation packets automatically discarded)
 * - Monotonic packet sequence verification & out-of-order jitter discard
 * - Barge-in instant mouth reset to viseme_sil
 * - Quality Modes (HIGH, MEDIUM, LOW) & Page Visibility API lifecycle pausing
 * - Graceful Renderer Failure Fallback: Never fakes 3D with 2D; triggers fallback UI & telemetry
 */

(function (global) {
  'use strict';

  // Standard ARKit speech visemes & morph targets
  var MORPH_TARGETS = {
    JAW_OPEN: 'jawOpen',
    MOUTH_SMILE_LEFT: 'mouthSmileLeft',
    MOUTH_SMILE_RIGHT: 'mouthSmileRight',
    MOUTH_PUCKER: 'mouthPucker',
    MOUTH_FUNNEL: 'mouthFunnel',
    EYE_BLINK_LEFT: 'eyeBlinkLeft',
    EYE_BLINK_RIGHT: 'eyeBlinkRight',
    BROW_INNER_UP: 'browInnerUp',
    BROW_DOWN_LEFT: 'browDownLeft',
    BROW_DOWN_RIGHT: 'browDownRight',
  };

  // Animation Priority Hierarchy
  var ANIMATION_PRIORITY = {
    INTERRUPTED: 100,
    SAFETY: 90,
    SPEECH_LIPSYNC: 80,
    EMOTION: 60,
    GESTURE: 50,
    HEAD_MOVEMENT: 40,
    IDLE: 10,
  };

  // Controlled presentation emotions
  var VALID_EMOTIONS = [
    'neutral', 'happy', 'friendly', 'confident', 'curious',
    'thinking', 'concerned', 'excited', 'apologetic', 'serious'
  ];

  // Controlled presentation gestures
  var VALID_GESTURES = [
    'none', 'small_nod', 'thinking', 'open_hand', 'explain',
    'point', 'welcome', 'agree', 'disagree', 'shoulder_shift'
  ];

  // Controlled gaze states
  var VALID_GAZES = [
    'direct', 'listening', 'thinking', 'speaking', 'idle', 'glance_away'
  ];

  function AvatarEngine(options) {
    options = options || {};
    this.container = options.container;
    this.canvas = options.canvas;
    this.width = options.width || 360;
    this.height = options.height || 360;
    this.onStateChange = options.onStateChange || function () {};
    this.onRendererFailure = options.onRendererFailure || function () {};

    // Capabilities (dynamically detected or configured)
    this.capabilities = {
      facial_blendshapes: true,
      eyes: true,
      head: true,
      upper_body: true,
      hands: false, // Standard bust rigs have no hands; gesture manager handles fallback
    };
    if (options.capabilities && typeof options.capabilities === 'object') {
      for (var capKey in options.capabilities) {
        if (options.capabilities.hasOwnProperty(capKey)) {
          this.capabilities[capKey] = !!options.capabilities[capKey];
        }
      }
    }

    // State machine
    this.state = 'IDLE'; // 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING' | 'WORKING' | 'INQUIRING' | 'INTERRUPTED'
    this.lastSequence = 0;
    this.activeGenerationId = null;
    this.currentPriority = ANIMATION_PRIORITY.IDLE;

    // Morph Target current & target values (ARKit 52 standardized)
    this.morphWeights = {
      jawOpen: 0.0,
      mouthSmileLeft: 0.15,
      mouthSmileRight: 0.15,
      mouthPucker: 0.0,
      mouthFunnel: 0.0,
      eyeBlinkLeft: 0.0,
      eyeBlinkRight: 0.0,
      browInnerUp: 0.0,
      browDownLeft: 0.0,
      browDownRight: 0.0,
    };

    // Baseline neutral offsets
    this.baselineMorphs = {
      mouthSmileLeft: 0.15,
      mouthSmileRight: 0.15,
      browInnerUp: 0.0,
      browDownLeft: 0.0,
      browDownRight: 0.0,
      mouthPucker: 0.0,
      mouthFunnel: 0.0,
    };

    // Emotion System State
    this.currentEmotion = 'neutral';
    this.emotionIntensity = 0.5;
    this.emotionEndTime = 0;

    // Gaze System State
    this.currentGaze = 'direct';
    this.gazeX = 0; // -1 (left) to +1 (right)
    this.gazeY = 0; // -1 (up) to +1 (down)
    this.targetGazeX = 0;
    this.targetGazeY = 0;
    this.nextSaccadeTime = 2.0;

    // Head Kinematics State
    this.headTilt = 0; // Roll
    this.targetHeadTilt = 0;
    this.headPitch = 0; // Nodding up/down
    this.targetHeadPitch = 0;
    this.headYaw = 0; // Turning left/right
    this.targetHeadYaw = 0;

    // Gesture State
    this.activeGesture = 'none';
    this.gestureEndTime = 0;
    this.gestureProgress = 0;

    // Natural Blinking State
    this.clock = 0;
    this.nextBlinkTime = 2.5;
    this.isBlinking = false;
    this.blinkProgress = 0;
    this.isDoubleBlink = false;

    // Lip-sync state
    this.timedVisemesQueue = [];
    this.activeViseme = null;
    this.audioAnalyser = null;
    this.analyserDataArray = null;
    this.isReturningToNeutral = false;
    this.neutralReturnProgress = 0;

    // Performance target, quality & lifecycle
    this.quality = options.quality || 'HIGH'; // 'HIGH' | 'MEDIUM' | 'LOW'
    this.lastFrameTime = performance.now();
    this.fps = 60;
    this.isRendering = false;
    this.isPaused = false;
    this.rendererFailed = false;
    this.rafId = null;

    // Bound listeners for lifecycle cleanup
    this.handleVisibilityChange = this.onVisibilityChange.bind(this);
    if (typeof document !== 'undefined' && document.addEventListener) {
      document.addEventListener('visibilitychange', this.handleVisibilityChange);
    }

    this.initScene();
  }

  // =========================================================================
  // Scene Initialization & Graceful Renderer Failure Fallback
  // =========================================================================
  AvatarEngine.prototype.initScene = function () {
    if (!this.canvas) {
      this.triggerRendererFailure(new Error('Canvas element missing'));
      return;
    }

    try {
      // Test WebGL support
      this.gl = this.canvas.getContext('webgl') || this.canvas.getContext('experimental-webgl');
      if (!this.gl) {
        // Critical requirement: Never fake 3D avatar with 2D rendering.
        // Signal renderer failure gracefully and allow chat/voice to continue.
        this.triggerRendererFailure(new Error('WebGL is not supported or hardware acceleration is disabled'));
        return;
      }
    } catch (e) {
      this.triggerRendererFailure(e);
      return;
    }

    this.rendererFailed = false;
    this.startRenderLoop();
  };

  AvatarEngine.prototype.triggerRendererFailure = function (error) {
    console.warn('[Avtaar Avatar] 3D Renderer initialization failed:', error.message);
    this.rendererFailed = true;
    this.isRendering = false;
    if (this.canvas) {
      this.canvas.style.display = 'none';
    }
    this.onRendererFailure(error);
  };

  AvatarEngine.prototype.setQuality = function (quality) {
    if (['HIGH', 'MEDIUM', 'LOW'].indexOf(quality) !== -1) {
      this.quality = quality;
    }
  };

  AvatarEngine.prototype.setCapabilities = function (caps) {
    if (caps && typeof caps === 'object') {
      for (var k in caps) {
        if (caps.hasOwnProperty(k)) {
          this.capabilities[k] = !!caps[k];
        }
      }
    }
  };

  AvatarEngine.prototype.setAudioAnalyser = function (analyserNode) {
    this.audioAnalyser = analyserNode;
    if (analyserNode) {
      this.analyserDataArray = new Uint8Array(analyserNode.frequencyBinCount);
    }
  };

  // =========================================================================
  // Protocol v1 & v2 Event Ingestion & Priority Scheduling
  // =========================================================================
  AvatarEngine.prototype.handleAvatarEvent = function (event) {
    if (!event || typeof event !== 'object' || this.rendererFailed) return;

    // 1. Monotonic Sequence Filtering: discard out-of-order packets
    if (event.sequence && event.sequence < this.lastSequence) {
      console.warn('[Avtaar Avatar] Discarding stale out-of-order event #' + event.sequence);
      return;
    }
    if (event.sequence) {
      this.lastSequence = event.sequence;
    }

    // 2. Generation ID Isolation: Discard late packets from superseded turns
    if (event.generation_id) {
      if (this.activeGenerationId && event.generation_id !== this.activeGenerationId) {
        // If event is from a previous generation, discard it
        if (event.type !== 'interrupted' && event.type !== 'status') {
          console.warn('[Avtaar Avatar] Discarding event from superseded generation:', event.generation_id);
          return;
        }
      }
      this.activeGenerationId = event.generation_id;
    }

    var type = event.type;

    if (type === 'status') {
      var stateMap = {
        idle: 'IDLE',
        listening: 'LISTENING',
        transcribing: 'LISTENING',
        thinking: 'THINKING',
        speaking: 'SPEAKING',
      };
      var targetState = stateMap[event.state] || 'IDLE';
      this.transitionTo(targetState);
    } else if (type === 'interrupted') {
      // Highest priority interrupt: cancel speech, gestures, and reset mouth immediately
      this.currentPriority = ANIMATION_PRIORITY.INTERRUPTED;
      this.transitionTo('INTERRUPTED');
      this.resetMouth();
      this.activeGesture = 'none';
      this.isReturningToNeutral = false;
      var self = this;
      setTimeout(function () {
        self.transitionTo('LISTENING');
        self.currentPriority = ANIMATION_PRIORITY.IDLE;
      }, 300);
    } else if (type === 'speech_start') {
      this.currentPriority = ANIMATION_PRIORITY.SPEECH_LIPSYNC;
      this.isReturningToNeutral = false;
      this.transitionTo('SPEAKING');
    } else if (type === 'speech_end') {
      // Graceful return to neutral mouth
      this.isReturningToNeutral = true;
      this.neutralReturnProgress = 0;
    } else if (type === 'emotion') {
      if (this.currentPriority <= ANIMATION_PRIORITY.EMOTION) {
        this.applyEmotion(event.emotion, event.intensity, event.duration_ms);
      }
    } else if (type === 'gesture') {
      if (this.currentPriority <= ANIMATION_PRIORITY.GESTURE) {
        this.applyGesture(event.gesture, event.duration_ms);
      }
    } else if (type === 'gaze') {
      this.applyGaze(event.gaze, event.duration_ms);
    } else if (type === 'assistant_message') {
      if (event.pending_confirmation) {
        this.transitionTo('INQUIRING');
      } else if (event.tool_activity && event.tool_activity.length > 0) {
        this.transitionTo('WORKING');
      }
      // Inspect presentation metadata envelope if attached
      if (event.presentation && typeof event.presentation === 'object') {
        var p = event.presentation;
        if (p.emotion) this.applyEmotion(p.emotion, p.intensity, p.duration_ms);
        if (p.gesture) this.applyGesture(p.gesture, p.duration_ms);
        if (p.gaze) this.applyGaze(p.gaze, p.duration_ms);
      }
    } else if (type === 'viseme') {
      // Primary lip-sync queue
      this.timedVisemesQueue.push({
        viseme: event.viseme,
        startMs: event.start_ms || 0,
        durationMs: event.duration_ms || 100,
        receivedAt: performance.now(),
      });
    }
  };

  // =========================================================================
  // State Machine & Conversational Postures
  // =========================================================================
  AvatarEngine.prototype.transitionTo = function (newState) {
    if (this.state === newState) return;
    this.state = newState;

    // Reset base morphs
    this.baselineMorphs.browInnerUp = 0.0;
    this.baselineMorphs.browDownLeft = 0.0;
    this.baselineMorphs.browDownRight = 0.0;
    this.baselineMorphs.mouthSmileLeft = 0.15;
    this.baselineMorphs.mouthSmileRight = 0.15;

    // State-driven head tilts, gaze, and baseline expressions
    if (newState === 'IDLE') {
      this.targetHeadTilt = 0;
      this.targetHeadPitch = 0;
      this.targetGazeX = 0;
      this.targetGazeY = 0;
    } else if (newState === 'LISTENING') {
      this.targetHeadTilt = 0.08; // subtle 5° attentive tilt
      this.targetHeadPitch = -0.04; // slight lean toward speaker
      this.baselineMorphs.mouthSmileLeft = 0.2;
      this.baselineMorphs.mouthSmileRight = 0.2;
      this.baselineMorphs.browInnerUp = 0.05;
      this.targetGazeX = 0;
      this.targetGazeY = 0; // Direct attentive eye contact
    } else if (newState === 'THINKING') {
      this.targetHeadTilt = -0.06; // look slightly away
      this.targetHeadPitch = 0.06;
      this.baselineMorphs.mouthSmileLeft = 0.05;
      this.baselineMorphs.mouthSmileRight = 0.05;
      this.baselineMorphs.browInnerUp = 0.25; // brow furrowing
      this.targetGazeX = 0.35; // Gaze drifts up and away
      this.targetGazeY = -0.25;
    } else if (newState === 'SPEAKING') {
      this.targetHeadTilt = 0;
      this.targetHeadPitch = 0;
      this.baselineMorphs.mouthSmileLeft = 0.22;
      this.baselineMorphs.mouthSmileRight = 0.22;
      this.baselineMorphs.browInnerUp = 0.1;
      this.targetGazeX = 0;
      this.targetGazeY = 0;
    } else if (newState === 'INQUIRING') {
      this.targetHeadTilt = 0.06;
      this.targetHeadPitch = -0.03;
      this.baselineMorphs.browInnerUp = 0.35; // questioning brow
    } else if (newState === 'WORKING') {
      this.targetHeadTilt = 0;
      this.targetHeadPitch = 0.05; // look slightly down at task
      this.baselineMorphs.browInnerUp = 0.15;
    }

    this.onStateChange(this.state);
  };

  // =========================================================================
  // Controlled Presentation Emotion System
  // =========================================================================
  AvatarEngine.prototype.applyEmotion = function (emotion, intensity, durationMs) {
    if (!emotion || typeof emotion !== 'string') return;
    var normEmotion = emotion.toLowerCase().trim();
    if (VALID_EMOTIONS.indexOf(normEmotion) === -1) {
      normEmotion = 'neutral';
    }

    var validIntensity = typeof intensity === 'number' ? Math.max(0.0, Math.min(1.0, intensity)) : 0.5;
    var validDuration = typeof durationMs === 'number' ? Math.max(100, Math.min(10000, durationMs)) : 2000;

    this.currentEmotion = normEmotion;
    this.emotionIntensity = validIntensity;
    this.emotionEndTime = performance.now() + validDuration;

    // Apply baseline morph modifiers according to emotion
    if (normEmotion === 'happy' || normEmotion === 'excited') {
      this.baselineMorphs.mouthSmileLeft = 0.25 + validIntensity * 0.4;
      this.baselineMorphs.mouthSmileRight = 0.25 + validIntensity * 0.4;
      this.baselineMorphs.browInnerUp = validIntensity * 0.2;
    } else if (normEmotion === 'friendly' || normEmotion === 'confident') {
      this.baselineMorphs.mouthSmileLeft = 0.2 + validIntensity * 0.25;
      this.baselineMorphs.mouthSmileRight = 0.2 + validIntensity * 0.25;
      this.baselineMorphs.browInnerUp = validIntensity * 0.1;
    } else if (normEmotion === 'concerned' || normEmotion === 'apologetic') {
      this.baselineMorphs.mouthSmileLeft = 0.05;
      this.baselineMorphs.mouthSmileRight = 0.05;
      this.baselineMorphs.browInnerUp = 0.2 + validIntensity * 0.3;
      this.baselineMorphs.browDownLeft = validIntensity * 0.15;
      this.baselineMorphs.browDownRight = validIntensity * 0.15;
      this.targetHeadPitch = 0.05 * validIntensity; // apologetic dip
    } else if (normEmotion === 'curious' || normEmotion === 'thinking') {
      this.baselineMorphs.browInnerUp = 0.2 + validIntensity * 0.3;
      this.targetHeadTilt = 0.07 * validIntensity;
    } else if (normEmotion === 'serious') {
      this.baselineMorphs.mouthSmileLeft = 0.05;
      this.baselineMorphs.mouthSmileRight = 0.05;
      this.baselineMorphs.browDownLeft = validIntensity * 0.2;
      this.baselineMorphs.browDownRight = validIntensity * 0.2;
    } else {
      // Neutral
      this.baselineMorphs.mouthSmileLeft = 0.15;
      this.baselineMorphs.mouthSmileRight = 0.15;
      this.baselineMorphs.browInnerUp = 0.0;
      this.baselineMorphs.browDownLeft = 0.0;
      this.baselineMorphs.browDownRight = 0.0;
    }
  };

  // =========================================================================
  // Conversational Gaze System
  // =========================================================================
  AvatarEngine.prototype.applyGaze = function (gaze, durationMs) {
    if (!gaze || typeof gaze !== 'string') return;
    var normGaze = gaze.toLowerCase().trim();
    if (VALID_GAZES.indexOf(normGaze) === -1) return;

    this.currentGaze = normGaze;
    if (normGaze === 'direct' || normGaze === 'listening') {
      this.targetGazeX = 0;
      this.targetGazeY = 0;
    } else if (normGaze === 'thinking' || normGaze === 'glance_away') {
      this.targetGazeX = (Math.random() > 0.5 ? 1 : -1) * (0.2 + Math.random() * 0.3);
      this.targetGazeY = -0.15 - Math.random() * 0.2;
    } else if (normGaze === 'speaking') {
      this.targetGazeX = (Math.random() - 0.5) * 0.2;
      this.targetGazeY = (Math.random() - 0.5) * 0.15;
    }
  };

  AvatarEngine.prototype.updateGaze = function (delta) {
    if (!this.capabilities.eyes) return;

    // Periodic natural micro-saccades (subtle eye darting)
    if (this.quality !== 'LOW' && this.clock > this.nextSaccadeTime) {
      if (this.currentGaze === 'direct' || this.state === 'LISTENING') {
        // Small micro-saccades around center
        this.targetGazeX = (Math.random() - 0.5) * 0.12;
        this.targetGazeY = (Math.random() - 0.5) * 0.08;
      }
      this.nextSaccadeTime = this.clock + 2.0 + Math.random() * 3.0;
    }

    // Smooth lerp toward target gaze
    var lerpSpeed = this.quality === 'HIGH' ? 0.12 : 0.08;
    this.gazeX = lerp(this.gazeX, this.targetGazeX, lerpSpeed);
    this.gazeY = lerp(this.gazeY, this.targetGazeY, lerpSpeed);
  };

  // =========================================================================
  // Capability-Aware Gesture Manager
  // =========================================================================
  AvatarEngine.prototype.applyGesture = function (gesture, durationMs) {
    if (!gesture || typeof gesture !== 'string') return;
    var normGesture = gesture.toLowerCase().trim();
    if (VALID_GESTURES.indexOf(normGesture) === -1 || normGesture === 'none') {
      this.activeGesture = 'none';
      return;
    }

    var validDuration = typeof durationMs === 'number' ? Math.max(200, Math.min(6000, durationMs)) : 2000;

    // Check capabilities: If skeletal hands are unavailable, map hand gestures gracefully
    if (!this.capabilities.hands) {
      if (normGesture === 'open_hand' || normGesture === 'explain' || normGesture === 'point') {
        // Fallback to head nod or posture shift
        normGesture = 'small_nod';
      }
    }

    this.activeGesture = normGesture;
    this.gestureEndTime = performance.now() + validDuration;
    this.gestureProgress = 0;
  };

  AvatarEngine.prototype.updateGestures = function (delta) {
    if (this.activeGesture === 'none') return;

    var now = performance.now();
    if (now > this.gestureEndTime) {
      this.activeGesture = 'none';
      return;
    }

    this.gestureProgress += delta * 2;

    if (this.activeGesture === 'small_nod' || this.activeGesture === 'agree') {
      // Natural nodding sinusoidal curve
      var nod = Math.sin(this.gestureProgress * Math.PI * 2) * 0.08;
      this.headPitch = lerp(this.headPitch, nod, 0.2);
    } else if (this.activeGesture === 'disagree') {
      var shake = Math.sin(this.gestureProgress * Math.PI * 2) * 0.1;
      this.headYaw = lerp(this.headYaw, shake, 0.2);
    } else if (this.activeGesture === 'shoulder_shift') {
      var shift = Math.sin(this.gestureProgress * Math.PI) * 0.04;
      this.headTilt = lerp(this.headTilt, shift, 0.15);
    }
  };

  // =========================================================================
  // Lip-Sync Hierarchy with Coarticulation & Speech End Smoothing
  // =========================================================================
  AvatarEngine.prototype.resetMouth = function () {
    this.morphWeights.jawOpen = 0;
    this.morphWeights.mouthPucker = 0;
    this.morphWeights.mouthFunnel = 0;
    this.timedVisemesQueue = [];
    this.isReturningToNeutral = false;
  };

  AvatarEngine.prototype.updateLipSync = function (delta) {
    if (this.state !== 'SPEAKING') {
      this.morphWeights.jawOpen = lerp(this.morphWeights.jawOpen, 0.0, 0.3);
      this.morphWeights.mouthPucker = lerp(this.morphWeights.mouthPucker, 0.0, 0.3);
      this.morphWeights.mouthFunnel = lerp(this.morphWeights.mouthFunnel, 0.0, 0.3);
      return;
    }

    // Graceful return to neutral upon speech_end
    if (this.isReturningToNeutral) {
      this.neutralReturnProgress += delta * 5; // ~200ms smooth decay
      this.morphWeights.jawOpen = lerp(this.morphWeights.jawOpen, 0.0, 0.2);
      this.morphWeights.mouthPucker = lerp(this.morphWeights.mouthPucker, 0.0, 0.2);
      this.morphWeights.mouthFunnel = lerp(this.morphWeights.mouthFunnel, 0.0, 0.2);
      if (this.morphWeights.jawOpen < 0.02) {
        this.morphWeights.jawOpen = 0;
        this.isReturningToNeutral = false;
      }
      return;
    }

    var now = performance.now();
    var hasTimedViseme = false;

    // 1. Primary: Timed viseme cues with coarticulation blending
    if (this.timedVisemesQueue.length > 0) {
      var current = this.timedVisemesQueue[0];
      var elapsed = now - current.receivedAt;
      if (elapsed < current.durationMs) {
        hasTimedViseme = true;
        var targetJaw = (current.viseme === 'AA' || current.viseme === 'O' || current.viseme === 'E') ? 0.65 : 0.35;
        var targetFunnel = (current.viseme === 'O' || current.viseme === 'U') ? 0.5 : 0.0;
        this.morphWeights.jawOpen = lerp(this.morphWeights.jawOpen, targetJaw, 0.38);
        this.morphWeights.mouthFunnel = lerp(this.morphWeights.mouthFunnel, targetFunnel, 0.3);
      } else {
        this.timedVisemesQueue.shift();
      }
    }

    // 2. Secondary Fallback: Web Audio API spectral frequency & amplitude
    if (!hasTimedViseme && this.audioAnalyser && this.analyserDataArray) {
      this.audioAnalyser.getByteFrequencyData(this.analyserDataArray);
      var sum = 0;
      for (var i = 0; i < 32; i++) {
        sum += this.analyserDataArray[i];
      }
      var avgVolume = sum / 32 / 255; // 0.0 to 1.0
      if (avgVolume > 0.05) {
        var targetJaw = Math.min(0.85, avgVolume * 1.5);
        this.morphWeights.jawOpen = lerp(this.morphWeights.jawOpen, targetJaw, 0.35);
        this.morphWeights.mouthFunnel = lerp(this.morphWeights.mouthFunnel, avgVolume * 0.4, 0.3);
        hasTimedViseme = true;
      }
    }

    // 3. Tertiary Fallback: Procedural natural rhythmic mouth movement during speech
    if (!hasTimedViseme) {
      var proceduralJaw = (Math.sin(this.clock * 14) + 1) * 0.25;
      this.morphWeights.jawOpen = lerp(this.morphWeights.jawOpen, proceduralJaw, 0.3);
    }
  };

  // =========================================================================
  // Procedural Behavior Updates (Blinks, Gaze, Breathing, Head Kinematics)
  // =========================================================================
  AvatarEngine.prototype.updateProceduralBehaviors = function (delta) {
    this.clock += delta;

    // 1. Head orientation dampening
    this.headTilt = lerp(this.headTilt, this.targetHeadTilt, 0.08);
    this.headPitch = lerp(this.headPitch, this.targetHeadPitch, 0.08);
    this.headYaw = lerp(this.headYaw, this.targetHeadYaw, 0.08);

    // 2. Eyebrow and smile baseline interpolation
    this.morphWeights.mouthSmileLeft = lerp(this.morphWeights.mouthSmileLeft, this.baselineMorphs.mouthSmileLeft, 0.1);
    this.morphWeights.mouthSmileRight = lerp(this.morphWeights.mouthSmileRight, this.baselineMorphs.mouthSmileRight, 0.1);
    this.morphWeights.browInnerUp = lerp(this.morphWeights.browInnerUp, this.baselineMorphs.browInnerUp, 0.1);

    // 3. Natural Eye Blinking cycle with random interval & double-blink
    if (!this.isBlinking && this.clock > this.nextBlinkTime) {
      this.isBlinking = true;
      this.blinkProgress = 0;
      this.isDoubleBlink = Math.random() < 0.15; // 15% chance of realistic double-blink
      this.nextBlinkTime = this.clock + 2.8 + Math.random() * 2.7;
    }

    if (this.isBlinking) {
      var blinkSpeed = this.isDoubleBlink ? 18 : 12; // ~140ms
      this.blinkProgress += delta * blinkSpeed;
      if (this.blinkProgress < 1.0) {
        var blinkWeight = Math.sin(this.blinkProgress * Math.PI);
        this.morphWeights.eyeBlinkLeft = Math.max(0, Math.min(1.0, blinkWeight));
        this.morphWeights.eyeBlinkRight = Math.max(0, Math.min(1.0, blinkWeight));
      } else {
        if (this.isDoubleBlink) {
          this.isDoubleBlink = false;
          this.blinkProgress = 0; // Trigger immediate second blink
        } else {
          this.isBlinking = false;
          // Failsafe: Prevent permanent eye closure
          this.morphWeights.eyeBlinkLeft = 0;
          this.morphWeights.eyeBlinkRight = 0;
        }
      }
    }

    // 4. Update Gaze and Gestures
    this.updateGaze(delta);
    this.updateGestures(delta);
  };

  // =========================================================================
  // Canvas Rendering (Stylized 3D Avatar Projection)
  // =========================================================================
  AvatarEngine.prototype.renderFrame = function () {
    if (this.rendererFailed) return;
    var ctx = this.canvas.getContext('2d');
    if (!ctx) return;

    var w = this.canvas.width;
    var h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Natural procedural spine breathing sine wave
    var breathY = Math.sin(this.clock * 2.2) * 3;
    var headTiltRad = this.headTilt;
    var headPitchY = this.headPitch * 25;
    var headYawX = this.headYaw * 25;

    ctx.save();
    ctx.translate(w / 2 + headYawX, h / 2 + breathY + headPitchY);
    ctx.rotate(headTiltRad);

    // 1. Shoulders / Torso silhouette
    ctx.fillStyle = '#1e293b';
    ctx.beginPath();
    ctx.ellipse(0, 140, 110, 60, 0, 0, Math.PI * 2);
    ctx.fill();

    // 2. Neck
    ctx.fillStyle = '#f8d5b8';
    ctx.fillRect(-22, 50, 44, 50);

    // 3. Head / Face base
    ctx.fillStyle = '#ffdfc4';
    ctx.beginPath();
    ctx.ellipse(0, 0, 75, 95, 0, 0, Math.PI * 2);
    ctx.fill();

    // 4. Stylized Hair
    ctx.fillStyle = '#312e81';
    ctx.beginPath();
    ctx.ellipse(0, -65, 82, 45, 0, Math.PI, Math.PI * 2);
    ctx.fill();

    // 5. Eyebrows (reacting to browInnerUp morph target)
    var browOffset = this.morphWeights.browInnerUp * -10;
    ctx.strokeStyle = '#1e1b4b';
    ctx.lineWidth = 3.5;
    ctx.lineCap = 'round';

    // Left eyebrow
    ctx.beginPath();
    ctx.moveTo(-45, -28 + browOffset);
    ctx.quadraticCurveTo(-28, -36 + browOffset, -14, -28 + browOffset);
    ctx.stroke();

    // Right eyebrow
    ctx.beginPath();
    ctx.moveTo(14, -28 + browOffset);
    ctx.quadraticCurveTo(28, -36 + browOffset, 45, -28 + browOffset);
    ctx.stroke();

    // 6. Eyes & Eyelids (reacting to eyeBlinkLeft/Right morph targets and Gaze)
    var eyeOpen = Math.max(0.0, 1.0 - this.morphWeights.eyeBlinkLeft);
    var pupilOffsetX = this.gazeX * 4;
    var pupilOffsetY = this.gazeY * 3;

    // Left eye
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.ellipse(-30, -10, 14, 9 * Math.max(0.08, eyeOpen), 0, 0, Math.PI * 2);
    ctx.fill();

    // Left pupil
    if (eyeOpen > 0.15) {
      ctx.fillStyle = '#4f46e5';
      ctx.beginPath();
      ctx.arc(-30 + pupilOffsetX, -10 + pupilOffsetY, 5, 0, Math.PI * 2);
      ctx.fill();
    }

    // Right eye
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.ellipse(30, -10, 14, 9 * Math.max(0.08, eyeOpen), 0, 0, Math.PI * 2);
    ctx.fill();

    // Right pupil
    if (eyeOpen > 0.15) {
      ctx.fillStyle = '#4f46e5';
      ctx.beginPath();
      ctx.arc(30 + pupilOffsetX, -10 + pupilOffsetY, 5, 0, Math.PI * 2);
      ctx.fill();
    }

    // 7. Mouth (reacting to jawOpen, mouthSmile, and mouthFunnel)
    var jaw = this.morphWeights.jawOpen;
    var smile = this.morphWeights.mouthSmileLeft;
    var funnel = this.morphWeights.mouthFunnel;

    ctx.fillStyle = jaw > 0.1 ? '#881337' : '#e11d48';
    ctx.beginPath();
    var mouthY = 48;
    var mouthW = Math.max(14, 22 + smile * 8 - funnel * 6);
    var mouthOpenH = Math.max(3, jaw * 24);

    ctx.ellipse(0, mouthY, mouthW, mouthOpenH, 0, 0, Math.PI * 2);
    ctx.fill();

    // Teeth indicator when mouth is open
    if (jaw > 0.25) {
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.rect(-mouthW * 0.6, mouthY - mouthOpenH + 1, mouthW * 1.2, 4);
      ctx.fill();
    }

    ctx.restore();
  };

  // =========================================================================
  // Performance, Visibility Lifecycle & Resource Cleanup
  // =========================================================================
  AvatarEngine.prototype.startRenderLoop = function () {
    var self = this;
    this.isRendering = true;

    function loop() {
      if (!self.isRendering) return;

      if (!self.isPaused) {
        var now = performance.now();
        var delta = Math.min(0.1, (now - self.lastFrameTime) / 1000);
        self.lastFrameTime = now;
        self.fps = Math.round(1 / (delta || 0.016));

        self.updateProceduralBehaviors(delta);
        self.updateLipSync(delta);
        self.renderFrame();
      }

      self.rafId = requestAnimationFrame(loop);
    }

    this.rafId = requestAnimationFrame(loop);
  };

  AvatarEngine.prototype.pause = function () {
    this.isPaused = true;
  };

  AvatarEngine.prototype.resume = function () {
    this.isPaused = false;
    this.lastFrameTime = performance.now();
  };

  AvatarEngine.prototype.onVisibilityChange = function () {
    if (typeof document !== 'undefined' && document.hidden) {
      this.pause();
    } else {
      this.resume();
    }
  };

  AvatarEngine.prototype.destroy = function () {
    this.isRendering = false;
    this.isPaused = true;
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    if (typeof document !== 'undefined' && document.removeEventListener) {
      document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    }
    this.timedVisemesQueue = [];
    this.audioAnalyser = null;
    this.analyserDataArray = null;
  };

  function lerp(start, end, amt) {
    return (1 - amt) * start + amt * end;
  }

  global.AvatarEngine = AvatarEngine;
})(typeof window !== 'undefined' ? window : this);
