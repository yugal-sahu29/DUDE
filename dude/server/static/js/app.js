/**
 * DUDE 0.4 Standalone Independent Application
 * Client Controller: Voice Call, Chat, Telemetry, Memory, and Notes
 */

document.addEventListener('DOMContentLoaded', () => {
  // State
  const state = {
    activeTab: 'chat',
    voiceOutputEnabled: true,
    activeSpeaker: 'en-US-GuyNeural',
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    callActive: false,
    callLoopRunning: false,
    activeNote: null,
  };

  // DOM Elements
  const navItems = document.querySelectorAll('.nav-item');
  const tabPanes = document.querySelectorAll('.tab-pane');
  const chatMessages = document.getElementById('chat-messages');
  const chatForm = document.getElementById('chat-form');
  const chatInput = document.getElementById('chat-input');
  const micBtn = document.getElementById('mic-btn');
  const quickChips = document.querySelectorAll('.chip');
  const btnToggleVoice = document.getElementById('btn-toggle-voice');
  const btnNewChat = document.getElementById('btn-new-chat');
  const ttsPlayer = document.getElementById('tts-audio-player');
  const sidebarVoiceSpeaker = document.getElementById('sidebar-voice-speaker');

  // Mobile Connect Modal Elements
  const btnMobileConnect = document.getElementById('btn-mobile-connect');
  const mobileModal = document.getElementById('mobile-modal');
  const mobileModalClose = document.getElementById('mobile-modal-close');
  const mobileQrImg = document.getElementById('mobile-qr-img');
  const mobileUrlInput = document.getElementById('mobile-url-input');
  const btnCopyMobileUrl = document.getElementById('btn-copy-mobile-url');
  const copyBtnLabel = document.getElementById('copy-btn-label');

  // Call Mode Elements
  const callOrb = document.getElementById('call-orb');
  const orbTrigger = document.getElementById('orb-click-trigger');
  const callToggleBtn = document.getElementById('call-toggle-btn');
  const callBtnText = document.getElementById('call-btn-text');
  const callStatusText = document.getElementById('call-status-text');
  const callTranscript = document.getElementById('call-transcript');
  const waveBars = document.querySelectorAll('.wave-bar');

  // Telemetry Elements
  const refreshTelemetryBtn = document.getElementById('refresh-telemetry-btn');
  const statCpuVal = document.getElementById('stat-cpu-val');
  const statCpuBar = document.getElementById('stat-cpu-bar');
  const statCpuMeta = document.getElementById('stat-cpu-meta');
  const statRamVal = document.getElementById('stat-ram-val');
  const statRamBar = document.getElementById('stat-ram-bar');
  const statRamMeta = document.getElementById('stat-ram-meta');
  const statDiskVal = document.getElementById('stat-disk-val');
  const statDiskBar = document.getElementById('stat-disk-bar');
  const statDiskMeta = document.getElementById('stat-disk-meta');
  const statBatteryVal = document.getElementById('stat-battery-val');
  const statBatteryBar = document.getElementById('stat-battery-bar');
  const statBatteryMeta = document.getElementById('stat-battery-meta');
  const statOsVal = document.getElementById('stat-os-val');
  const statUptimeVal = document.getElementById('stat-uptime-val');

  // Memory Elements
  const memoryGrid = document.getElementById('memory-cards-grid');
  const addMemoryForm = document.getElementById('add-memory-form');
  const memoryKeyInput = document.getElementById('memory-key-input');
  const memoryValInput = document.getElementById('memory-val-input');
  const clearAllMemoryBtn = document.getElementById('clear-all-memory-btn');

  // Notes Elements
  const notesListPane = document.getElementById('notes-list-pane');
  const noteTitleInput = document.getElementById('note-title-input');
  const noteContentInput = document.getElementById('note-content-input');
  const saveNoteBtn = document.getElementById('save-note-btn');
  const createNewNoteBtn = document.getElementById('create-new-note-btn');

  // =========================================================================
  // 1. Tab Navigation
  // =========================================================================

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetTab = item.getAttribute('data-tab');
      switchTab(targetTab);
    });
  });

  function switchTab(tabId) {
    state.activeTab = tabId;

    navItems.forEach(item => {
      if (item.getAttribute('data-tab') === tabId) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    tabPanes.forEach(pane => {
      if (pane.id === `tab-${tabId}`) {
        pane.classList.add('active');
      } else {
        pane.classList.remove('active');
      }
    });

    // Lazy load tab data
    if (tabId === 'telemetry') {
      fetchTelemetry();
    } else if (tabId === 'memory') {
      fetchMemory();
    } else if (tabId === 'notes') {
      fetchNotes();
    }
  }

  // =========================================================================
  // 2. Status & Initialization
  // =========================================================================

  async function fetchStatus() {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        if (data.active_speaker) {
          state.activeSpeaker = data.active_speaker;
          const shortName = data.active_speaker.split('-').pop().replace('Neural', '');
          sidebarVoiceSpeaker.textContent = shortName;
        }
        state.voiceOutputEnabled = data.voice_enabled !== false;
        updateVoiceButtonState();

        // Update mobile link & QR if available
        if (data.mobile_url && mobileUrlInput) {
          mobileUrlInput.value = data.mobile_url;
          if (mobileQrImg) {
            mobileQrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(data.mobile_url)}`;
          }
        }
      }
    } catch (e) {
      console.warn('Backend not responding yet:', e);
    }
  }

  function updateVoiceButtonState() {
    if (btnToggleVoice) {
      btnToggleVoice.style.color = state.voiceOutputEnabled ? 'var(--accent-cyan)' : 'var(--text-dim)';
      btnToggleVoice.title = state.voiceOutputEnabled ? 'Voice Output: Enabled' : 'Voice Output: Disabled';
    }
  }

  if (btnToggleVoice) {
    btnToggleVoice.addEventListener('click', () => {
      state.voiceOutputEnabled = !state.voiceOutputEnabled;
      updateVoiceButtonState();
      showToast(state.voiceOutputEnabled ? 'Voice output enabled' : 'Voice output muted');
    });
  }

  // Mobile Connect Modal Handlers
  if (btnMobileConnect && mobileModal) {
    btnMobileConnect.addEventListener('click', () => {
      const currentUrl = (mobileUrlInput && mobileUrlInput.value) || `http://10.98.107.121:8000`;
      if (mobileUrlInput) mobileUrlInput.value = currentUrl;
      if (mobileQrImg && !mobileQrImg.src) {
        mobileQrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(currentUrl)}`;
      }
      mobileModal.style.display = 'flex';
    });
  }

  if (mobileModalClose && mobileModal) {
    mobileModalClose.addEventListener('click', () => {
      mobileModal.style.display = 'none';
    });
  }

  if (mobileModal) {
    mobileModal.addEventListener('click', (e) => {
      if (e.target === mobileModal) {
        mobileModal.style.display = 'none';
      }
    });
  }

  if (btnCopyMobileUrl && mobileUrlInput) {
    btnCopyMobileUrl.addEventListener('click', () => {
      mobileUrlInput.select();
      const urlToCopy = mobileUrlInput.value;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(urlToCopy).then(() => {
          if (copyBtnLabel) copyBtnLabel.textContent = 'Copied!';
          setTimeout(() => { if (copyBtnLabel) copyBtnLabel.textContent = 'Copy URL'; }, 2000);
        }).catch(() => {
          fallbackCopy();
        });
      } else {
        fallbackCopy();
      }

      function fallbackCopy() {
        try {
          document.execCommand('copy');
          if (copyBtnLabel) copyBtnLabel.textContent = 'Copied!';
          setTimeout(() => { if (copyBtnLabel) copyBtnLabel.textContent = 'Copy URL'; }, 2000);
        } catch (_) {}
      }
    });
  }

  if (btnNewChat) {
    btnNewChat.addEventListener('click', async () => {
      chatMessages.innerHTML = `
        <div class="message-row assistant">
          <div class="message-avatar">D</div>
          <div class="message-bubble">
            <p>Started a fresh conversation session. How can I help you right now?</p>
          </div>
        </div>
      `;
      chatInput.focus();
    });
  }

  // Quick action chips
  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        sendMessage(prompt);
      }
    });
  });

  // =========================================================================
  // 3. Chat Messaging & Tools Execution
  // =========================================================================

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;
    sendMessage(text);
  });

  async function sendMessage(text) {
    chatInput.value = '';
    appendMessage('user', text);

    // Append loading placeholder
    const loadingId = 'loading-' + Date.now();
    appendLoadingBubble(loadingId);
    scrollToBottom();

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, speak: false }),
      });

      removeLoadingBubble(loadingId);

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Network error' }));
        appendMessage('assistant', `⚠️ **Error**: ${err.detail || 'Failed to communicate with DUDE brain.'}`);
        return;
      }

      const data = await res.json();
      appendMessage('assistant', data.response, data.tools_executed);
      scrollToBottom();

      // If voice enabled, synthesize and speak in browser
      if (state.voiceOutputEnabled && data.response) {
        speakTextInBrowser(data.response);
      }

    } catch (err) {
      removeLoadingBubble(loadingId);
      appendMessage('assistant', `⚠️ **Connection Error**: Unable to reach DUDE backend: ${err.message}`);
    }
  }

  function appendMessage(role, content, tools = []) {
    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'Y' : 'D';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    // Tool badges
    if (tools && tools.length > 0) {
      tools.forEach(t => {
        const chip = document.createElement('div');
        chip.className = 'tool-chip';
        const argKeys = Object.keys(t.args || {});
        const argStr = argKeys.length > 0 ? ` (${argKeys.map(k => `${k}=${JSON.stringify(t.args[k])}`).join(', ')})` : '';
        chip.innerHTML = `⚡ <span>${t.tool}${argStr}</span>`;
        bubble.appendChild(chip);
      });
    }

    const textElem = document.createElement('div');
    textElem.innerHTML = formatMarkdown(content);
    bubble.appendChild(textElem);

    row.appendChild(avatar);
    row.appendChild(bubble);
    chatMessages.appendChild(row);
  }

  function appendLoadingBubble(id) {
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.id = id;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'D';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = `<span style="color: var(--text-dim); font-style: italic;">DUDE is thinking...</span>`;

    row.appendChild(avatar);
    row.appendChild(bubble);
    chatMessages.appendChild(row);
  }

  function removeLoadingBubble(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function formatMarkdown(text) {
    if (!text) return '';
    let escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Code blocks ```code```
    escaped = escaped.replace(/```([a-z0-9_-]*)\n?([\s\S]*?)```/gi, (match, lang, code) => {
      return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline code `code`
    escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold **text**
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    escaped = escaped.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Bullet points (- or * )
    escaped = escaped.replace(/^\s*[-*]\s+(.*)$/gm, '<li>$1</li>');
    escaped = escaped.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Newlines to <br> if not in pre/ul
    escaped = escaped.replace(/\n\n/g, '</p><p>');
    escaped = escaped.replace(/\n/g, '<br>');

    return `<p>${escaped}</p>`;
  }

  // =========================================================================
  // 4. Voice Input (Microphone Recording)
  // =========================================================================

  micBtn.addEventListener('click', toggleMicrophone);

  async function toggleMicrophone() {
    if (state.isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      state.audioChunks = [];
      state.mediaRecorder = new MediaRecorder(stream);

      state.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) state.audioChunks.push(e.data);
      };

      state.mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(state.audioChunks, { type: 'audio/webm' });
        stream.getTracks().forEach(track => track.stop());
        await transcribeAndSendAudio(audioBlob);
      };

      state.mediaRecorder.start();
      state.isRecording = true;
      micBtn.classList.add('recording');
      chatInput.placeholder = 'Listening to your voice...';
    } catch (err) {
      alert('Microphone access denied or unavailable: ' + err.message);
    }
  }

  function stopRecording() {
    if (state.mediaRecorder && state.isRecording) {
      state.mediaRecorder.stop();
      state.isRecording = false;
      micBtn.classList.remove('recording');
      chatInput.placeholder = 'Transcribing voice input...';
    }
  }

  async function transcribeAndSendAudio(blob) {
    const formData = new FormData();
    formData.append('audio', blob, 'input.webm');

    try {
      const res = await fetch('/api/voice/transcribe', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error('Transcription failed');
      }

      const data = await res.json();
      const transcribed = data.text ? data.text.trim() : '';

      chatInput.placeholder = 'Type a message or command...';

      if (transcribed) {
        sendMessage(transcribed);
      } else {
        showToast('No speech detected');
      }
    } catch (e) {
      chatInput.placeholder = 'Type a message or command...';
      showToast('Speech recognition error: ' + e.message);
    }
  }

  // Edge-TTS Speech Synthesis in Browser
  async function speakTextInBrowser(text) {
    try {
      const res = await fetch('/api/voice/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, speaker: state.activeSpeaker }),
      });

      if (res.ok) {
        const audioBlob = await res.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        ttsPlayer.src = audioUrl;
        ttsPlayer.play();
      }
    } catch (e) {
      console.warn('TTS playback error:', e);
    }
  }

  // =========================================================================
  // 5. Hands-Free Voice Call Mode (Glowing Reactive Orb)
  // =========================================================================

  callToggleBtn.addEventListener('click', toggleCallMode);
  orbTrigger.addEventListener('click', toggleCallMode);

  function setOrbState(orbState, statusMsg, transcriptMsg) {
    callOrb.className = `orb-wrapper ${orbState}`;
    if (statusMsg) callStatusText.textContent = statusMsg;
    if (transcriptMsg) callTranscript.textContent = transcriptMsg;

    // Animate wave bars when active
    waveBars.forEach((b, i) => {
      if (orbState === 'listening' || orbState === 'speaking') {
        b.style.height = `${12 + Math.floor(Math.random() * 32)}px`;
      } else {
        b.style.height = '8px';
      }
    });
  }

  async function toggleCallMode() {
    if (state.callActive) {
      endCallMode();
    } else {
      startCallMode();
    }
  }

  async function startCallMode() {
    state.callActive = true;
    callToggleBtn.classList.remove('btn-primary');
    callToggleBtn.classList.add('btn-secondary');
    callBtnText.textContent = 'End Voice Call';

    setOrbState('listening', 'Connected - Listening...', 'Say anything to DUDE...');
    runCallLoop();
  }

  function endCallMode() {
    state.callActive = false;
    callToggleBtn.classList.remove('btn-secondary');
    callToggleBtn.classList.add('btn-primary');
    callBtnText.textContent = 'Connect Voice Call';

    setOrbState('idle', 'Call Disconnected', 'Click the orb or button above to reconnect.');
    if (ttsPlayer) ttsPlayer.pause();
  }

  async function runCallLoop() {
    if (!state.callActive) return;

    try {
      // 1. Record User Voice (4 seconds burst or stop on speech)
      setOrbState('listening', 'Listening...', 'DUDE is listening to your voice...');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks = [];
      const rec = new MediaRecorder(stream);

      rec.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };

      const audioPromise = new Promise(resolve => {
        rec.onstop = () => {
          stream.getTracks().forEach(t => t.stop());
          resolve(new Blob(chunks, { type: 'audio/webm' }));
        };
      });

      rec.start();
      // Record duration
      await new Promise(r => setTimeout(r, 4500));
      if (!state.callActive) {
        rec.stop();
        return;
      }
      rec.stop();
      const audioBlob = await audioPromise;

      if (!state.callActive) return;

      // 2. Transcribe
      setOrbState('thinking', 'Processing Audio...', 'Transcribing speech with Whisper...');
      const formData = new FormData();
      formData.append('audio', audioBlob, 'call.webm');

      const transRes = await fetch('/api/voice/transcribe', { method: 'POST', body: formData });
      if (!transRes.ok) throw new Error('Transcription error');
      const transData = await transRes.json();
      const userSpeech = (transData.text || '').trim();

      if (!userSpeech) {
        // No speech, immediately listen again
        if (state.callActive) runCallLoop();
        return;
      }

      setOrbState('thinking', 'Thinking...', `You: "${userSpeech}"`);

      // Check exit keywords
      if (userSpeech.toLowerCase().includes('goodbye') || userSpeech.toLowerCase().includes('exit call')) {
        setOrbState('speaking', 'Goodbye!', 'DUDE: Goodbye! Talk to you soon.');
        await playTTSAudio('Goodbye! Talk to you soon.');
        endCallMode();
        return;
      }

      // 3. DUDE Brain Response
      const chatRes = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userSpeech, speak: false }),
      });
      const chatData = await chatRes.json();
      const aiReply = chatData.response;

      if (!state.callActive) return;

      // 4. Speak Reply
      setOrbState('speaking', 'Speaking...', `DUDE: ${aiReply}`);
      await playTTSAudio(aiReply);

      // 5. Next loop iteration
      if (state.callActive) {
        runCallLoop();
      }

    } catch (err) {
      console.warn('Call loop error:', err);
      if (state.callActive) {
        setOrbState('listening', 'Listening...', 'Encountered audio glitch, still listening...');
        setTimeout(() => { if (state.callActive) runCallLoop(); }, 1000);
      }
    }
  }

  function playTTSAudio(text) {
    return new Promise(async (resolve) => {
      try {
        const res = await fetch('/api/voice/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, speaker: state.activeSpeaker }),
        });
        if (!res.ok) {
          resolve();
          return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        ttsPlayer.src = url;
        ttsPlayer.onended = () => resolve();
        ttsPlayer.onerror = () => resolve();
        await ttsPlayer.play();
      } catch (e) {
        resolve();
      }
    });
  }

  // =========================================================================
  // 6. Telemetry Dashboard
  // =========================================================================

  refreshTelemetryBtn.addEventListener('click', fetchTelemetry);

  async function fetchTelemetry() {
    try {
      const res = await fetch('/api/telemetry');
      if (!res.ok) return;
      const data = await res.json();

      // CPU
      const cpuUsage = data.cpu?.usage_percent || '0%';
      statCpuVal.textContent = cpuUsage;
      statCpuBar.style.width = cpuUsage;
      statCpuMeta.textContent = `Logical Cores: ${data.cpu?.cores || '--'}`;

      // RAM
      const ramUsage = data.memory?.usage_percent || '0%';
      statRamVal.textContent = `${ramUsage}%`;
      statRamBar.style.width = `${ramUsage}%`;
      statRamMeta.textContent = `${data.memory?.used_gb || 0} GB Used / ${data.memory?.total_gb || 0} GB Total`;

      // Disk
      const diskUsage = data.disk?.usage_percent || '0%';
      statDiskVal.textContent = `${diskUsage}%`;
      statDiskBar.style.width = `${diskUsage}%`;
      statDiskMeta.textContent = `${data.disk?.free_gb || 0} GB Free / ${data.disk?.total_gb || 0} GB Total`;

      // Battery
      if (data.battery && data.battery.percent !== undefined) {
        statBatteryVal.textContent = `${data.battery.percent}%`;
        statBatteryBar.style.width = `${data.battery.percent}%`;
        statBatteryMeta.textContent = `Status: ${data.battery.charging_status || 'Operating on Battery'}`;
      } else {
        statBatteryVal.textContent = 'AC';
        statBatteryBar.style.width = '100%';
        statBatteryMeta.textContent = 'Desktop / AC Power Connected';
      }

      // System info
      statOsVal.textContent = data.os || 'Windows';
      statUptimeVal.textContent = data.uptime || '--';

    } catch (err) {
      console.warn('Telemetry fetch error:', err);
    }
  }

  // =========================================================================
  // 7. Memory Vault
  // =========================================================================

  async function fetchMemory() {
    try {
      const res = await fetch('/api/memory');
      if (!res.ok) return;
      const data = await res.json();
      renderMemoryCards(data.facts || []);
    } catch (err) {
      console.warn('Memory fetch error:', err);
    }
  }

  function renderMemoryCards(facts) {
    memoryGrid.innerHTML = '';
    if (facts.length === 0) {
      memoryGrid.innerHTML = `<p style="grid-column: 1/-1; color: var(--text-dim); text-align: center; padding: 40px 0;">Persistent memory is currently empty. Tell DUDE a fact or add one above!</p>`;
      return;
    }

    facts.forEach(f => {
      const card = document.createElement('div');
      card.className = 'memory-card';
      card.innerHTML = `
        <div>
          <div class="memory-card-header">
            <span class="memory-tag">${f.fact_key || 'Fact'}</span>
            <span style="color: var(--text-dim); font-size: 0.75rem;">#${f.id}</span>
          </div>
          <p style="margin-top: 8px;">${f.fact_value}</p>
        </div>
        <div class="memory-card-footer">
          <span>${f.created_at ? f.created_at.split(' ')[0] : 'Persistent'}</span>
          <button class="delete-fact-btn" data-id="${f.id}" title="Forget this fact">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          </button>
        </div>
      `;
      memoryGrid.appendChild(card);
    });

    // Hook up delete buttons
    document.querySelectorAll('.delete-fact-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = btn.getAttribute('data-id');
        if (confirm(`Forget fact #${id}?`)) {
          await fetch(`/api/memory/${id}`, { method: 'DELETE' });
          fetchMemory();
          showToast(`Fact #${id} removed from SQLite memory.`);
        }
      });
    });
  }

  addMemoryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const val = memoryValInput.value.trim();
    const key = memoryKeyInput.value.trim() || null;
    if (!val) return;

    try {
      const res = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fact_value: val, fact_key: key }),
      });
      if (res.ok) {
        memoryValInput.value = '';
        memoryKeyInput.value = '';
        fetchMemory();
        showToast('Saved to persistent memory!');
      }
    } catch (e) {
      alert('Failed to save fact: ' + e.message);
    }
  });

  clearAllMemoryBtn.addEventListener('click', async () => {
    if (confirm('Are you sure you want to erase ALL persistent facts from SQLite memory?')) {
      await fetch('/api/memory', { method: 'DELETE' });
      fetchMemory();
      showToast('Cleared all memory facts.');
    }
  });

  // =========================================================================
  // 8. Notes Explorer
  // =========================================================================

  async function fetchNotes() {
    try {
      const res = await fetch('/api/notes');
      if (!res.ok) return;
      const data = await res.json();
      renderNotesList(data.notes || []);
    } catch (err) {
      console.warn('Notes fetch error:', err);
    }
  }

  function renderNotesList(notes) {
    notesListPane.innerHTML = '';
    if (notes.length === 0) {
      notesListPane.innerHTML = `<p style="color: var(--text-dim); text-align: center; padding: 20px 0; font-size: 0.85rem;">No notes saved yet.</p>`;
      return;
    }

    notes.forEach((n, idx) => {
      const item = document.createElement('div');
      item.className = `note-item ${idx === 0 ? 'active' : ''}`;
      item.innerHTML = `
        <h4>${n.name}</h4>
        <p>${n.preview || 'Empty note'}</p>
        <span style="font-size: 0.7rem; color: var(--text-dim);">${n.modified || ''}</span>
      `;
      item.addEventListener('click', () => loadNoteDetail(n.name, item));
      notesListPane.appendChild(item);
    });

    if (notes.length > 0) {
      loadNoteDetail(notes[0].name, notesListPane.children[0]);
    }
  }

  async function loadNoteDetail(name, itemElem) {
    document.querySelectorAll('.note-item').forEach(i => i.classList.remove('active'));
    if (itemElem) itemElem.classList.add('active');

    try {
      const res = await fetch(`/api/notes/${name}`);
      if (res.ok) {
        const data = await res.json();
        noteTitleInput.value = data.name;
        // Strip header banner if present
        let body = data.content || '';
        const noteMatch = body.match(/--- Note: .* ---\nCreated: .*\n\n([\s\S]*)/);
        if (noteMatch) body = noteMatch[1];
        noteContentInput.value = body.trim();
        state.activeNote = data.name;
      }
    } catch (e) {
      console.warn('Error loading note:', e);
    }
  }

  saveNoteBtn.addEventListener('click', async () => {
    const title = noteTitleInput.value.trim();
    const content = noteContentInput.value.trim();
    if (!title || !content) {
      alert('Please provide both note title and content.');
      return;
    }

    try {
      const res = await fetch('/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content }),
      });
      if (res.ok) {
        showToast(`Note '${title}' saved successfully!`);
        fetchNotes();
      }
    } catch (e) {
      alert('Failed to save note: ' + e.message);
    }
  });

  createNewNoteBtn.addEventListener('click', () => {
    noteTitleInput.value = '';
    noteContentInput.value = '';
    noteTitleInput.focus();
    document.querySelectorAll('.note-item').forEach(i => i.classList.remove('active'));
  });

  // =========================================================================
  // Toast Notifications
  // =========================================================================

  function showToast(msg) {
    let toast = document.getElementById('dude-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'dude-toast';
      toast.style.position = 'fixed';
      toast.style.bottom = '24px';
      toast.style.right = '24px';
      toast.style.background = 'rgba(13, 18, 29, 0.95)';
      toast.style.border = '1px solid var(--accent-cyan)';
      toast.style.color = 'var(--text-main)';
      toast.style.padding = '10px 18px';
      toast.style.borderRadius = 'var(--radius-md)';
      toast.style.fontSize = '0.9rem';
      toast.style.boxShadow = 'var(--shadow-glow)';
      toast.style.zIndex = '9999';
      toast.style.transition = 'opacity 0.3s ease';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = '1';
    setTimeout(() => { toast.style.opacity = '0'; }, 3000);
  }

  // Run initialization
  fetchStatus();
});
