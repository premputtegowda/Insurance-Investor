import base64
import getpass
import secrets
import sys

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERS = 600_000
SALT_BYTES = 16
IV_BYTES = 12

with open("cards.json", "rb") as f:
    cards_bytes = f.read()

pw = getpass.getpass("Password (min 12 chars): ")
if len(pw) < 12:
    sys.exit("Password must be at least 12 characters.")
pw2 = getpass.getpass("Confirm password: ")
if pw != pw2:
    sys.exit("Passwords do not match.")

salt = secrets.token_bytes(SALT_BYTES)
iv = secrets.token_bytes(IV_BYTES)
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITERS)
key = kdf.derive(pw.encode("utf-8"))
ciphertext = AESGCM(key).encrypt(iv, cards_bytes, None)
blob_b64 = base64.b64encode(salt + iv + ciphertext).decode()

template = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Insurance Exam Flashcards</title>
<style>
  :root {
    --bg: #f4f5f7;
    --card-bg: #fff;
    --text: #1f2328;
    --muted: #6a737d;
    --border: #d0d7de;
    --accent: #0969da;
    --known: #1a7f37;
    --known-bg: #dafbe1;
    --review: #cf222e;
    --review-bg: #ffebe9;
    --seen: #6a737d;
    --seen-bg: #eaeef2;
    --answer-bg: #dafbe1;
    --answer-border: #1a7f37;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }
  header { display: none; }
  main { display: none; }
  body.unlocked header { display: block; }
  body.unlocked main { display: block; }
  body.unlocked #lock { display: none; }
  #lock {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }
  .lock-box {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 32px;
    max-width: 380px;
    width: 100%;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }
  .lock-box h2 {
    margin: 0 0 8px;
    font-size: 18px;
  }
  .lock-box p {
    margin: 0 0 20px;
    color: var(--muted);
    font-size: 13px;
  }
  .lock-box input[type="password"] {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 15px;
    font-family: inherit;
  }
  .lock-box input[type="password"]:focus {
    outline: none;
    border-color: var(--accent);
  }
  .lock-box button {
    margin-top: 12px;
    width: 100%;
    padding: 10px;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
    font-family: inherit;
  }
  .lock-box button:disabled { opacity: 0.6; cursor: wait; }
  .lock-error {
    margin-top: 12px;
    color: var(--review);
    font-size: 13px;
    min-height: 18px;
  }
  header {
    background: var(--card-bg);
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
    position: sticky;
    top: 0;
    z-index: 10;
  }
  .top-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    justify-content: space-between;
  }
  h1 {
    font-size: 18px;
    margin: 0;
    font-weight: 600;
  }
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .filter-btn {
    cursor: pointer;
    border: 1px solid var(--border);
    background: var(--card-bg);
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 14px;
    color: var(--text);
    font-family: inherit;
  }
  .filter-btn:hover { background: var(--bg); }
  .filter-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }
  .filter-btn .count {
    font-weight: 600;
    margin-left: 4px;
  }
  .actions {
    display: flex;
    gap: 8px;
  }
  .jump-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
    align-items: center;
  }
  .jump-row select {
    flex: 1 1 200px;
    padding: 6px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--card-bg);
    font-size: 14px;
    font-family: inherit;
    color: var(--text);
  }
  .qjump {
    display: flex;
    gap: 6px;
  }
  .qjump input {
    width: 80px;
    padding: 6px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 14px;
    font-family: inherit;
  }
  .btn {
    cursor: pointer;
    border: 1px solid var(--border);
    background: var(--card-bg);
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 14px;
    font-family: inherit;
    color: var(--text);
  }
  .btn:hover { background: var(--bg); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn.primary:hover { filter: brightness(1.05); }
  .btn.known { background: var(--known-bg); border-color: var(--known); color: var(--known); }
  .btn.review { background: var(--review-bg); border-color: var(--review); color: var(--review); }
  .btn.danger { color: var(--review); }
  main {
    max-width: 800px;
    margin: 24px auto;
    padding: 0 16px;
  }
  .position {
    text-align: center;
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 8px;
  }
  .card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 24px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  }
  .chapter {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
    margin-bottom: 12px;
  }
  .question {
    font-size: 18px;
    font-weight: 500;
    margin-bottom: 20px;
  }
  .choices {
    list-style-type: lower-alpha;
    padding-left: 24px;
    margin: 0 0 16px;
  }
  .choice {
    padding: 8px 10px;
    margin: 4px -10px;
    border-radius: 6px;
    border: 1px solid transparent;
    cursor: pointer;
    position: relative;
  }
  .choice:hover { background: var(--bg); }
  .choice.locked { cursor: default; }
  .choice.locked:hover { background: inherit; }
  .choice.answer {
    background: var(--answer-bg);
    border-color: var(--answer-border);
    font-weight: 600;
  }
  .choice.picked-wrong {
    background: var(--review-bg);
    border-color: var(--review);
    font-weight: 600;
  }
  .choice .mark {
    float: right;
    font-weight: 700;
    margin-left: 8px;
  }
  .choice.answer .mark { color: var(--known); }
  .choice.picked-wrong .mark { color: var(--review); }
  .state-tags {
    display: flex;
    gap: 6px;
    margin-top: 12px;
    min-height: 22px;
  }
  .tag {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border: 1px solid transparent;
    cursor: pointer;
    font-family: inherit;
  }
  .tag:hover { filter: brightness(0.95); }
  .tag .x {
    margin-left: 4px;
    opacity: 0.6;
    font-weight: 700;
  }
  .tag:hover .x { opacity: 1; }
  .tag.known { background: var(--known-bg); color: var(--known); }
  .tag.review { background: var(--review-bg); color: var(--review); }
  .tag.seen { background: var(--seen-bg); color: var(--seen); }
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 16px;
    justify-content: center;
  }
  .empty {
    text-align: center;
    padding: 60px 20px;
    color: var(--muted);
    background: var(--card-bg);
    border: 1px dashed var(--border);
    border-radius: 10px;
  }
  .hint {
    text-align: center;
    color: var(--muted);
    font-size: 12px;
    margin-top: 16px;
  }
  kbd {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-bottom-width: 2px;
    border-radius: 4px;
    padding: 1px 5px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 11px;
  }
  @media (max-width: 640px) {
    header { padding: 10px 12px; position: static; }
    h1 { font-size: 16px; }
    .top-row { gap: 8px; }
    .filters { gap: 6px; width: 100%; }
    .filter-btn { flex: 1 1 calc(50% - 3px); padding: 10px 8px; font-size: 13px; }
    .actions { width: 100%; }
    .actions .btn { flex: 1; padding: 10px 12px; }
    .jump-row { flex-direction: column; align-items: stretch; gap: 6px; }
    .jump-row select { flex: 1; width: 100%; padding: 10px; font-size: 14px; max-width: 100%; }
    .qjump { width: 100%; }
    .qjump input { flex: 1; width: auto; padding: 10px; font-size: 16px; }
    .qjump .btn { padding: 10px 18px; }
    main { margin: 12px auto; padding: 0 10px; }
    .card { padding: 16px; border-radius: 8px; }
    .question { font-size: 16px; margin-bottom: 16px; }
    .choices { padding-left: 20px; }
    .choice { padding: 10px 8px; margin: 6px -8px; font-size: 15px; }
    main {
      display: grid;
      grid-template-areas:
        "pos pos"
        "prev next"
        "card card"
        "known review"
        "reveal reveal"
        "reset reset"
        "hint hint";
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      margin: 12px auto;
    }
    .position { grid-area: pos; margin-bottom: 0; }
    #card-area { grid-area: card; }
    .hint { grid-area: hint; }
    .controls { display: contents; }
    #known-btn { grid-area: known; }
    #review-btn { grid-area: review; }
    #reveal-btn { grid-area: reveal; }
    #prev-btn { grid-area: prev; }
    #next-btn { grid-area: next; }
    #reset-card-btn { grid-area: reset; }
    .controls .btn {
      min-height: 44px;
      padding: 10px 8px;
      font-size: 14px;
      margin: 0;
    }
    .hint { display: none; }
    .lock-box { padding: 24px 20px; }
    .lock-box input[type="password"] { font-size: 16px; padding: 12px; }
    .lock-box button { padding: 14px; min-height: 48px; }
    .position { font-size: 12px; }
    .tag { padding: 4px 10px; font-size: 11px; }
  }
