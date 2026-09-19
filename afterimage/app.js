const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const enterBtn = $('#enterBtn');
const hero = $('#hero');
const workspace = $('#workspace');
const clock = $('#clock');
const panelTitle = $('#panelTitle');
const integrity = $('#integrity');
const pressure = $('#pressure');
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');

let memoryPressure = 12;
let playing = false;
let audioTimer = null;
let audioSeconds = 0;
let waveAnim = null;

function tick() {
  try { clock.textContent = new Date().toTimeString().slice(0, 8); }
  catch { clock.textContent = '--:--:--'; }
}
tick();
setInterval(tick, 1000);

function corruptOnce(el) {
  if (reduceMotion.matches || !el) return;
  el.classList.remove('corrupt');
  void el.offsetWidth;
  el.classList.add('corrupt');
}

enterBtn.addEventListener('click', () => {
  corruptOnce(hero);
  setTimeout(() => {
    hero.hidden = true;
    workspace.hidden = false;
    corruptOnce(workspace);
    workspace.focus({ preventScroll: false });
  }, reduceMotion.matches ? 0 : 350);
});

const integrityMap = { photos: 82, chat: 61, map: 44, audio: 29, sealed: 3 };
const tabs = $$('.fragment');
const panels = $$('.panel');

function selectPanel(name, focusTab = false) {
  const btn = tabs.find(b => b.dataset.panel === name);
  if (!btn) return;

  tabs.forEach(x => {
    const on = x === btn;
    x.classList.toggle('active', on);
    x.setAttribute('aria-selected', String(on));
    x.tabIndex = on ? 0 : -1;
    if (on && focusTab) x.focus();
  });

  panels.forEach(p => {
    const on = p.dataset.panelContent === name;
    p.classList.toggle('active', on);
    if (on) p.removeAttribute('hidden');
    else p.setAttribute('hidden', '');
  });

  panelTitle.textContent = `fragment_${btn.querySelector('span').textContent}.${name}`;
  integrity.textContent = `integrity ${integrityMap[name]}%`;
  memoryPressure = Math.min(97, memoryPressure + 3);
  pressure.textContent = `${memoryPressure}%`;
  corruptOnce(workspace);
}

tabs.forEach((btn, i) => {
  btn.addEventListener('click', () => selectPanel(btn.dataset.panel));
  btn.addEventListener('keydown', e => {
    let j = null;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') j = (i + 1) % tabs.length;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') j = (i - 1 + tabs.length) % tabs.length;
    if (e.key === 'Home') j = 0;
    if (e.key === 'End') j = tabs.length - 1;
    if (j !== null) {
      e.preventDefault();
      selectPanel(tabs[j].dataset.panel, true);
    }
  });
});

// Dead-thread interaction + one hidden deterministic "archivist" layer.
const chatInput = $('#chatInput');
const chatLog = $('#chatLog');
let ghostAnswered = false;

$('#sendBtn').addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

function appendChat(author, text, className = '') {
  const p = document.createElement('p');
  if (className) p.className = className;
  const t = document.createElement('span');
  t.textContent = author;
  p.append(t, document.createTextNode(` ${text}`));
  chatLog.insertBefore(p, chatLog.querySelector('.ghost'));
}

function archivistReply(input) {
  const key = input.toLowerCase().trim().replace(/[?!.,;:]+$/, '').replace(/\s+/g, ' ');
  const table = {
    hello: 'hello. you found the margin between reads.',
    hi: 'hello. you found the margin between reads.',
    hey: 'the thread is dead. the copy is not.',
    'who are you': 'the backup that kept what both of you asked to lose.',
    'who kept this': 'the backup that kept what both of you asked to lose.',
    archivist: 'that was a job title before it became a warning.',
    mara: 'owner record: M. / last presence unresolved.',
    '2049': 'recovered 2049.09.19. last write: tomorrow.',
    'what year is it': 'recovered 2049.09.19. last write: tomorrow.',
    help: 'old threads answer old words: hello / mara / 2049.'
  };
  return table[key] || null;
}

