"""
build_trainer.py
Reads vocabulary.csv and writes trainer.html — a self-contained, offline-capable
Latin vocabulary flashcard trainer.  Re-run whenever vocabulary.csv changes.
"""

import csv
import json
import os

CSV_PATH       = "vocabulary.csv"
HTML_PATH      = "trainer.html"
SENTENCES_PATH = "sentences.json"


def load_vocab(path, sentences):
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            {
                "id": i,
                "la": row["latin"].strip(),
                "de": row["german"].strip(),
                "ex": sentences.get(row["latin"].strip(), ""),
            }
            for i, row in enumerate(reader)
            if row["latin"].strip() and row["german"].strip()
        ]


def load_sentences(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
  <title>Latein Vokabeltrainer</title>
  <style>
    :root {
      --bg:       #f1f5f9;
      --surface:  #ffffff;
      --primary:  #4f46e5;
      --pri-dark: #3730a3;
      --pri-lite: #ede9fe;
      --ok:       #16a34a;
      --ok-lite:  #dcfce7;
      --warn:     #b45309;
      --warn-lite:#fef3c7;
      --bad:      #dc2626;
      --bad-lite: #fee2e2;
      --text:     #0f172a;
      --muted:    #64748b;
      --border:   #e2e8f0;
      --r:        14px;
      --shadow:   0 2px 16px rgba(0,0,0,.08);
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg); color: var(--text);
      display: flex; flex-direction: column; align-items: center;
      min-height: 100vh;
    }
    /* ── screens ──────────────────────────────────────────── */
    .screen {
      display: none; flex-direction: column; align-items: center;
      width: 100%; max-width: 480px; min-height: 100vh; padding: 0 20px 40px;
    }
    .screen.active { display: flex; }

    /* ── shared buttons ───────────────────────────────────── */
    .btn-main {
      width: 100%; padding: 15px; border: none; border-radius: var(--r);
      background: var(--primary); color: #fff;
      font-size: 1rem; font-weight: 600; cursor: pointer;
      transition: background .2s, transform .1s;
    }
    .btn-main:hover  { background: var(--pri-dark); }
    .btn-main:active { transform: scale(.98); }
    .btn-ghost {
      width: 100%; padding: 13px; border: 2px solid var(--primary);
      border-radius: var(--r); background: transparent; color: var(--primary);
      font-size: 1rem; font-weight: 600; cursor: pointer;
      transition: background .2s;
    }
    .btn-ghost:hover { background: var(--pri-lite); }

    /* ── HOME ─────────────────────────────────────────────── */
    .home-title    { font-size: 2rem; font-weight: 700; margin-top: 48px; letter-spacing: -.5px; }
    .home-sub      { color: var(--muted); font-size: .9rem; margin-bottom: 36px; }
    .card-box {
      width: 100%; background: var(--surface); border-radius: var(--r);
      box-shadow: var(--shadow); padding: 22px; margin-bottom: 14px;
    }
    .box-label {
      font-size: .75rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: .07em; color: var(--muted); margin-bottom: 6px;
    }
    .mastery-num {
      font-size: 2.4rem; font-weight: 700; color: var(--primary); line-height: 1;
      margin-bottom: 6px;
    }
    .mastery-num span { font-size: 1.1rem; font-weight: 400; color: var(--muted); }
    .seen-num {
      font-size: 1rem; color: var(--muted); margin-bottom: 12px;
    }
    .seen-num strong { color: var(--warn); font-weight: 600; }
    .bucket-bar {
      display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: var(--border);
    }
    .bucket-bar div { transition: width .5s ease; }
    .legend {
      display: flex; gap: 14px; margin-top: 10px; flex-wrap: wrap;
    }
    .legend-item {
      display: flex; align-items: center; gap: 5px;
      font-size: .78rem; color: var(--muted);
    }
    .legend-dot { width: 9px; height: 9px; border-radius: 50%; }
    /* toggle */
    .row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; }
    .row + .row { border-top: 1px solid var(--border); }
    .row-label { font-size: .95rem; font-weight: 500; }
    .toggle { position: relative; display: inline-block; width: 44px; height: 24px; }
    .toggle input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute; inset: 0; cursor: pointer;
      background: var(--border); border-radius: 24px; transition: .3s;
    }
    .slider::before {
      content: ""; position: absolute;
      width: 18px; height: 18px; left: 3px; bottom: 3px;
      background: #fff; border-radius: 50%; transition: .3s;
    }
    .toggle input:checked + .slider { background: var(--primary); }
    .toggle input:checked + .slider::before { transform: translateX(20px); }
    .dir-label { font-size: .85rem; color: var(--muted); }
    .btn-main { margin-bottom: 10px; }
    .btn-reset {
      background: none; border: none; color: var(--bad);
      font-size: .85rem; cursor: pointer; padding: 6px; margin-top: 6px;
    }
    .btn-list-link {
      background: none; border: none; color: var(--primary);
      font-size: .85rem; cursor: pointer; padding: 6px; text-decoration: underline;
    }
    /* ── LIST SCREEN ──────────────────────────────────────────────────────── */
    .list-header {
      display: flex; align-items: center; gap: 12px;
      width: 100%; padding: 16px 0 12px; position: sticky; top: 0;
      background: var(--bg); z-index: 1;
    }
    .list-title { font-size: 1.1rem; font-weight: 700; flex: 1; }
    .list-count { font-size: .82rem; color: var(--muted); }
    .list-table {
      width: 100%; border-collapse: collapse;
      background: var(--surface); border-radius: var(--r);
      box-shadow: var(--shadow); overflow: hidden;
      margin-bottom: 24px;
    }
    .list-table tr { border-bottom: 1px solid var(--border); }
    .list-table tr:last-child { border-bottom: none; }
    .list-table td { padding: 10px 14px; font-size: .88rem; vertical-align: top; }
    .list-table td:first-child { font-style: italic; width: 48%; border-right: 1px solid var(--border); }
    .list-table td:last-child { color: var(--muted); }

    /* ── CARD SCREEN ──────────────────────────────────────── */
    .session-bar {
      display: flex; align-items: center; gap: 12px; width: 100%; padding: 16px 0 20px;
    }
    .btn-quit {
      background: none; border: none; font-size: 1.1rem;
      color: var(--muted); cursor: pointer; padding: 4px 8px;
      border-radius: 8px; flex-shrink: 0;
    }
    .btn-quit:hover { background: var(--border); }
    .prog-bar { flex: 1; height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }
    .prog-fill { height: 100%; background: var(--primary); border-radius: 3px; transition: width .4s ease; }
    .card-counter { font-size: .82rem; color: var(--muted); font-weight: 600; flex-shrink: 0; }
    /* flip card */
    .card-scene { width: 100%; perspective: 900px; flex: 1; display: flex; align-items: center; }
    .card-wrap {
      width: 100%; min-height: 260px; cursor: pointer; user-select: none;
      transform-style: preserve-3d; transition: transform .55s cubic-bezier(.23,1,.32,1);
      position: relative;
    }
    .card-wrap.flipped { transform: rotateY(180deg); }
    .card-face {
      position: absolute; inset: 0; width: 100%; min-height: 260px;
      background: var(--surface); border-radius: var(--r); box-shadow: var(--shadow);
      backface-visibility: hidden; -webkit-backface-visibility: hidden;
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; padding: 32px 28px; text-align: center;
    }
    .card-back { transform: rotateY(180deg); background: #fafbff; }
    .card-pill {
      font-size: .7rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: .1em; padding: 3px 12px; border-radius: 20px; margin-bottom: 18px;
    }
    .card-face:first-child .card-pill { background: var(--pri-lite); color: var(--primary); }
    .card-back .card-pill { background: var(--ok-lite); color: var(--ok); }
    .card-text {
      font-size: clamp(1.1rem, 4vw, 1.55rem);
      font-weight: 600; line-height: 1.5; color: var(--text);
      overflow-wrap: break-word; word-break: break-word; max-width: 100%;
    }
    .card-hint { margin-top: 24px; font-size: .82rem; color: var(--muted); }
    .kbd-hint   { font-size: .72rem; color: #c4b5fd; margin-top: 4px; }
    .card-example {
      margin-top: 18px; font-size: .82rem; color: var(--muted);
      font-style: italic; line-height: 1.5;
    }
    /* rating */
    .rating-row {
      display: flex; gap: 10px; width: 100%; padding: 20px 0 8px;
      opacity: 0; pointer-events: none; transition: opacity .25s;
    }
    .rating-row.visible { opacity: 1; pointer-events: auto; }
    .btn-rate {
      flex: 1; padding: 14px 6px; border: none; border-radius: var(--r);
      font-size: .85rem; font-weight: 600; cursor: pointer; line-height: 1.4;
      transition: transform .1s;
    }
    .btn-rate:active { transform: scale(.95); }
    .rate-wrong  { background: var(--bad-lite);  color: var(--bad);  }
    .rate-almost { background: var(--warn-lite); color: var(--warn); }
    .rate-ok     { background: var(--ok-lite);   color: var(--ok);   }
    .rate-wrong:hover  { background: #fecaca; }
    .rate-almost:hover { background: #fde68a; }
    .rate-ok:hover     { background: #bbf7d0; }
    .kbd-row { text-align: center; font-size: .72rem; color: var(--muted); padding-bottom: 4px; }

    /* ── SUMMARY ──────────────────────────────────────────── */
    .sum-title  { font-size: 1.8rem; font-weight: 700; margin-top: 48px; }
    .sum-sub    { color: var(--muted); margin: 6px 0 28px; }
    .stats-row  { display: flex; gap: 10px; width: 100%; margin-bottom: 16px; }
    .stat-box   {
      flex: 1; background: var(--surface); border-radius: var(--r);
      box-shadow: var(--shadow); padding: 18px 10px; text-align: center;
    }
    .stat-n     { font-size: 2rem; font-weight: 700; line-height: 1; margin-bottom: 4px; }
    .stat-lbl   { font-size: .78rem; color: var(--muted); font-weight: 500; }
    .stat-ok   .stat-n { color: var(--ok);   }
    .stat-alm  .stat-n { color: var(--warn); }
    .stat-bad  .stat-n { color: var(--bad);  }
    .sum-info {
      width: 100%; background: var(--surface); border-radius: var(--r);
      box-shadow: var(--shadow); padding: 18px 22px; margin-bottom: 16px;
      text-align: center; font-size: .92rem; color: var(--muted);
    }
    .sum-info strong { color: var(--primary); font-size: 1.05rem; }
    .missed-box {
      width: 100%; background: var(--surface); border-radius: var(--r);
      box-shadow: var(--shadow); padding: 16px 20px; margin-bottom: 20px;
    }
    .missed-title {
      font-size: .75rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: .07em; color: var(--muted); margin-bottom: 10px;
    }
    .missed-item {
      display: flex; justify-content: space-between; align-items: baseline;
      gap: 12px; padding: 7px 0; border-bottom: 1px solid var(--border);
      font-size: .88rem;
    }
    .missed-item:last-child { border-bottom: none; }
    .m-la { font-style: italic; flex-shrink: 0; }
    .m-de { color: var(--muted); text-align: right; }
    .btn-main { margin-bottom: 10px; }

    /* ── footer ───────────────────────────────────────────── */
    .footer {
      margin-top: auto; padding: 24px 0 8px;
      font-size: .78rem; color: var(--muted);
    }
    .footer a { color: var(--muted); text-decoration: underline; cursor: pointer; }

    /* ── modal ────────────────────────────────────────────── */
    .modal-overlay {
      display: none; position: fixed; inset: 0;
      background: rgba(0,0,0,.45); z-index: 100;
      align-items: center; justify-content: center;
    }
    .modal-overlay.open { display: flex; }
    .modal-box {
      background: var(--surface); border-radius: var(--r);
      box-shadow: 0 8px 40px rgba(0,0,0,.2);
      padding: 28px 28px 22px; max-width: 340px; width: 90%;
    }
    .modal-title { font-weight: 700; margin-bottom: 12px; }
    .modal-body  { font-size: .88rem; color: var(--muted); line-height: 1.6; }
    .modal-close {
      margin-top: 18px; width: 100%; padding: 10px; border: none;
      border-radius: var(--r); background: var(--border);
      font-size: .9rem; font-weight: 600; cursor: pointer;
    }
    .modal-close:hover { background: #cbd5e1; }
  </style>
</head>
<body>

<!-- ═══ HOME ═══════════════════════════════════════════════════════════════ -->
<div id="screen-home" class="screen">
  <h1 class="home-title">🏛️ Latein Trainer</h1>
  <p class="home-sub">Vokabeltrainer für das Abitur</p>

  <div class="card-box">
    <div class="box-label">Fortschritt</div>
    <div class="mastery-num" id="h-mastery">0 <span>/ __TOTAL__ gelernt</span></div>
    <div class="seen-num"   id="h-seen"></div>
    <div class="bucket-bar" id="h-bar"></div>
    <div class="legend">
      <div class="legend-item"><div class="legend-dot" style="background:#e2e8f0"></div>Neu</div>
      <div class="legend-item"><div class="legend-dot" style="background:#fbbf24"></div>Lernend</div>
      <div class="legend-item"><div class="legend-dot" style="background:#4ade80"></div>Gelernt</div>
    </div>
  </div>

  <div class="card-box">
    <div class="row">
      <span class="row-label">Richtung</span>
      <span class="dir-label" id="h-dir-label">Latein → Deutsch</span>
    </div>
    <div class="row">
      <span class="row-label">Umkehren (DE → LA)</span>
      <label class="toggle">
        <input type="checkbox" id="toggle-dir">
        <span class="slider"></span>
      </label>
    </div>
  </div>

  <button class="btn-main" id="btn-start">Übung starten (5 Karten)</button>
  <button class="btn-list-link" id="btn-list">Alle Vokabeln anzeigen</button>
  <button class="btn-reset" id="btn-reset">Fortschritt zurücksetzen</button>
  <div class="footer"><a id="btn-datenschutz">Datenschutz</a></div>
</div>

<!-- ═══ DATENSCHUTZ MODAL ══════════════════════════════════════════════════ -->
<div class="modal-overlay" id="modal-datenschutz">
  <div class="modal-box">
    <div class="modal-title">Datenschutz</div>
    <div class="modal-body">
      Diese App speichert Daten (Lernfortschritt) ausschließlich lokal
      in Ihrem Browser (localStorage). Es werden keine persönlichen Daten
      erhoben, gespeichert oder übertragen.
    </div>
    <button class="modal-close" id="btn-datenschutz-close">Schließen</button>
  </div>
</div>

<!-- ═══ LIST ═════════════════════════════════════════════════════════════════ -->
<div id="screen-list" class="screen">
  <div class="list-header">
    <button class="btn-quit" id="btn-list-back">←</button>
    <span class="list-title">Alle Vokabeln</span>
    <span class="list-count">__TOTAL__ Einträge</span>
  </div>
  <table class="list-table" id="list-table"></table>
</div>

<!-- ═══ CARD ════════════════════════════════════════════════════════════════ -->
<div id="screen-card" class="screen">
  <div class="session-bar">
    <button class="btn-quit" id="btn-quit" title="Abbrechen">✕</button>
    <div class="prog-bar"><div class="prog-fill" id="c-fill"></div></div>
    <span class="card-counter" id="c-counter">1 / 20</span>
  </div>

  <div class="card-scene">
    <div class="card-wrap" id="card-wrap" tabindex="0" role="button">
      <div class="card-face card-front">
        <div class="card-pill" id="front-pill">Latein</div>
        <div class="card-text" id="front-text"></div>
        <div class="card-example" id="front-example"></div>
        <div class="card-hint">Tippen zum Umdrehen</div>
        <div class="kbd-hint">[ Leertaste ]</div>
      </div>
      <div class="card-face card-back">
        <div class="card-pill" id="back-pill">Deutsch</div>
        <div class="card-text" id="back-text"></div>
        <div class="card-example" id="back-example"></div>
        <div class="kbd-hint" style="margin-top:20px">[1] Nicht gewusst · [2] Fast · [3] Gewusst</div>
      </div>
    </div>
  </div>

  <div class="rating-row" id="rating-row">
    <button class="btn-rate rate-wrong"  data-r="0">✗<br><small>Nicht gewusst</small></button>
    <button class="btn-rate rate-almost" data-r="1">～<br><small>Fast</small></button>
    <button class="btn-rate rate-ok"     data-r="2">✓<br><small>Gewusst!</small></button>
  </div>
</div>

<!-- ═══ SUMMARY ══════════════════════════════════════════════════════════════ -->
<div id="screen-summary" class="screen">
  <h2 class="sum-title">Gut gemacht! 🎉</h2>
  <p class="sum-sub" id="sum-sub"></p>

  <div class="stats-row">
    <div class="stat-box stat-ok">
      <div class="stat-n" id="s-ok">0</div><div class="stat-lbl">Gewusst</div>
    </div>
    <div class="stat-box stat-alm">
      <div class="stat-n" id="s-alm">0</div><div class="stat-lbl">Fast</div>
    </div>
    <div class="stat-box stat-bad">
      <div class="stat-n" id="s-bad">0</div><div class="stat-lbl">Nicht gewusst</div>
    </div>
  </div>

  <div class="sum-info" id="s-mastery"></div>

  <div class="missed-box" id="missed-box">
    <div class="missed-title">Noch üben</div>
    <div id="missed-items"></div>
  </div>

  <button class="btn-main"  id="btn-again">Weiter üben</button>
  <button class="btn-ghost" id="btn-home">Startseite</button>
</div>

<script>
/* ── vocabulary data ─────────────────────────────────────────────────────── */
const VOCAB = __VOCAB_DATA__;

/* ── constants ──────────────────────────────────────────────────────────── */
const TOTAL         = VOCAB.length;
const SESSION_SIZE  = 5;
const MASTERY_AT    = 3;   // score threshold for "mastered"
const STORAGE_KEY   = 'audrey-latin-v1';

/* ── persistent state ───────────────────────────────────────────────────── */
let cards    = {};   // { [id]: { score:0, lastSeen:0 } }
let reversed = false;

function loadState() {
  try {
    const s = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    cards    = s.cards    || {};
    reversed = s.reversed || false;
  } catch (_) {}
}

function saveState() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ cards, reversed })); } catch (_) {}
}

function cardOf(id) {
  return cards[id] || (cards[id] = { score: 0, lastSeen: 0 });
}

/* ── session state ───────────────────────────────────────────────────────── */
let ses = null;  // { queue, index, flipped, ok, alm, bad, missed }

/* ── session selection ───────────────────────────────────────────────────── */
function buildSession() {
  const now = Date.now();
  const scored = VOCAB.map(w => {
    const c  = cardOf(w.id);
    const hrs = c.lastSeen ? (now - c.lastSeen) / 3_600_000 : Math.random() * 9_999;
    return { w, pri: (MASTERY_AT - Math.min(c.score, MASTERY_AT)) * 10_000 + Math.min(hrs, 9_999) };
  });
  scored.sort((a, b) => b.pri - a.pri);
  const queue = scored.slice(0, SESSION_SIZE).map(x => x.w);
  // Shuffle so presentation order is random within each session
  for (let i = queue.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [queue[i], queue[j]] = [queue[j], queue[i]];
  }
  return queue;
}

/* ── screen switching ────────────────────────────────────────────────────── */
let currentScreen = 'screen-home';
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  currentScreen = id;
}