</style>
</head>
<body>
<div id="lock">
  <form class="lock-box" id="lock-form" autocomplete="off">
    <h2>Insurance Exam Flashcards</h2>
    <p>Enter password to unlock</p>
    <input type="password" id="pw-input" autofocus required>
    <button type="submit" id="unlock-btn">Unlock</button>
    <div class="lock-error" id="lock-error"></div>
  </form>
</div>
<header>
  <div class="top-row">
    <h1>Insurance Exam Flashcards</h1>
    <div class="actions">
      <button class="btn" id="shuffle-btn">Shuffle</button>
      <button class="btn danger" id="clear-btn">Clear states</button>
    </div>
  </div>
  <div class="filters" style="margin-top: 10px;">
    <button class="filter-btn" data-filter="all">All <span class="count" id="all-count">0</span></button>
    <button class="filter-btn" data-filter="known">Known <span class="count" id="known-count">0</span></button>
    <button class="filter-btn" data-filter="review">Review <span class="count" id="review-count">0</span></button>
    <button class="filter-btn" data-filter="seen">Seen <span class="count" id="seen-count">0</span></button>
  </div>
  <div class="jump-row">
    <select id="chapter-select"><option value="">Jump to chapter…</option></select>
    <form id="qjump-form" class="qjump">
      <input type="number" id="qjump-input" placeholder="Q#" min="1" inputmode="numeric">
      <button type="submit" class="btn">Go</button>
    </form>
  </div>