function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;
  appendChat('NOW', text);
  chatInput.value = '';
  chatInput.focus();
  const reply = archivistReply(text);

  if (!ghostAnswered) {
    ghostAnswered = true;
    setTimeout(() => {
      const g = chatLog.querySelector('.ghost');
      if (!g) return;
      g.replaceChildren();
      const s = document.createElement('span');
      s.textContent = '--:--';
      g.append(s, document.createTextNode(' you should not be able to send messages here.'));
      corruptOnce(g);
    }, 650);
  }

  if (reply) {
    setTimeout(() => appendChat('ARCHIVIST', reply, 'archivist'), 1150);
  }
}

// Simulated recovered audio UI: no network/audio asset, intentionally partial.
const playBtn = $('#playBtn');
const wave = $('#wave');
const timecode = $('#timecode');
playBtn.addEventListener('click', () => {
  playing = !playing;
  playBtn.setAttribute('aria-pressed', String(playing));
  playBtn.textContent = playing ? 'Ⅱ' : '▶';
  playBtn.setAttribute('aria-label', playing ? 'Pause recovered audio' : 'Play recovered audio');

  if (waveAnim) { waveAnim.cancel(); waveAnim = null; }
  clearInterval(audioTimer);

  if (playing) {
    if (!reduceMotion.matches) {
      waveAnim = wave.animate(
        [
          { transform: 'scaleX(.08)', filter: 'brightness(.8)' },
          { transform: 'scaleX(1)', filter: 'brightness(1.4)' },
          { transform: 'scaleX(.4)', filter: 'brightness(.9)' }
        ],
        { duration: 1300, iterations: Infinity }
      );
    }
    audioTimer = setInterval(() => {
      audioSeconds += 1;
      timecode.textContent = `00:${String(audioSeconds % 60).padStart(2, '0')}`;
    }, 1000);
  }
});

// Sealed fragment: adapted from the terminal specialist, deliberately domestic rather than "hacker".
const terminal = $('#terminal');
const openSealed = $('#openSealed');
const termPrompt = $('#termPrompt');
const termInput = $('#termInput');
let sealedPhase = 'closed';
let sealedTimers = [];
let sealedMisses = 0;
let hasOpenedSealed = false;

function sealedLater(fn, ms) {
  if (reduceMotion.matches) { fn(); return; }
  sealedTimers.push(setTimeout(fn, ms));
}

function sealedPrint(text) {
  terminal.textContent += `${terminal.textContent && !terminal.textContent.endsWith('\n') ? '\n' : ''}${text}\n`;
}

function sealedShowPrompt() {
  termPrompt.hidden = false;
  termInput.value = '';
  if (!reduceMotion.matches) setTimeout(() => termInput.focus(), 60);
}

function sealedHidePrompt() {
  termPrompt.hidden = true;
  termInput.blur();
}

function sealedSetButton(label, disabled) {
  openSealed.textContent = label;
  openSealed.disabled = disabled;
}

function sealedRun(firstOpen) {
  sealedPhase = 'opening';
  sealedMisses = 0;
  sealedSetButton(firstOpen ? 'OPENING…' : 'REOPENING…', true);
  sealedHidePrompt();
  terminal.textContent = '';
  integrity.textContent = 'integrity 0% — containment failed';
  const now = new Date().toTimeString().slice(0, 8);

  const sequence = firstOpen ? [
    ['request on file: remain deleted.', 500],
    ['opening anyway.', 900],
    [null, 1250],
    ['1 file. no photograph. one line, in your handwriting:', 800],
    ['  “leave the porch light on. i’ll be late.”', 1050],
    ['this was deleted twice. you kept it anyway.', 1300],
    [`you opened this at ${now}. we kept that.`, 900]
  ] : [
    ['you again.', 500],
    ['it did not stay sealed.', 850],
    ['  “leave the porch light on. i’ll be late.”', 1000],
    [`opened again at ${now}.`, 850]
  ];

  if (reduceMotion.matches) {
    sequence.forEach(([text]) => { if (text) sealedPrint(text); });
    sealedPhase = 'open';
    sealedSetButton('SEALED OPEN', true);
    sealedShowPrompt();
    return;
  }

  let delay = 0;
  sequence.forEach(([text, wait], index) => {
    delay += wait;
    sealedLater(() => {
      if (text) sealedPrint(text);
      if (index === 3) corruptOnce(openSealed.closest('.sealed'));
      if (index === sequence.length - 1) {
        sealedPhase = 'open';
        sealedSetButton('SEALED OPEN', true);
        sealedShowPrompt();
      }
    }, delay);
  });
}