/* ── HOME ─────────────────────────────────────────────────────────────────── */
function renderHome() {
  let unseen = 0, learning = 0, mastered = 0;
  VOCAB.forEach(w => {
    const s = cardOf(w.id).score;
    if      (s >= MASTERY_AT) mastered++;
    else if (s > 0)           learning++;
    else                      unseen++;
  });

  const seen = learning + mastered;
  document.getElementById('h-mastery').innerHTML =
    `${mastered} <span>/ ${TOTAL} gelernt</span>`;
  document.getElementById('h-seen').innerHTML = seen > 0
    ? `<strong>${seen}</strong> bereits gesehen &nbsp;·&nbsp; ${mastered} sicher gelernt`
    : `Noch keine Vokabeln geübt`;

  const bar = document.getElementById('h-bar');
  const segs = [
    { pct: unseen  / TOTAL * 100, color: '#e2e8f0' },
    { pct: learning/ TOTAL * 100, color: '#fbbf24' },
    { pct: mastered/ TOTAL * 100, color: '#4ade80' },
  ];
  bar.innerHTML = segs.map(s =>
    `<div style="width:${s.pct}%;background:${s.color}"></div>`
  ).join('');

  document.getElementById('toggle-dir').checked = reversed;
  document.getElementById('h-dir-label').textContent =
    reversed ? 'Deutsch → Latein' : 'Latein → Deutsch';
}