</header>
<main>
  <div class="position" id="position"></div>
  <div id="card-area"></div>
  <div class="controls" id="controls">
    <button class="btn" id="prev-btn">&larr; Prev</button>
    <button class="btn primary" id="reveal-btn">Reveal</button>
    <button class="btn known" id="known-btn">Mark Known</button>
    <button class="btn review" id="review-btn">Mark Review</button>
    <button class="btn" id="next-btn">Next &rarr;</button>
    <button class="btn" id="reset-card-btn">Reset card</button>
  </div>
  <div class="hint">
    Shortcuts: <kbd>Space</kbd> reveal/next &middot; <kbd>K</kbd> known &middot; <kbd>R</kbd> review &middot; <kbd>S</kbd> shuffle &middot; <kbd>&larr;</kbd> / <kbd>&rarr;</kbd> prev/next
  </div>
</main>
<script>
const ENCRYPTED_BLOB_B64 = "__BLOB__";
const PBKDF2_ITERS = __ITERS__;
const SALT_BYTES = __SALT_BYTES__;
const IV_BYTES = __IV_BYTES__;

let CARDS = [];

const STORAGE_KEY = 'insurance_flashcards_v1';
const state = {
  filter: 'all',
  deck: [],
  pos: 0,
  revealed: false,
  picked: null,
  sets: { known: new Set(), review: new Set(), seen: new Set() },
};

function b64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function decryptCards(password) {
  const data = b64ToBytes(ENCRYPTED_BLOB_B64);
  const salt = data.slice(0, SALT_BYTES);
  const iv = data.slice(SALT_BYTES, SALT_BYTES + IV_BYTES);
  const ct = data.slice(SALT_BYTES + IV_BYTES);
  const enc = new TextEncoder();
  const baseKey = await crypto.subtle.importKey(
    'raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']
  );
  const key = await crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: PBKDF2_ITERS, hash: 'SHA-256' },
    baseKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['decrypt']
  );
  const plainBuf = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct);
  return JSON.parse(new TextDecoder().decode(plainBuf));
}

document.getElementById('lock-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('unlock-btn');
  const errEl = document.getElementById('lock-error');
  const pw = document.getElementById('pw-input').value;
  errEl.textContent = '';
  btn.disabled = true;
  btn.textContent = 'Unlocking...';
  try {
    CARDS = await decryptCards(pw);
    document.body.classList.add('unlocked');
    initApp();
  } catch (err) {
    errEl.textContent = 'Wrong password.';
    btn.disabled = false;
    btn.textContent = 'Unlock';
    document.getElementById('pw-input').select();
  }
});

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const s = JSON.parse(raw);
    state.sets.known = new Set(s.known || []);
    state.sets.review = new Set(s.review || []);
    state.sets.seen = new Set(s.seen || []);
    if (s.filter) state.filter = s.filter;
    if (typeof s.currentNum === 'number') state._restoreNum = s.currentNum;
  } catch (e) {}
}

function save() {
  const card = state.deck.length > 0 ? CARDS[state.deck[state.pos]] : null;
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    known: [...state.sets.known],
    review: [...state.sets.review],
    seen: [...state.sets.seen],
    filter: state.filter,
    currentNum: card ? card.num : null,
  }));
}