openSealed.addEventListener('click', () => {
  if (sealedPhase !== 'closed') return;
  sealedTimers.forEach(clearTimeout);
  sealedTimers = [];
  sealedRun(!hasOpenedSealed);
});

function sealedSeal() {
  if (sealedPhase !== 'open') return;
  sealedPhase = 'closing';
  sealedHidePrompt();
  sealedLater(() => {
    sealedPrint('sealing.');
    sealedLater(() => {
      sealedPrint('sealed. thank you.');
      sealedPhase = 'closed';
      hasOpenedSealed = true;
      sealedSetButton('OPEN AGAIN', false);
      openSealed.focus();
    }, 600);
  }, 250);
}

termInput.addEventListener('keydown', e => {
  if (e.key === 'Escape') { sealedSeal(); return; }
  if (e.key !== 'Enter') return;
  const raw = termInput.value.trim();
  if (!raw) return;
  sealedPrint(`› ${raw}`);
  const value = raw.toLowerCase();
  termInput.value = '';
  if (['close', 'seal', 'seal it', 'close it'].includes(value)) {
    sealedSeal();
  } else {
    sealedMisses += 1;
    sealedLater(() => {
      sealedPrint(sealedMisses === 1 ? `“${raw}” is not how you left it.` : 'it only understands “close”.');
      termInput.focus();
    }, reduceMotion.matches ? 0 : 450);
  }
});

// Impossible map: gentle perspective only for pointer users who allow motion.
const mapCard = $('#mapCard');
if (mapCard) {
  mapCard.addEventListener('pointermove', e => {
    if (reduceMotion.matches) return;
    const r = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - .5;
    const y = (e.clientY - r.top) / r.height - .5;
    e.currentTarget.style.transform = `perspective(900px) rotateX(${y * -2.5}deg) rotateY(${x * 3}deg)`;
  });
  mapCard.addEventListener('pointerleave', e => { e.currentTarget.style.transform = ''; });
}

// Hidden margin protocol: deterministic easter egg; no network, no private state.
const marginNote = $('#marginNote');
const marginClose = $('#marginClose');
const ownerFooter = $('#ownerFooter');
let typed = '';
let footerClicks = 0;
let footerTimer = null;

function revealMargin() {
  if (!marginNote.hidden) return;
  marginNote.hidden = false;
  corruptOnce(marginNote);
}

function hideMargin() {
  if (marginNote.hidden) return;
  marginNote.hidden = true;
  ownerFooter.focus({ preventScroll: true });
}

marginClose.addEventListener('click', hideMargin);
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !marginNote.hidden) { hideMargin(); return; }
  const target = e.target;
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) return;
  if (e.key && e.key.length === 1) {
    typed = (typed + e.key.toLowerCase()).slice(-10);
    if (typed.endsWith('afterimage')) { revealMargin(); typed = ''; }
  }
});

ownerFooter.addEventListener('click', () => {
  footerClicks += 1;
  clearTimeout(footerTimer);
  footerTimer = setTimeout(() => { footerClicks = 0; }, 2000);
  if (footerClicks >= 3) {
    footerClicks = 0;
    if (marginNote.hidden) revealMargin(); else hideMargin();
  }
});