/* ── CARD ─────────────────────────────────────────────────────────────────── */
function startSession() {
  ses = { queue: buildSession(), index: 0, flipped: false,
          ok: 0, alm: 0, bad: 0, missed: [] };
  showScreen('screen-card');
  renderCard();
}

function renderCard() {
  const w  = ses.queue[ses.index];
  const n  = ses.queue.length;

  document.getElementById('c-fill').style.width = `${ses.index / n * 100}%`;
  document.getElementById('c-counter').textContent = `${ses.index + 1} / ${n}`;

  const front = reversed ? w.de : w.la;
  const back  = reversed ? w.la : w.de;

  document.getElementById('front-pill').textContent = reversed ? 'Deutsch' : 'Latein';
  document.getElementById('back-pill').textContent  = reversed ? 'Latein'  : 'Deutsch';
  document.getElementById('front-text').textContent = front;
  document.getElementById('back-text').textContent  = back;

  // Example sentence: on front only in LA→DE mode; on back always
  const ex = w.ex || '';
  document.getElementById('front-example').textContent = (!reversed && ex) ? ex : '';
  document.getElementById('back-example').textContent  = ex;

  const wrap = document.getElementById('card-wrap');
  wrap.classList.remove('flipped');
  ses.flipped = false;

  document.getElementById('rating-row').classList.remove('visible');
}