function rebuildDeck() {
  const indices = [];
  for (let i = 0; i < CARDS.length; i++) {
    const num = CARDS[i].num;
    let include = false;
    if (state.filter === 'all') include = true;
    else if (state.filter === 'known') include = state.sets.known.has(num);
    else if (state.filter === 'review') include = state.sets.review.has(num);
    else if (state.filter === 'seen') include = state.sets.seen.has(num);
    if (include) indices.push(i);
  }
  state.deck = indices;
  state.pos = 0;
  state.revealed = false;
  state.picked = null;
}

function shuffle() {
  const a = state.deck.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  state.deck = a;
  state.pos = 0;
  state.revealed = false;
  state.picked = null;
  save();
  render();
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function render() {
  document.getElementById('all-count').textContent = CARDS.length;
  document.getElementById('known-count').textContent = state.sets.known.size;
  document.getElementById('review-count').textContent = state.sets.review.size;
  document.getElementById('seen-count').textContent = state.sets.seen.size;

  document.querySelectorAll('.filter-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.filter === state.filter);
  });

  const cardArea = document.getElementById('card-area');
  const controls = document.getElementById('controls');
  const positionEl = document.getElementById('position');

  if (state.deck.length === 0) {
    positionEl.textContent = '';
    cardArea.innerHTML = '<div class="empty">No cards in this section yet.</div>';
    controls.style.display = 'none';
    return;
  }
  controls.style.display = '';

  const card = CARDS[state.deck[state.pos]];
  positionEl.textContent = `${state.pos + 1} of ${state.deck.length}`;

  const choicesHtml = card.choices.map((c, i) => {
    const classes = ['choice'];
    if (state.revealed) classes.push('locked');
    let mark = '';
    if (state.revealed) {
      if (c.is_answer) {
        classes.push('answer');
        if (state.picked === i) mark = '<span class="mark">&check;</span>';
      } else if (state.picked === i) {
        classes.push('picked-wrong');
        mark = '<span class="mark">&times;</span>';
      }
    }
    return `<li class="${classes.join(' ')}" data-idx="${i}">${escapeHtml(c.text)}${mark}</li>`;
  }).join('');

  const tagsHtml = [
    state.sets.known.has(card.num) ? '<span class="tag known">Known</span>' : '',
    state.sets.review.has(card.num) ? '<span class="tag review">Review</span>' : '',
    state.sets.seen.has(card.num) ? '<span class="tag seen">Seen</span>' : '',
  ].join('');

  cardArea.innerHTML = `
    <div class="card">
      <div class="chapter">${escapeHtml(card.chapter)} &middot; Q${card.num}</div>
      <div class="question">${escapeHtml(card.question)}</div>
      <ol class="choices" type="a">${choicesHtml}</ol>
      <div class="state-tags">${tagsHtml}</div>
    </div>
  `;

  if (!state.revealed) {
    cardArea.querySelectorAll('.choice').forEach(el => {
      el.addEventListener('click', () => pickChoice(parseInt(el.dataset.idx, 10)));
    });
  }

  document.getElementById('reveal-btn').disabled = state.revealed;
}

function pickChoice(idx) {
  if (state.revealed || state.deck.length === 0) return;
  state.picked = idx;
  state.revealed = true;
  const card = CARDS[state.deck[state.pos]];
  state.sets.seen.add(card.num);
  save();
  render();
}

function reveal() {
  if (state.deck.length === 0) return;
  if (state.revealed) { next(); return; }
  state.revealed = true;
  const card = CARDS[state.deck[state.pos]];
  state.sets.seen.add(card.num);
  save();
  render();
}

function markKnown() {
  if (state.deck.length === 0) return;
  const card = CARDS[state.deck[state.pos]];
  state.sets.known.add(card.num);
  state.sets.review.delete(card.num);
  state.sets.seen.add(card.num);
  save();
  next();
}

function markReview() {
  if (state.deck.length === 0) return;
  const card = CARDS[state.deck[state.pos]];
  state.sets.review.add(card.num);
  state.sets.known.delete(card.num);
  state.sets.seen.add(card.num);
  save();
  next();
}

function next() {
  if (state.deck.length === 0) return;
  state.pos = (state.pos + 1) % state.deck.length;
  state.revealed = false;
  state.picked = null;
  save();
  render();
}

function prev() {
  if (state.deck.length === 0) return;
  state.pos = (state.pos - 1 + state.deck.length) % state.deck.length;
  state.revealed = false;
  state.picked = null;
  save();
  render();
}

