/**
 * Avtaar AI Employee Website Widget — Standalone JavaScript Bundle
 * Phase 4 Public Runtime Client
 *
 * Requirements:
 * - Standalone vanilla JavaScript IIFE — zero host React runtime dependency.
 * - Shadow DOM style isolation to prevent host site CSS collisions.
 * - Reads data-ai-employee / data-public-id and data-api-base from script tag.
 * - Authenticates anonymously via public session bearer token.
 * - Session token sent ONLY through Authorization: Bearer <token> header.
 * - Supports chat messaging, conversation restoration on reload, citations accordion,
 *   tool execution indicators, and human confirmation flow for write actions.
 * - Fully responsive: desktop floating window and mobile full-screen/bottom-sheet.
 */

(function () {
  'use strict';

  // Prevent multiple initializations on the same page
  if (window.__AVTAAR_WIDGET_INITIALIZED__) {
    return;
  }
  window.__AVTAAR_WIDGET_INITIALIZED__ = true;

  // 1. Locate current script and read attributes
  var scriptElement =
    document.currentScript ||
    (function () {
      var scripts = document.getElementsByTagName('script');
      for (var i = scripts.length - 1; i >= 0; i--) {
        if (
          scripts[i].getAttribute('data-ai-employee') ||
          scripts[i].getAttribute('data-public-id')
        ) {
          return scripts[i];
        }
      }
      return null;
    })();

  if (!scriptElement) {
    console.error('[Avtaar Widget] Could not locate <script> tag with data-ai-employee attribute.');
    return;
  }

  var publicId =
    scriptElement.getAttribute('data-ai-employee') ||
    scriptElement.getAttribute('data-public-id');
  var apiBase =
    scriptElement.getAttribute('data-api-base') ||
    (scriptElement.src ? new URL(scriptElement.src).origin + '/api/v1' : 'http://localhost:8000/api/v1');

  // Strip trailing slash if present
  if (apiBase.endsWith('/')) {
    apiBase = apiBase.slice(0, -1);
  }

  if (!publicId) {
    console.error('[Avtaar Widget] Missing required data-ai-employee attribute.');
    return;
  }

  // 2. Visitor identity (Untrusted correlation ID stored in localStorage only)
  var VISITOR_STORAGE_KEY = '_avtaar_visitor_id_' + publicId;
  var visitorId = null;
  try {
    visitorId = localStorage.getItem(VISITOR_STORAGE_KEY);
    if (!visitorId) {
      visitorId = 'vis_' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
      localStorage.setItem(VISITOR_STORAGE_KEY, visitorId);
    }
  } catch (e) {
    visitorId = 'vis_' + Math.random().toString(36).substring(2, 15);
  }

  // 3. Widget Runtime State
  var state = {
    isOpen: false,
    mode: 'chat', // 'chat' | 'voice' | 'avatar'
    publicConfig: null,
    sessionToken: null,
    sessionExpiresAt: null,
    messages: [],
    isLoading: false,
    isSending: false,
    errorMessage: null,
    pendingConfirmation: null,
    expandedCitationIndex: null,
    // Voice Mode State (Phase 5)
    voiceStatus: 'idle', // 'idle' | 'connecting' | 'listening' | 'transcribing' | 'thinking' | 'speaking'
    voiceTranscript: '',
    isRecording: false,
    audioQueue: [],
    isPlayingAudio: false,
  };

  // 4. Create Host Container & Shadow Root for CSS Isolation
  var hostContainer = document.createElement('div');
  hostContainer.id = 'avtaar-widget-root';
  hostContainer.style.position = 'fixed';
  hostContainer.style.zIndex = '2147483647';
  hostContainer.style.bottom = '0';
  hostContainer.style.right = '0';
  hostContainer.style.pointerEvents = 'none';

  var shadow = hostContainer.attachShadow({ mode: 'open' });
  document.body.appendChild(hostContainer);

  // 5. CSS Styles for Shadow DOM
  var styleSheet = document.createElement('style');
  styleSheet.textContent = `
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      -webkit-font-smoothing: antialiased;
    }

    .widget-wrap {
      position: fixed;
      display: flex;
      flex-direction: column;
      pointer-events: auto;
      z-index: 2147483647;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .pos-bottom-right {
      bottom: 24px;
      right: 24px;
      align-items: flex-end;
    }

    .pos-bottom-left {
      bottom: 24px;
      left: 24px;
      align-items: flex-start;
    }

    /* Launcher Button */
    .launcher-btn {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: var(--brand-color, #4f46e5);
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.2);
      border: 1px solid rgba(255, 255, 255, 0.15);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      outline: none;
      transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
      position: relative;
    }

    .launcher-btn:hover {
      transform: scale(1.06);
      box-shadow: 0 14px 28px -4px rgba(79, 70, 229, 0.45);
    }

    .launcher-btn:active {
      transform: scale(0.96);
    }

    .launcher-btn svg {
      width: 28px;
      height: 28px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
      transition: transform 0.2s ease;
    }

    /* Chat Window Container */
    .chat-window {
      width: 390px;
      max-width: calc(100vw - 32px);
      height: 600px;
      max-height: calc(100vh - 110px);
      background: #0f172a;
      color: #f8fafc;
      border-radius: 16px;
      box-shadow: 0 20px 35px -10px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.1);
      display: none;
      flex-direction: column;
      overflow: hidden;
      margin-bottom: 14px;
      animation: avtaarSlideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .chat-window.open {
      display: flex;
    }

    @keyframes avtaarSlideUp {
      from {
        opacity: 0;
        transform: translateY(16px) scale(0.97);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    /* Header */
    .chat-header {
      padding: 14px 18px;
      background: #1e293b;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .header-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .avatar-badge {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: var(--brand-color, #4f46e5);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      font-weight: 600;
      font-size: 15px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }

    .name-title {
      font-size: 14px;
      font-weight: 600;
      color: #f8fafc;
      line-height: 1.2;
    }

    .role-subtitle {
      font-size: 11px;
      color: #94a3b8;
      margin-top: 2px;
    }

    .close-btn {
      background: transparent;
      border: none;
      color: #94a3b8;
      cursor: pointer;
      padding: 6px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s, color 0.15s;
    }

    .close-btn:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #ffffff;
    }

    /* Mode Switcher in Header */
    .mode-switch-wrap {
      display: flex;
      align-items: center;
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 20px;
      padding: 2px;
      gap: 2px;
    }

    .mode-btn {
      background: transparent;
      border: none;
      color: #94a3b8;
      font-size: 11.5px;
      font-weight: 500;
      padding: 3px 10px;
      border-radius: 16px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      transition: all 0.15s ease;
    }

    .mode-btn.active {
      background: var(--brand-color, #4f46e5);
      color: #ffffff;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
    }

    /* Voice Mode Container */
    .voice-panel {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px 20px;
      background: radial-gradient(circle at 50% 30%, rgba(79, 70, 229, 0.15), transparent 70%), #090e1a;
      text-align: center;
      position: relative;
    }

    .voice-status-pill {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 4px 12px;
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.07);
      color: #94a3b8;
      border: 1px solid rgba(255, 255, 255, 0.08);
      margin-bottom: 24px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .voice-status-pill.speaking {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border-color: rgba(52, 211, 153, 0.3);
    }

    .voice-status-pill.listening {
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
      border-color: rgba(248, 113, 113, 0.3);
    }

    .voice-status-pill.thinking {
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border-color: rgba(251, 191, 36, 0.3);
    }

    .voice-avatar-visualizer {
      width: 120px;
      height: 120px;
      border-radius: 50%;
      background: linear-gradient(135deg, rgba(79, 70, 229, 0.8), rgba(129, 140, 248, 0.5));
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 35px rgba(79, 70, 229, 0.4);
      position: relative;
      margin-bottom: 24px;
      transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .voice-avatar-visualizer.pulsing {
      animation: avtaarVoicePulse 1.8s infinite ease-in-out;
    }

    @keyframes avtaarVoicePulse {
      0% { transform: scale(1); box-shadow: 0 0 25px rgba(79, 70, 229, 0.3); }
      50% { transform: scale(1.08); box-shadow: 0 0 45px rgba(79, 70, 229, 0.6); }
      100% { transform: scale(1); box-shadow: 0 0 25px rgba(79, 70, 229, 0.3); }
    }

    .voice-transcript-preview {
      min-height: 48px;
      max-height: 90px;
      overflow-y: auto;
      font-size: 13.5px;
      color: #cbd5e1;
      line-height: 1.45;
      padding: 8px 14px;
      background: rgba(15, 23, 42, 0.6);
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.07);
      width: 100%;
      margin-bottom: 24px;
      word-break: break-word;
    }

    .voice-mic-btn {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: var(--brand-color, #4f46e5);
      border: 2px solid rgba(255, 255, 255, 0.2);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 8px 20px -4px rgba(79, 70, 229, 0.5);
      transition: all 0.2s ease;
      outline: none;
    }

    .voice-mic-btn:hover {
      transform: scale(1.06);
    }

    .voice-mic-btn.recording {
      background: #dc2626;
      border-color: #f87171;
      box-shadow: 0 0 25px rgba(220, 38, 38, 0.6);
      animation: avtaarMicPulse 1.2s infinite;
    }

    @keyframes avtaarMicPulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.08); }
    }

    .voice-hint {
      font-size: 11px;
      color: #64748b;
      margin-top: 12px;
    }

    /* Message Body */
    .chat-messages {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #090e1a;
    }

    .chat-messages::-webkit-scrollbar {
      width: 6px;
    }
    .chat-messages::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.15);
      border-radius: 3px;
    }

    .msg-row {
      display: flex;
      flex-direction: column;
      max-width: 86%;
    }

    .msg-user {
      align-self: flex-end;
      align-items: flex-end;
    }

    .msg-assistant {
      align-self: flex-start;
      align-items: flex-start;
    }

    .bubble {
      padding: 10px 14px;
      border-radius: 14px;
      font-size: 13.5px;
      line-height: 1.45;
      word-break: break-word;
      white-space: pre-wrap;
    }

    .bubble-user {
      background: var(--brand-color, #4f46e5);
      color: #ffffff;
      border-bottom-right-radius: 3px;
    }

    .bubble-assistant {
      background: #1e293b;
      color: #e2e8f0;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-bottom-left-radius: 3px;
    }

    .msg-time {
      font-size: 10px;
      color: #64748b;
      margin-top: 4px;
      padding: 0 4px;
    }

    /* Citations Accordion */
    .citations-box {
      margin-top: 8px;
      padding: 8px 10px;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: 8px;
      width: 100%;
    }

    .citations-header {
      font-size: 11px;
      font-weight: 600;
      color: #818cf8;
      display: flex;
      align-items: center;
      gap: 5px;
      cursor: pointer;
    }

    .citations-list {
      margin-top: 6px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .citation-item {
      font-size: 10.5px;
      color: #cbd5e1;
      background: rgba(30, 41, 59, 0.6);
      padding: 4px 8px;
      border-radius: 4px;
      display: flex;
      justify-content: space-between;
    }

    .citation-name {
      font-weight: 500;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 190px;
    }

    .citation-score {
      color: #38bdf8;
      font-family: monospace;
      font-size: 9.5px;
    }

    /* Tool Activity Badge */
    .tool-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 10.5px;
      font-family: monospace;
      color: #34d399;
      background: rgba(6, 78, 59, 0.4);
      border: 1px solid rgba(52, 211, 153, 0.3);
      padding: 3px 8px;
      border-radius: 6px;
      margin-top: 6px;
    }

    /* Action Confirmation Card (WRITE tools) */
    .confirm-card {
      margin-top: 10px;
      padding: 12px;
      background: rgba(120, 53, 15, 0.25);
      border: 1px solid rgba(245, 158, 11, 0.4);
      border-radius: 10px;
      width: 100%;
    }

    .confirm-title {
      font-size: 12px;
      font-weight: 600;
      color: #fbbf24;
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 6px;
    }

    .confirm-desc {
      font-size: 11.5px;
      color: #e2e8f0;
      margin-bottom: 8px;
    }

    .confirm-args {
      font-size: 10px;
      font-family: monospace;
      background: rgba(0, 0, 0, 0.4);
      padding: 6px;
      border-radius: 4px;
      color: #94a3b8;
      max-height: 80px;
      overflow-y: auto;
      margin-bottom: 10px;
    }

    .confirm-actions {
      display: flex;
      gap: 8px;
    }

    .btn-confirm {
      flex: 1;
      padding: 6px 12px;
      background: #f59e0b;
      color: #000;
      font-weight: 600;
      font-size: 11.5px;
      border-radius: 6px;
      border: none;
      cursor: pointer;
      transition: background 0.15s;
    }

    .btn-confirm:hover {
      background: #fbbf24;
    }

    .btn-cancel {
      padding: 6px 12px;
      background: rgba(255, 255, 255, 0.1);
      color: #cbd5e1;
      font-size: 11.5px;
      border-radius: 6px;
      border: none;
      cursor: pointer;
      transition: background 0.15s;
    }

    .btn-cancel:hover {
      background: rgba(255, 255, 255, 0.15);
      color: #ffffff;
    }

    /* Input Footer */
    .chat-footer {
      padding: 12px 14px;
      background: #1e293b;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .chat-input {
      flex: 1;
      background: #0f172a;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 13px;
      color: #f8fafc;
      outline: none;
      transition: border 0.15s;
    }

    .chat-input:focus {
      border-color: var(--brand-color, #4f46e5);
    }

    .chat-input::placeholder {
      color: #64748b;
    }

    .send-btn {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: var(--brand-color, #4f46e5);
      border: none;
      color: #ffffff;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s, opacity 0.15s;
      flex-shrink: 0;
    }

    .send-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .send-btn svg {
      width: 18px;
      height: 18px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    /* Typing indicator dots */
    .typing-indicator {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 8px 12px;
      background: #1e293b;
      border-radius: 12px;
      width: fit-content;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .typing-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #818cf8;
      animation: avtaarPulse 1.4s infinite ease-in-out both;
    }
    .typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .typing-dot:nth-child(2) { animation-delay: -0.16s; }

    @keyframes avtaarPulse {
      0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
      40% { transform: scale(1); opacity: 1; }
    }

    /* Mobile Viewport */
    @media (max-width: 640px) {
      .widget-wrap {
        bottom: 0 !important;
        right: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        align-items: flex-end;
      }
      .chat-window {
        width: 100vw !important;
        max-width: 100vw !important;
        height: 100vh !important;
        max-height: 100vh !important;
        border-radius: 0 !important;
        margin-bottom: 0 !important;
      }
      .launcher-btn {
        margin: 16px;
      }
    }
  `;
  shadow.appendChild(styleSheet);

  // 6. DOM Structure Generator
  var widgetWrap = document.createElement('div');
  widgetWrap.className = 'widget-wrap pos-bottom-right';

  // Floating Launcher Button
  var launcherBtn = document.createElement('button');
  launcherBtn.className = 'launcher-btn';
  launcherBtn.setAttribute('aria-label', 'Open AI Employee Chat');
  launcherBtn.innerHTML = `
    <svg viewBox="0 0 24 24">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    </svg>
  `;

  // Chat Window
  var chatWindow = document.createElement('div');
  chatWindow.className = 'chat-window';
  chatWindow.innerHTML = `
    <div class="chat-header">
      <div class="header-info">
        <div class="avatar-badge" id="avtaar-avatar">AI</div>
        <div>
          <div class="name-title" id="avtaar-name">AI Employee</div>
          <div class="role-subtitle" id="avtaar-role">Autonomous Assistant</div>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <div class="mode-switch-wrap">
          <button class="mode-btn active" id="btn-mode-chat">Chat</button>
          <button class="mode-btn" id="btn-mode-voice">Voice</button>
          <button class="mode-btn" id="btn-mode-avatar">Avatar</button>
        </div>
        <button class="close-btn" id="avtaar-close" aria-label="Close chat">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>
    
    <!-- Text Mode View -->
    <div id="view-text-mode" style="display: flex; flex-direction: column; flex: 1; overflow: hidden;">
      <div class="chat-messages" id="avtaar-messages"></div>
      <div class="chat-footer">
        <input type="text" class="chat-input" id="avtaar-input" placeholder="Type your message..." />
        <button class="send-btn" id="avtaar-send" aria-label="Send message">
          <svg viewBox="0 0 24 24">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
    </div>

    <!-- Voice Mode View -->
    <div id="view-voice-mode" class="voice-panel" style="display: none;">
      <div class="voice-status-pill" id="voice-status-pill">IDLE</div>
      <div class="voice-avatar-visualizer" id="voice-visualizer">
        <svg width="50" height="50" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
          <line x1="12" y1="19" x2="12" y2="23"></line>
          <line x1="8" y1="23" x2="16" y2="23"></line>
        </svg>
      </div>
      <div class="voice-transcript-preview" id="voice-transcript">Press microphone to speak with your AI employee...</div>
      <button class="voice-mic-btn" id="voice-mic-btn" aria-label="Toggle Microphone">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
          <line x1="12" y1="19" x2="12" y2="23"></line>
          <line x1="8" y1="23" x2="16" y2="23"></line>
        </svg>
      </button>
      <div class="voice-hint" id="voice-hint">Click mic to start • Click again to send • Click while AI speaks to barge-in</div>
    </div>

    <!-- Avatar 3D Mode View (Phase 6) -->
    <div id="view-avatar-mode" class="voice-panel" style="display: none; padding: 12px 16px;">
      <div class="voice-status-pill" id="avatar-status-pill">IDLE</div>
      <div style="width: 260px; height: 260px; position: relative; display: flex; align-items: center; justify-content: center; margin-bottom: 8px;">
        <canvas id="avatar-3d-canvas" width="260" height="260" style="width: 260px; height: 260px; border-radius: 16px; background: radial-gradient(circle at 50% 40%, rgba(99, 102, 241, 0.2), transparent 70%);"></canvas>
      </div>
      <div class="voice-transcript-preview" id="avatar-transcript" style="margin-bottom: 12px; min-height: 40px;">Embodied AI ready. Click mic to converse...</div>
      <button class="voice-mic-btn" id="avatar-mic-btn" aria-label="Toggle Microphone" style="width: 54px; height: 54px;">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
          <line x1="12" y1="19" x2="12" y2="23"></line>
          <line x1="8" y1="23" x2="16" y2="23"></line>
        </svg>
      </button>
    </div>
  `;

  widgetWrap.appendChild(chatWindow);
  widgetWrap.appendChild(launcherBtn);
  shadow.appendChild(widgetWrap);

  // References to UI elements
  var messagesContainer = shadow.getElementById('avtaar-messages');
  var inputElement = shadow.getElementById('avtaar-input');
  var sendBtn = shadow.getElementById('avtaar-send');
  var closeBtn = shadow.getElementById('avtaar-close');
  var nameElement = shadow.getElementById('avtaar-name');
  var roleElement = shadow.getElementById('avtaar-role');
  var avatarBadge = shadow.getElementById('avtaar-avatar');
  var btnModeChat = shadow.getElementById('btn-mode-chat');
  var btnModeVoice = shadow.getElementById('btn-mode-voice');
  var btnModeAvatar = shadow.getElementById('btn-mode-avatar');
  var viewTextMode = shadow.getElementById('view-text-mode');
  var viewVoiceMode = shadow.getElementById('view-voice-mode');
  var viewAvatarMode = shadow.getElementById('view-avatar-mode');
  var voiceStatusPill = shadow.getElementById('voice-status-pill');
  var avatarStatusPill = shadow.getElementById('avatar-status-pill');
  var voiceVisualizer = shadow.getElementById('voice-visualizer');
  var voiceTranscriptEl = shadow.getElementById('voice-transcript');
  var avatarTranscriptEl = shadow.getElementById('avatar-transcript');
  var voiceMicBtn = shadow.getElementById('voice-mic-btn');
  var avatarMicBtn = shadow.getElementById('avatar-mic-btn');
  var avatarCanvas = shadow.getElementById('avatar-3d-canvas');

  // 7. Security: HTTP Client using only Authorization: Bearer <session_token>
  function apiRequest(path, options) {
    options = options || {};
    var headers = options.headers || {};

    if (state.sessionToken) {
      headers['Authorization'] = 'Bearer ' + state.sessionToken;
    }
    if (options.body && typeof options.body === 'object') {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(options.body);
    }
    options.headers = headers;
    options.credentials = 'same-origin';

    return fetch(apiBase + path, options).then(function (response) {
      if (!response.ok) {
        return response.json().then(
          function (data) {
            var msg = (data && data.error && data.error.message) || data.detail || 'Request failed';
            throw new Error(msg);
          },
          function () {
            throw new Error('HTTP ' + response.status + ' ' + response.statusText);
          }
        );
      }
      return response.json();
    });
  }

  // 8. Bootstrap Public Configuration & Apply Custom Theme
  function fetchPublicConfig() {
    return apiRequest('/public/employees/' + encodeURIComponent(publicId) + '/config', {
      method: 'GET',
    })
      .then(function (config) {
        state.publicConfig = config;
        nameElement.textContent = config.name;
        roleElement.textContent = config.role;
        avatarBadge.textContent = config.name.slice(0, 2).toUpperCase();

        var wConfig = config.widget_config || {};
        var brandColor = wConfig.primary_color || '#4f46e5';
        hostContainer.style.setProperty('--brand-color', brandColor);

        // Position customization
        if (wConfig.position === 'bottom-left') {
          widgetWrap.classList.remove('pos-bottom-right');
          widgetWrap.classList.add('pos-bottom-left');
        }

        // Welcome message
        if (wConfig.welcome_message && state.messages.length === 0) {
          state.messages.push({
            role: 'ASSISTANT',
            content: wConfig.welcome_message,
            created_at: new Date().toISOString(),
          });
          renderMessages();
        }
        return config;
      })
      .catch(function (err) {
        console.warn('[Avtaar Widget] Failed to fetch employee configuration:', err.message);
      });
  }

  // 9. Session Management (Initializes or Resumes Session Token)
  function ensureSession() {
    if (state.sessionToken) {
      return Promise.resolve(state.sessionToken);
    }

    return apiRequest('/public/employees/' + encodeURIComponent(publicId) + '/sessions', {
      method: 'POST',
      body: { visitor_id: visitorId },
    }).then(function (data) {
      state.sessionToken = data.session_token;
      state.sessionExpiresAt = data.expires_at;

      // Restore conversation history if resumed session
      return apiRequest('/public/sessions/messages', { method: 'GET' })
        .then(function (history) {
          if (history && history.length > 0) {
            state.messages = history;
          }
          renderMessages();
          return state.sessionToken;
        })
        .catch(function () {
          return state.sessionToken;
        });
    });
  }

  // 10. Message Rendering & Interaction
  function renderMessages() {
    messagesContainer.innerHTML = '';

    state.messages.forEach(function (msg, idx) {
      var isUser = msg.role === 'USER' || msg.role === 'user';
      var row = document.createElement('div');
      row.className = 'msg-row ' + (isUser ? 'msg-user' : 'msg-assistant');

      var bubble = document.createElement('div');
      bubble.className = 'bubble ' + (isUser ? 'bubble-user' : 'bubble-assistant');
      bubble.textContent = msg.content;
      row.appendChild(bubble);

      // Tool Activity indicator
      if (!isUser && msg.tool_activity && msg.tool_activity.length > 0) {
        var toolsBox = document.createElement('div');
        msg.tool_activity.forEach(function (toolName) {
          var tBadge = document.createElement('span');
          tBadge.className = 'tool-badge';
          tBadge.innerHTML = '⚡ ' + escapeHtml(toolName);
          toolsBox.appendChild(tBadge);
        });
        row.appendChild(toolsBox);
      }

      // Citations / Sources Accordion
      if (!isUser && msg.citations && msg.citations.length > 0) {
        var cBox = document.createElement('div');
        cBox.className = 'citations-box';

        var cHeader = document.createElement('div');
        cHeader.className = 'citations-header';
        cHeader.innerHTML =
          '<span>📚 Sources (' +
          msg.citations.length +
          ')</span> <span style="font-size: 9px;">' +
          (state.expandedCitationIndex === idx ? '▲' : '▼') +
          '</span>';

        var cList = document.createElement('div');
        cList.className = 'citations-list';
        cList.style.display = state.expandedCitationIndex === idx ? 'flex' : 'none';

        msg.citations.forEach(function (c) {
          var cItem = document.createElement('div');
          cItem.className = 'citation-item';
          cItem.innerHTML =
            '<span class="citation-name">' +
            escapeHtml(c.document_name) +
            (c.page_number ? ' (p.' + c.page_number + ')' : '') +
            '</span>' +
            '<span class="citation-score">' +
            (c.score ? Math.round(c.score * 100) + '%' : '') +
            '</span>';
          cList.appendChild(cItem);
        });

        cHeader.onclick = function () {
          state.expandedCitationIndex = state.expandedCitationIndex === idx ? null : idx;
          renderMessages();
        };

        cBox.appendChild(cHeader);
        cBox.appendChild(cList);
        row.appendChild(cBox);
      }

      // Timestamp
      if (msg.created_at) {
        var timeStr = new Date(msg.created_at).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        });
        var timeSpan = document.createElement('span');
        timeSpan.className = 'msg-time';
        timeSpan.textContent = timeStr;
        row.appendChild(timeSpan);
      }

      messagesContainer.appendChild(row);
    });

    // Render Action Confirmation Card if pending write action
    if (state.pendingConfirmation) {
      var pc = state.pendingConfirmation;
      var card = document.createElement('div');
      card.className = 'confirm-card';
      card.innerHTML = `
        <div class="confirm-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          Action Approval Required
        </div>
        <div class="confirm-desc">
          ${escapeHtml(pc.message || 'The assistant requests permission to perform this action:')}
        </div>
        <div class="confirm-args">
          Tool: <strong>${escapeHtml(pc.tool_name)}</strong><br/>
          Parameters: ${escapeHtml(JSON.stringify(pc.arguments))}
        </div>
        <div class="confirm-actions">
          <button class="btn-confirm" id="btn-approve-action">Confirm & Proceed</button>
          <button class="btn-cancel" id="btn-reject-action">Cancel</button>
        </div>
      `;
      messagesContainer.appendChild(card);

      var approveBtn = card.querySelector('#btn-approve-action');
      var rejectBtn = card.querySelector('#btn-reject-action');

      approveBtn.onclick = function () {
        submitConfirmation(pc.pending_action_id, true);
      };
      rejectBtn.onclick = function () {
        submitConfirmation(pc.pending_action_id, false);
      };
    }

    // Typing indicator
    if (state.isSending) {
      var typingEl = document.createElement('div');
      typingEl.className = 'typing-indicator';
      typingEl.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
      messagesContainer.appendChild(typingEl);
    }

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // 11. Sending Messages & Confirming Actions
  function sendMessage(text) {
    if (!text || !text.trim() || state.isSending) return;

    var cleanText = text.trim();
    inputElement.value = '';

    // Add user message to UI immediately
    state.messages.push({
      role: 'USER',
      content: cleanText,
      created_at: new Date().toISOString(),
    });
    state.isSending = true;
    renderMessages();

    ensureSession()
      .then(function () {
        return apiRequest('/public/sessions/messages', {
          method: 'POST',
          body: {
            message: cleanText,
          },
        });
      })
      .then(function (res) {
        state.isSending = false;
        state.pendingConfirmation = res.pending_confirmation || null;
        state.messages.push({
          role: 'ASSISTANT',
          content: res.message,
          citations: res.citations || [],
          tool_activity: res.tool_activity || [],
          created_at: res.created_at || new Date().toISOString(),
        });
        renderMessages();
      })
      .catch(function (err) {
        state.isSending = false;
        state.messages.push({
          role: 'ASSISTANT',
          content: '⚠️ ' + (err.message || 'Failed to send message. Please try again.'),
          created_at: new Date().toISOString(),
        });
        renderMessages();
      });
  }

  function submitConfirmation(pendingActionId, confirm) {
    state.pendingConfirmation = null;
    state.isSending = true;
    renderMessages();

    ensureSession()
      .then(function () {
        return apiRequest('/public/sessions/messages', {
          method: 'POST',
          body: {
            message: confirm ? 'Action confirmed.' : 'Action cancelled.',
            pending_action_id: pendingActionId,
            confirm_action: confirm,
          },
        });
      })
      .then(function (res) {
        state.isSending = false;
        state.pendingConfirmation = res.pending_confirmation || null;
        state.messages.push({
          role: 'ASSISTANT',
          content: res.message,
          citations: res.citations || [],
          tool_activity: res.tool_activity || [],
          created_at: res.created_at || new Date().toISOString(),
        });
        renderMessages();
      })
      .catch(function (err) {
        state.isSending = false;
        state.messages.push({
          role: 'ASSISTANT',
          content: '⚠️ ' + (err.message || 'Failed to execute confirmation.'),
          created_at: new Date().toISOString(),
        });
        renderMessages();
      });
  }

  // 12. Event Listeners
  launcherBtn.onclick = function () {
    state.isOpen = !state.isOpen;
    if (state.isOpen) {
      chatWindow.classList.add('open');
      launcherBtn.innerHTML = `
        <svg viewBox="0 0 24 24">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      `;
      ensureSession();
      setTimeout(function () {
        inputElement.focus();
      }, 100);
    } else {
      chatWindow.classList.remove('open');
      launcherBtn.innerHTML = `
        <svg viewBox="0 0 24 24">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      `;
    }
  };

  closeBtn.onclick = function () {
    state.isOpen = false;
    chatWindow.classList.remove('open');
    launcherBtn.innerHTML = `
      <svg viewBox="0 0 24 24">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
    `;
  };

  sendBtn.onclick = function () {
    sendMessage(inputElement.value);
  };

  inputElement.onkeydown = function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputElement.value);
    }
  };

  // =========================================================================
  // 13. Real-Time Voice & Avatar Streaming Client (Phase 5 & 6)
  // =========================================================================
  var voiceWs = null;
  var mediaRecorder = null;
  var audioStream = null;
  var audioContext = null;
  var currentAudioSource = null;
  var avatarEngine = null;

  // Initialize 3D Avatar Engine if available
  try {
    if (typeof window.AvatarEngine === 'function' && avatarCanvas) {
      avatarEngine = new window.AvatarEngine({
        canvas: avatarCanvas,
        width: 260,
        height: 260,
        onStateChange: function (engineState) {
          if (avatarStatusPill) {
            avatarStatusPill.className = 'voice-status-pill ' + engineState.toLowerCase();
            avatarStatusPill.textContent = engineState;
          }
        },
      });
    }
  } catch (e) {
    console.warn('[Avtaar Avatar] Failed to initialize AvatarEngine:', e);
  }

  function updateVoiceUI(status, transcriptText) {
    state.voiceStatus = status;
    voiceStatusPill.className = 'voice-status-pill ' + status;
    voiceStatusPill.textContent = status.toUpperCase();

    if (avatarStatusPill) {
      avatarStatusPill.className = 'voice-status-pill ' + status;
      avatarStatusPill.textContent = status.toUpperCase();
    }

    if (transcriptText !== undefined) {
      state.voiceTranscript = transcriptText;
      voiceTranscriptEl.textContent = transcriptText || 'Listening...';
      if (avatarTranscriptEl) {
        avatarTranscriptEl.textContent = transcriptText || 'Listening...';
      }
    }

    if (status === 'speaking') {
      voiceVisualizer.classList.add('pulsing');
    } else {
      voiceVisualizer.classList.remove('pulsing');
    }
  }

  function getWsVoiceUrl() {
    var wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Derive WS host from apiBase
    try {
      var urlObj = new URL(apiBase);
      var proto = urlObj.protocol === 'https:' ? 'wss:' : 'ws:';
      return proto + '//' + urlObj.host + urlObj.pathname.replace(/\/api\/v1\/?$/, '') + '/api/v1/voice/stream';
    } catch (e) {
      return wsProto + '//' + window.location.host + '/api/v1/voice/stream';
    }
  }

  function connectVoiceWebSocket() {
    return ensureSession().then(function (token) {
      if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
        return voiceWs;
      }

      var wsUrl = getWsVoiceUrl();
      voiceWs = new WebSocket(wsUrl);
      updateVoiceUI('connecting', 'Connecting voice & avatar runtime...');

      voiceWs.onopen = function () {
        // Authenticate as first frame
        voiceWs.send(JSON.stringify({ type: 'auth', token: token }));
      };

      voiceWs.onmessage = function (event) {
        try {
          var data = JSON.parse(event.data);
          handleVoiceWsMessage(data);
        } catch (err) {
          console.error('[Avtaar Voice WS] Parse error:', err);
        }
      };

      voiceWs.onclose = function () {
        updateVoiceUI('idle', 'Session closed. Click mic to speak.');
      };

      voiceWs.onerror = function (err) {
        console.error('[Avtaar Voice WS] Error:', err);
        updateVoiceUI('idle', 'Connection error.');
      };

      return voiceWs;
    });
  }

  function handleVoiceWsMessage(data) {
    // Forward directly to AvatarEngine event protocol handler
    if (avatarEngine && typeof avatarEngine.handleAvatarEvent === 'function') {
      avatarEngine.handleAvatarEvent(data);
    }

    if (data.type === 'auth_ok') {
      updateVoiceUI('idle', 'Ready to listen. Click mic to speak.');
    } else if (data.type === 'status') {
      updateVoiceUI(data.state);
    } else if (data.type === 'transcript') {
      updateVoiceUI('transcribing', '“' + data.text + '”');
      // Append user message to shared conversation history
      if (data.is_final && data.text) {
        state.messages.push({
          role: 'USER',
          content: data.text,
          created_at: new Date().toISOString(),
        });
        renderMessages();
      }
    } else if (data.type === 'assistant_message') {
      state.messages.push({
        role: 'ASSISTANT',
        content: data.text,
        citations: data.citations || [],
        tool_activity: data.tool_activity || [],
        created_at: new Date().toISOString(),
      });
      renderMessages();
      updateVoiceUI('speaking', data.text);
    } else if (data.type === 'audio_chunk') {
      playVoiceAudioChunk(data.audio_base64);
    } else if (data.type === 'interrupted') {
      stopVoiceAudioPlayback();
      updateVoiceUI('listening', 'Listening to you...');
    }
  }

  function playVoiceAudioChunk(base64Audio) {
    try {
      if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }
      var binaryStr = atob(base64Audio);
      var len = binaryStr.length;
      var bytes = new Uint8Array(len);
      for (var i = 0; i < len; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
      }

      audioContext.decodeAudioData(bytes.buffer, function (buffer) {
        var source = audioContext.createBufferSource();
        source.buffer = buffer;

        // Route through AnalyserNode for lip-sync secondary fallback
        var analyser = audioContext.createAnalyser();
        analyser.fftSize = 64;
        source.connect(analyser);
        analyser.connect(audioContext.destination);

        if (avatarEngine && typeof avatarEngine.setAudioAnalyser === 'function') {
          avatarEngine.setAudioAnalyser(analyser);
        }

        currentAudioSource = source;
        source.start(0);
      }, function (decodeErr) {
        // Fallback for audio element
        var audioEl = new Audio('data:audio/mp3;base64,' + base64Audio);
        audioEl.play().catch(function () {});
      });
    } catch (e) {
      console.warn('[Avtaar Voice] Audio playback error:', e);
    }
  }

  function stopVoiceAudioPlayback() {
    if (currentAudioSource) {
      try {
        currentAudioSource.stop();
      } catch (e) {}
      currentAudioSource = null;
    }
    if (avatarEngine && typeof avatarEngine.resetMouth === 'function') {
      avatarEngine.resetMouth();
    }
  }

  function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      audioStream = stream;
      var options = { mimeType: 'audio/webm;codecs=opus' };
      if (!MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        options = { mimeType: 'audio/webm' };
      }

      mediaRecorder = new MediaRecorder(stream, options);
      var recordedChunks = [];

      mediaRecorder.ondataavailable = function (e) {
        if (e.data && e.data.size > 0) {
          recordedChunks.push(e.data);
        }
      };

      mediaRecorder.onstop = function () {
        var blob = new Blob(recordedChunks, { type: 'audio/webm' });
        var reader = new FileReader();
        reader.onloadend = function () {
          var base64data = reader.result.split(',')[1];
          if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
            voiceWs.send(JSON.stringify({
              type: 'audio_utterance',
              data: base64data,
              format: 'webm',
            }));
          }
        };
        reader.readAsDataURL(blob);
      };

      // If AI is speaking, send user_speaking frame for barge-in
      if (state.voiceStatus === 'speaking' && voiceWs && voiceWs.readyState === WebSocket.OPEN) {
        voiceWs.send(JSON.stringify({ type: 'user_speaking' }));
        stopVoiceAudioPlayback();
      }

      mediaRecorder.start(250);
      state.isRecording = true;
      voiceMicBtn.classList.add('recording');
      if (avatarMicBtn) avatarMicBtn.classList.add('recording');
      updateVoiceUI('listening', 'Listening... speak now');
    }).catch(function (err) {
      console.error('[Avtaar Voice] Microphone access denied:', err);
      updateVoiceUI('idle', 'Microphone permission denied.');
    });
  }

  function stopRecording() {
    if (mediaRecorder && state.isRecording) {
      mediaRecorder.stop();
      state.isRecording = false;
      voiceMicBtn.classList.remove('recording');
      if (avatarMicBtn) avatarMicBtn.classList.remove('recording');
      updateVoiceUI('transcribing', 'Processing your speech...');

      if (audioStream) {
        audioStream.getTracks().forEach(function (t) { t.stop(); });
        audioStream = null;
      }
    }
  }

  // Multi-Mode Button Interactions (Chat, Voice, Avatar)
  btnModeChat.onclick = function () {
    state.mode = 'chat';
    btnModeChat.classList.add('active');
    btnModeVoice.classList.remove('active');
    if (btnModeAvatar) btnModeAvatar.classList.remove('active');
    viewTextMode.style.display = 'flex';
    viewVoiceMode.style.display = 'none';
    if (viewAvatarMode) viewAvatarMode.style.display = 'none';
  };

  btnModeVoice.onclick = function () {
    state.mode = 'voice';
    btnModeVoice.classList.add('active');
    btnModeChat.classList.remove('active');
    if (btnModeAvatar) btnModeAvatar.classList.remove('active');
    viewTextMode.style.display = 'none';
    viewVoiceMode.style.display = 'flex';
    if (viewAvatarMode) viewAvatarMode.style.display = 'none';
    connectVoiceWebSocket();
  };

  if (btnModeAvatar) {
    btnModeAvatar.onclick = function () {
      state.mode = 'avatar';
      btnModeAvatar.classList.add('active');
      btnModeChat.classList.remove('active');
      btnModeVoice.classList.remove('active');
      viewTextMode.style.display = 'none';
      viewVoiceMode.style.display = 'none';
      if (viewAvatarMode) viewAvatarMode.style.display = 'flex';
      connectVoiceWebSocket();
    };
  }

  function handleMicButtonClick() {
    if (state.voiceStatus === 'speaking') {
      // Barge-in interruption
      if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
        voiceWs.send(JSON.stringify({ type: 'user_speaking' }));
      }
      stopVoiceAudioPlayback();
      updateVoiceUI('idle', 'Interrupted. Click mic to speak.');
      return;
    }

    if (!state.isRecording) {
      connectVoiceWebSocket().then(function () {
        startRecording();
      });
    } else {
      stopRecording();
    }
  }

  voiceMicBtn.onclick = handleMicButtonClick;
  if (avatarMicBtn) {
    avatarMicBtn.onclick = handleMicButtonClick;
  }

  // 14. Initialize configuration
  fetchPublicConfig();
})();