function flipCard() {
  if (ses.flipped) return;
  ses.flipped = true;
  document.getElementById('card-wrap').classList.add('flipped');
  document.getElementById('rating-row').classList.add('visible');
}

function rate(r) {
  if (!ses || !ses.flipped) return;
  const w = ses.queue[ses.index];
  const c = cardOf(w.id);

  if      (r === 2) { c.score = Math.min(c.score + 1, 5); ses.ok++;  }
  else if (r === 1) {                                       ses.alm++; }
  else              { c.score = Math.max(c.score - 1, 0); ses.bad++;
                      ses.missed.push(w); }
  c.lastSeen = Date.now();
  saveState();

  ses.index++;
  if (ses.index >= ses.queue.length) showSummary();
  else renderCard();
}

/* ── SUMMARY ─────────────────────────────────────────────────────────────── */
function showSummary() {
  const mastered = VOCAB.filter(w => cardOf(w.id).score >= MASTERY_AT).length;
  const seen     = VOCAB.filter(w => cardOf(w.id).score > 0).length;
  const pct      = Math.round(ses.ok / ses.queue.length * 100);

  document.getElementById('sum-sub').textContent   = `${pct}% richtig in dieser Runde`;
  document.getElementById('s-ok').textContent      = ses.ok;
  document.getElementById('s-alm').textContent     = ses.alm;
  document.getElementById('s-bad').textContent     = ses.bad;
  document.getElementById('s-mastery').innerHTML   =
    `Bereits gesehen: <strong>${seen} / ${TOTAL}</strong> &nbsp;·&nbsp; Sicher gelernt: <strong>${mastered} / ${TOTAL}</strong>`;

  const box   = document.getElementById('missed-box');
  const items = document.getElementById('missed-items');
  if (ses.missed.length > 0) {
    items.innerHTML = ses.missed.map(w =>
      `<div class="missed-item">
        <span class="m-la">${w.la}</span>
        <span class="m-de">${w.de}</span>
       </div>`
    ).join('');
    box.style.display = '';
  } else {
    box.style.display = 'none';
  }

  showScreen('screen-summary');
}