function setFilter(f) {
  state.filter = f;
  save();
  rebuildDeck();
  render();
}

function resetCard() {
  if (state.deck.length === 0) return;
  const card = CARDS[state.deck[state.pos]];
  const num = card.num;
  state.sets.known.delete(num);
  state.sets.review.delete(num);
  state.sets.seen.delete(num);
  save();
  rebuildDeck();
  const idx = state.deck.findIndex(i => CARDS[i].num === num);
  state.pos = idx >= 0 ? idx : Math.min(state.pos, Math.max(0, state.deck.length - 1));
  state.revealed = false;
  state.picked = null;
  render();
}

function jumpToCard(num) {
  if (state.filter !== 'all') {
    state.filter = 'all';
    rebuildDeck();
  }
  const idx = state.deck.findIndex(i => CARDS[i].num === num);
  if (idx < 0) return false;
  state.pos = idx;
  state.revealed = false;
  state.picked = null;
  save();
  render();
  return true;
}

function jumpToChapter(chapter) {
  if (state.filter !== 'all') {
    state.filter = 'all';
    rebuildDeck();
  }
  const idx = state.deck.findIndex(i => CARDS[i].chapter === chapter);
  if (idx < 0) return false;
  state.pos = idx;
  state.revealed = false;
  state.picked = null;
  save();
  render();
  return true;
}

function populateChapterDropdown() {
  const sel = document.getElementById('chapter-select');
  const seen = new Set();
  for (const c of CARDS) {
    if (seen.has(c.chapter)) continue;
    seen.add(c.chapter);
    const opt = document.createElement('option');
    opt.value = c.chapter;
    opt.textContent = c.chapter;
    sel.appendChild(opt);
  }
}

function clearStates() {
  if (!confirm('Clear all Known, Review, and Seen marks? Cards stay.')) return;
  state.sets.known.clear();
  state.sets.review.clear();
  state.sets.seen.clear();
  save();
  rebuildDeck();
  render();
}

function initApp() {
  document.getElementById('shuffle-btn').addEventListener('click', shuffle);
  document.getElementById('clear-btn').addEventListener('click', clearStates);
  document.getElementById('reveal-btn').addEventListener('click', reveal);
  document.getElementById('known-btn').addEventListener('click', markKnown);
  document.getElementById('review-btn').addEventListener('click', markReview);
  document.getElementById('next-btn').addEventListener('click', next);
  document.getElementById('prev-btn').addEventListener('click', prev);
  document.getElementById('reset-card-btn').addEventListener('click', resetCard);
  document.querySelectorAll('.filter-btn').forEach(b => {
    b.addEventListener('click', () => setFilter(b.dataset.filter));
  });
  populateChapterDropdown();
  document.getElementById('chapter-select').addEventListener('change', (e) => {
    if (e.target.value) {
      jumpToChapter(e.target.value);
      e.target.value = '';
    }
  });
  document.getElementById('qjump-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const input = document.getElementById('qjump-input');
    const num = parseInt(input.value, 10);
    if (!isNaN(num) && jumpToCard(num)) {
      input.value = '';
    } else {
      input.style.borderColor = 'var(--review)';
      setTimeout(() => { input.style.borderColor = ''; }, 800);
    }
  });
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    switch (e.key) {
      case ' ': e.preventDefault(); reveal(); break;
      case 'ArrowRight': next(); break;
      case 'ArrowLeft': prev(); break;
      case 'k': case 'K': markKnown(); break;
      case 'r': case 'R': markReview(); break;
      case 's': case 'S': shuffle(); break;
    }
  });
  load();
  rebuildDeck();
  if (state._restoreNum != null) {
    const idx = state.deck.findIndex(i => CARDS[i].num === state._restoreNum);
    if (idx >= 0) state.pos = idx;
    delete state._restoreNum;
  }
  render();
}
</script>
</body>
</html>
"""

html = (template
        .replace("__BLOB__", blob_b64)
        .replace("__ITERS__", str(PBKDF2_ITERS))
        .replace("__SALT_BYTES__", str(SALT_BYTES))
        .replace("__IV_BYTES__", str(IV_BYTES)))

with open("index.html", "w") as f:
    f.write(html)
print(f"Wrote index.html ({len(html):,} bytes) — ciphertext: {len(blob_b64):,} chars")
