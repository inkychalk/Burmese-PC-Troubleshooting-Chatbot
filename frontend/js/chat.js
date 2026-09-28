// ============================================================================
// Our Store Tech Assistant - Chat Frontend Logic
// Connects to the Flask backend API (/api/chat, /api/categories)
// ============================================================================

const API_BASE_URL = window.CHATBOT_API_URL || 'http://localhost:5000';

const chatWindow = document.getElementById('chatWindow');
const composerForm = document.getElementById('composerForm');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const langButtons = document.querySelectorAll('.lang-btn');
const suggestionsBar = document.getElementById('suggestions');

let selectedLanguage = 'my'; // 'my' | 'en' - overrides auto-detect when sending
let userId = getOrCreateUserId();

function getOrCreateUserId() {
  const key = 'chat_user_id';
  let id = localStorage.getItem(key);
  if (!id) {
    id = 'web_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem(key, id);
  }
  return id;
}

// ----------------------------------------------------------------------------
// Rendering
// ----------------------------------------------------------------------------

function appendMessage({ role, text, category }) {
  const bubble = document.createElement('div');
  bubble.className = `msg msg-${role}`;

  if (category && role === 'bot') {
    const cat = document.createElement('span');
    cat.className = 'msg-category';
    cat.textContent = category;
    bubble.appendChild(cat);
    bubble.appendChild(document.createElement('br'));
  }

  const textNode = document.createTextNode(text);
  bubble.appendChild(textNode);

  chatWindow.appendChild(bubble);
  scrollToBottom();
}

function showTyping() {
  const typing = document.createElement('div');
  typing.className = 'typing';
  typing.id = 'typingIndicator';
  typing.innerHTML = '<span></span><span></span><span></span>';
  chatWindow.appendChild(typing);
  scrollToBottom();
}

function hideTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ----------------------------------------------------------------------------
// API calls
// ----------------------------------------------------------------------------

async function sendMessageToBackend(message) {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      language: selectedLanguage,
      platform: 'web',
      user_id: userId,
    }),
  });

  if (!response.ok) {
    throw new Error(`Server responded with ${response.status}`);
  }

  return response.json();
}

async function loadCategories() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/categories`);
    if (!response.ok) return;
    const data = await response.json();
    // Categories are used server-side; the visible suggestion chips are
    // curated in the HTML to match real seeded entries for a reliable demo.
    console.debug('Available categories:', data.categories);
  } catch (err) {
    console.debug('Could not load categories (backend may be offline):', err);
  }
}

// ----------------------------------------------------------------------------
// Event handling
// ----------------------------------------------------------------------------

async function handleSend(text) {
  const trimmed = text.trim();
  if (!trimmed) return;

  appendMessage({ role: 'user', text: trimmed });
  messageInput.value = '';
  autoResizeInput();
  sendBtn.disabled = true;
  showTyping();

  try {
    const result = await sendMessageToBackend(trimmed);
    hideTyping();
    appendMessage({
      role: 'bot',
      text: result.response,
    });
  } catch (err) {
    hideTyping();
    const offlineMsg = selectedLanguage === 'my'
      ? 'ဆာဗာနှင့် ချိတ်ဆက်၍ မရပါ။ Backend ကို စစ်ဆေးပါ။'
      : 'Could not reach the server. Please check the backend is running.';
    appendMessage({ role: 'bot', text: offlineMsg });
    console.error(err);
  } finally {
    sendBtn.disabled = false;
  }
}

composerForm.addEventListener('submit', (e) => {
  e.preventDefault();
  handleSend(messageInput.value);
});

messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend(messageInput.value);
  }
});

function autoResizeInput() {
  messageInput.style.height = 'auto';
  messageInput.style.height = Math.min(messageInput.scrollHeight, 100) + 'px';
}

messageInput.addEventListener('input', autoResizeInput);

langButtons.forEach((btn) => {
  btn.addEventListener('click', () => {
    langButtons.forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    selectedLanguage = btn.dataset.lang;
    messageInput.placeholder = selectedLanguage === 'my'
      ? 'ပြဿနာကို ဒီမှာ ရိုက်ထည့်ပါ...'
      : 'Type your problem here...';
  });
});

// Click via keyboard (Enter/Space on a focused chip) never goes through the
// pointer drag path below, so it's still handled by the plain click event.
suggestionsBar.addEventListener('click', (e) => {
  if (e.detail !== 0) return; // 0 = keyboard/synthetic activation, non-zero = real pointer click (handled below)
  const chip = e.target.closest('.chip');
  if (!chip) return;
  handleSend(chip.dataset.text);
});

// Drag-to-scroll: overflow-x:auto alone only reacts to touch/trackpad
// swipes, so a mouse press-and-drag starting on a chip button does nothing.
// setPointerCapture retargets later pointer/click events to suggestionsBar
// itself, so we resolve the chip up front and fire the send on pointerup
// directly instead of trusting the (retargeted) native click.
(() => {
  let isDown = false;
  let dragged = false;
  let startX = 0;
  let startScrollLeft = 0;
  let downChip = null;

  suggestionsBar.addEventListener('pointerdown', (e) => {
    isDown = true;
    dragged = false;
    startX = e.clientX;
    startScrollLeft = suggestionsBar.scrollLeft;
    downChip = e.target.closest('.chip');
    // Keep receiving move/up events even once the pointer leaves the
    // bar's bounds, and stop the button from starting a text/drag selection.
    suggestionsBar.setPointerCapture(e.pointerId);
  });

  suggestionsBar.addEventListener('pointermove', (e) => {
    if (!isDown) return;
    const delta = e.clientX - startX;
    if (Math.abs(delta) > 4) {
      dragged = true;
      suggestionsBar.scrollLeft = startScrollLeft - delta;
      e.preventDefault();
    }
  });

  const endDrag = (e) => {
    isDown = false;
    if (suggestionsBar.hasPointerCapture(e.pointerId)) {
      suggestionsBar.releasePointerCapture(e.pointerId);
    }
    if (!dragged && downChip) {
      handleSend(downChip.dataset.text);
    }
    downChip = null;
  };

  suggestionsBar.addEventListener('pointerup', endDrag);
  suggestionsBar.addEventListener('pointercancel', () => {
    isDown = false;
    downChip = null;
  });
})();

// ----------------------------------------------------------------------------
// Init
// ----------------------------------------------------------------------------

function init() {
  appendMessage({
    role: 'bot',
    text: 'မင်္ဂလာပါ! ကျွန်ုပ်သည် Our Store ၏ AI နည်းပညာ လက်ထောက် ဖြစ်ပါသည်။ သင့်ကွန်ပျူတာ ပြဿနာကို အောက်တွင် ရိုက်ထည့်ပါ သို့မဟုတ် အောက်ပါ အကြံပြုချက်များကို နှိပ်ပါ။',
  });
  loadCategories();
}

init();