/* ── events ──────────────────────────────────────────────────────────────── */
document.getElementById('btn-start').addEventListener('click', startSession);
document.getElementById('btn-again').addEventListener('click', startSession);
document.getElementById('btn-home').addEventListener('click', () => {
  renderHome(); showScreen('screen-home');
});
document.getElementById('btn-quit').addEventListener('click', () => {
  if (confirm('Übung abbrechen?')) { renderHome(); showScreen('screen-home'); }
});
document.getElementById('toggle-dir').addEventListener('change', e => {
  reversed = e.target.checked;
  document.getElementById('h-dir-label').textContent =
    reversed ? 'Deutsch → Latein' : 'Latein → Deutsch';
  saveState();
});
document.getElementById('btn-list').addEventListener('click', () => {
  const tbody = document.getElementById('list-table');
  if (!tbody.hasChildNodes()) {
    tbody.innerHTML = VOCAB.map(w =>
      `<tr><td>${w.la}</td><td>${w.de}</td></tr>`
    ).join('');
  }
  showScreen('screen-list');
});
document.getElementById('btn-list-back').addEventListener('click', () => {
  showScreen('screen-home');
});

document.getElementById('btn-reset').addEventListener('click', () => {
  if (confirm('Wirklich alle Fortschritte löschen?')) {
    cards = {}; saveState(); renderHome();
  }
});

