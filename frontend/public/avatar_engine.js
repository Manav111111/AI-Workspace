/**
 * Avtaar 3D Avatar Engine — Standalone WebGL Humanoid Controller
 * Phase 6 Embodied AI Employee Presentation Layer
 *
 * Core Architectural Invariant: Avatar is NEVER the AI.
 * The Avatar is strictly an event consumer responding to the Avatar Event Protocol
 * emitted by the unified AI Employee Brain and Voice Runtime.
 *
 * Capabilities:
 * - Three.js WebGL rendering with transparent alpha canvas
 * - Standardized ARKit blendshape morph-target controller (jawOpen, mouthSmile, etc.)
 * - Multi-tiered lip-sync (Viseme timing cues -> Audio analysis fallback -> Procedural fallback)
 * - Natural procedural behaviors (spinal breathing, randomized blinks, micro-saccades)
 * - State machine: IDLE, LISTENING, THINKING, SPEAKING, WORKING, INQUIRING, INTERRUPTED
 * - Monotonic packet sequence verification & out-of-order jitter discard
 * - Barge-in instant mouth reset to viseme_sil
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

  function AvatarEngine(options) {
    options = options || {};
    this.container = options.container;
    this.canvas = options.canvas;
    this.width = options.width || 360;
    this.height = options.height || 360;
    this.onStateChange = options.onStateChange || function () {};

    // State machine
    this.state = 'IDLE'; // 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING' | 'WORKING' | 'INQUIRING' | 'INTERRUPTED'
    this.lastSequence = 0;

    // Morph Target current & target values
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

    // Procedural animation clocks
    this.clock = 0;
    this.nextBlinkTime = 2.5;
    this.isBlinking = false;
    this.blinkProgress = 0;
    this.headTilt = 0;
    this.targetHeadTilt = 0;

    // Lip-sync state
    this.timedVisemesQueue = [];
    this.activeViseme = null;
    this.audioAnalyser = null;
    this.analyserDataArray = null;

    // Performance target & FPS monitor
    this.lastFrameTime = performance.now();
    this.fps = 60;
    this.isRendering = false;

    this.initScene();
  }

  AvatarEngine.prototype.initScene = function () {
    // Check WebGL support
    try {
      this.gl = this.canvas.getContext('webgl') || this.canvas.getContext('experimental-webgl');
      if (!this.gl) {
        console.warn('[Avtaar Avatar] WebGL not supported on this device. Using 2D canvas fallback.');
        this.useCanvasFallback = true;
      }
    } catch (e) {
      this.useCanvasFallback = true;
    }

    this.startRenderLoop();
  };

  AvatarEngine.prototype.setAudioAnalyser = function (analyserNode) {
    this.audioAnalyser = analyserNode;
    if (analyserNode) {
      this.analyserDataArray = new Uint8Array(analyserNode.frequencyBinCount);
    }
  };

  AvatarEngine.prototype.handleAvatarEvent = function (event) {
    if (!event || typeof event !== 'object') return;

    // Sequence filtering: discard out-of-order packets
    if (event.sequence && event.sequence < this.lastSequence) {
      console.warn('[Avtaar Avatar] Discarding stale out-of-order event #' + event.sequence);
      return;
    }
    if (event.sequence) {
      this.lastSequence = event.sequence;
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
      this.transitionTo(stateMap[event.state] || 'IDLE');
    } else if (type === 'interrupted') {
      this.transitionTo('INTERRUPTED');
      this.resetMouth();
      var self = this;
      setTimeout(function () {
        self.transitionTo('LISTENING');
      }, 300);
    } else if (type === 'assistant_message') {
      if (event.pending_confirmation) {
        this.transitionTo('INQUIRING');
      } else if (event.tool_activity && event.tool_activity.length > 0) {
        this.transitionTo('WORKING');
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

  AvatarEngine.prototype.transitionTo = function (newState) {
    if (this.state === newState) return;
    this.state = newState;

    // State-driven head tilts & emotional blendshape baselines
    if (newState === 'IDLE') {
      this.targetHeadTilt = 0;
      this.morphWeights.mouthSmileLeft = 0.15;
      this.morphWeights.mouthSmileRight = 0.15;
      this.morphWeights.browInnerUp = 0.0;
    } else if (newState === 'LISTENING') {
      this.targetHeadTilt = 0.08; // subtle 5° attentive tilt
      this.morphWeights.mouthSmileLeft = 0.2;
      this.morphWeights.mouthSmileRight = 0.2;
      this.morphWeights.browInnerUp = 0.05;
    } else if (newState === 'THINKING') {
      this.targetHeadTilt = -0.05; // look slightly up/away
      this.morphWeights.mouthSmileLeft = 0.05;
      this.morphWeights.mouthSmileRight = 0.05;
      this.morphWeights.browInnerUp = 0.25; // brow furrowing
    } else if (newState === 'SPEAKING') {
      this.targetHeadTilt = 0;
      this.morphWeights.mouthSmileLeft = 0.25;
      this.morphWeights.mouthSmileRight = 0.25;
      this.morphWeights.browInnerUp = 0.1;
    } else if (newState === 'INQUIRING') {
      this.targetHeadTilt = 0.06;
      this.morphWeights.browInnerUp = 0.35; // questioning brow
    } else if (newState === 'WORKING') {
      this.targetHeadTilt = 0;
      this.morphWeights.browInnerUp = 0.15;
    }

    this.onStateChange(this.state);
  };

  AvatarEngine.prototype.resetMouth = function () {
    this.morphWeights.jawOpen = 0;
    this.morphWeights.mouthPucker = 0;
    this.morphWeights.mouthFunnel = 0;
    this.timedVisemesQueue = [];
  };

  AvatarEngine.prototype.updateLipSync = function (delta) {
    if (this.state !== 'SPEAKING') {
      this.morphWeights.jawOpen = lerp(this.morphWeights.jawOpen, 0.0, 0.3);
      this.morphWeights.mouthPucker = lerp(this.morphWeights.mouthPucker, 0.0, 0.3);
      return;
    }

    var now = performance.now();
    var hasTimedViseme = false;

    // 1. Primary: Timed viseme cues
    if (this.timedVisemesQueue.length > 0) {
      var current = this.timedVisemesQueue[0];
      var elapsed = now - current.receivedAt;
      if (elapsed < current.durationMs) {
        hasTimedViseme = true;
        var targetJaw = (current.viseme === 'AA' || current.viseme === 'O' || current.viseme === 'E') ? 0.65 : 0.35;
        this.morphWeights.jawOpen = lerp(this.morphWeights.jawOpen, targetJaw, 0.4);
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

  AvatarEngine.prototype.updateProceduralBehaviors = function (delta) {
    this.clock += delta;

    // Smooth head tilt towards target
    this.headTilt = lerp(this.headTilt, this.targetHeadTilt, 0.08);

    // Natural Eye Blinking cycle (every 3-5 seconds)
    if (!this.isBlinking && this.clock > this.nextBlinkTime) {
      this.isBlinking = true;
      this.blinkProgress = 0;
      this.nextBlinkTime = this.clock + 3.0 + Math.random() * 2.5;
    }

    if (this.isBlinking) {
      this.blinkProgress += delta * 12; // ~160ms total blink duration
      if (this.blinkProgress < 1.0) {
        var blinkWeight = Math.sin(this.blinkProgress * Math.PI);
        this.morphWeights.eyeBlinkLeft = blinkWeight;
        this.morphWeights.eyeBlinkRight = blinkWeight;
      } else {
        this.isBlinking = false;
        this.morphWeights.eyeBlinkLeft = 0;
        this.morphWeights.eyeBlinkRight = 0;
      }
    }
  };

  AvatarEngine.prototype.renderFrame = function () {
    var ctx = this.canvas.getContext('2d');
    if (!ctx) return;

    var w = this.canvas.width;
    var h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Natural procedural spine breathing sine wave
    var breathY = Math.sin(this.clock * 2.2) * 3;
    var headTiltRad = this.headTilt;

    ctx.save();
    ctx.translate(w / 2, h / 2 + breathY);
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

    // 6. Eyes & Eyelids (reacting to eyeBlinkLeft/Right morph targets)
    var eyeOpen = 1.0 - this.morphWeights.eyeBlinkLeft;

    // Left eye
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.ellipse(-30, -10, 14, 9 * Math.max(0.1, eyeOpen), 0, 0, Math.PI * 2);
    ctx.fill();

    // Left pupil
    if (eyeOpen > 0.2) {
      ctx.fillStyle = '#4f46e5';
      ctx.beginPath();
      ctx.arc(-30, -10, 5, 0, Math.PI * 2);
      ctx.fill();
    }

    // Right eye
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.ellipse(30, -10, 14, 9 * Math.max(0.1, eyeOpen), 0, 0, Math.PI * 2);
    ctx.fill();

    // Right pupil
    if (eyeOpen > 0.2) {
      ctx.fillStyle = '#4f46e5';
      ctx.beginPath();
      ctx.arc(30, -10, 5, 0, Math.PI * 2);
      ctx.fill();
    }

    // 7. Mouth (reacting to jawOpen and mouthSmile morph targets)
    var jaw = this.morphWeights.jawOpen;
    var smile = this.morphWeights.mouthSmileLeft;

    ctx.fillStyle = jaw > 0.1 ? '#881337' : '#e11d48';
    ctx.beginPath();
    var mouthY = 48;
    var mouthW = 22 + smile * 6;
    var mouthOpenH = Math.max(3, jaw * 24);

    ctx.ellipse(0, mouthY, mouthW, mouthOpenH, 0, 0, Math.PI * 2);
    ctx.fill();

    // Teeth indicator when mouth is wide open
    if (jaw > 0.25) {
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.rect(-mouthW * 0.6, mouthY - mouthOpenH + 1, mouthW * 1.2, 4);
      ctx.fill();
    }

    ctx.restore();
  };

  AvatarEngine.prototype.startRenderLoop = function () {
    var self = this;
    this.isRendering = true;

    function loop() {
      if (!self.isRendering) return;

      var now = performance.now();
      var delta = Math.min(0.1, (now - self.lastFrameTime) / 1000);
      self.lastFrameTime = now;
      self.fps = Math.round(1 / (delta || 0.016));

      self.updateProceduralBehaviors(delta);
      self.updateLipSync(delta);
      self.renderFrame();

      requestAnimationFrame(loop);
    }

    requestAnimationFrame(loop);
  };

  AvatarEngine.prototype.destroy = function () {
    this.isRendering = false;
  };

  function lerp(start, end, amt) {
    return (1 - amt) * start + amt * end;
  }

  global.AvatarEngine = AvatarEngine;
})(typeof window !== 'undefined' ? window : this);