document.getElementById('card-wrap').addEventListener('click', flipCard);

document.querySelectorAll('.btn-rate').forEach(btn =>
  btn.addEventListener('click', () => rate(+btn.dataset.r))
);

document.addEventListener('keydown', e => {
  if (currentScreen !== 'screen-card') return;
  if (e.key === ' ' || e.key === 'ArrowRight') { e.preventDefault(); flipCard(); }
  if (ses?.flipped) {
    if (e.key === '1') rate(0);
    if (e.key === '2') rate(1);
    if (e.key === '3') rate(2);
  }
});

document.getElementById('btn-datenschutz').addEventListener('click', () => {
  document.getElementById('modal-datenschutz').classList.add('open');
});
document.getElementById('btn-datenschutz-close').addEventListener('click', () => {
  document.getElementById('modal-datenschutz').classList.remove('open');
});
document.getElementById('modal-datenschutz').addEventListener('click', e => {
  if (e.target === e.currentTarget)
    e.currentTarget.classList.remove('open');
});

/* ── init ─────────────────────────────────────────────────────────────────── */
loadState();
renderHome();
showScreen('screen-home');
</script>
</body>
</html>
"""


def main():
    sentences = load_sentences(SENTENCES_PATH)
    vocab     = load_vocab(CSV_PATH, sentences)
    vocab_json = json.dumps(vocab, ensure_ascii=False)

    with_ex = sum(1 for v in vocab if v["ex"])
    print(f"Loaded {len(vocab)} vocab entries, {with_ex} with example sentences.")

    html = HTML_TEMPLATE.replace("__VOCAB_DATA__", vocab_json)
    html = html.replace("__TOTAL__", str(len(vocab)))

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Written {HTML_PATH}.")


if __name__ == "__main__":
    main()
