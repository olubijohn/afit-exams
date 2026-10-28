/* NCAT Exams — single-page app. Questions ship in data/questions.json; accounts and results live in Supabase. */
(() => {
'use strict';

const C = window.NCAT_CONFIG;
const sb = window.supabase.createClient(C.supabaseUrl, C.supabaseAnonKey, {
  auth: { persistSession: true, autoRefreshToken: true, storageKey: 'afit-exams-auth' },
});
const PASS = C.passMark || 75;
const SUBJECT_COLORS = ['#1d6fd8', '#0f8a5f', '#7c3aed', '#c2410c', '#0e7490', '#b45309', '#be185d', '#4d7c0f'];

/* ---------- helpers ---------- */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const store = {
  get(k, d = null) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* storage full or blocked */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* ignore */ } },
};
const uid = () => (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2));
const shuffle = a => { a = [...a]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);
const L = i => String.fromCharCode(65 + i);
const fmtTime = s => { s = Math.max(0, Math.round(s)); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60; return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(x).padStart(2, '0'); };
const fmtDur = s => (s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)} min` : `${Math.floor(s / 3600)}h ${Math.round((s % 3600) / 60)}m`);
const fmtDate = iso => { const d = new Date(iso), now = new Date(); const t = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }); if (d.toDateString() === now.toDateString()) return `Today, ${t}`; const y = new Date(now); y.setDate(now.getDate() - 1); if (d.toDateString() === y.toDateString()) return `Yesterday, ${t}`; return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: d.getFullYear() === now.getFullYear() ? undefined : 'numeric' }) + `, ${t}`; };
const initials = n => (n || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('');
const firstName = () => (S.profile?.full_name || '').split(' ')[0] || 'there';

const I = {
  plane: '<svg viewBox="0 0 24 24"><path d="M12 2c.8 0 1.4.9 1.4 2v5.2l7.6 4.3v2.2l-7.6-2.3v4.8l2.2 1.6V21l-3.6-1-3.6 1v-1.2l2.2-1.6v-4.8L3 15.7v-2.2l7.6-4.3V4c0-1.1.6-2 1.4-2z"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>',
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/></svg>',
  play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="m10 8.5 5.5 3.5-5.5 3.5z"/></svg>',
  book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H20v15H5.5A1.5 1.5 0 0 0 4 19.5z"/><path d="M4 19.5A1.5 1.5 0 0 0 5.5 21H20"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  hist: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/></svg>',
  key: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="15" r="4"/><path d="m10.8 12.2 9.2-9.2M17 6l3 3M15 8l2 2"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
  out: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>',
  flag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 21V4h11l-1.5 4L16 12H5"/></svg>',
  left: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>',
  right: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
  target: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></svg>',
  star: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z"/></svg>',
  layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/></svg>',
  cloud: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 18a5 5 0 1 1 .9-9.9A6 6 0 0 1 19 10a4 4 0 0 1-1 8z"/></svg>',
  mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>',
  chev: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>',
};
const credit = cls => `<p class="credit ${cls || ''}">Built by Olubi_Dev · <a href="tel:+2348131351217">08131351217</a></p>`;
const logo = (sub = '') => `<a class="logo" href="#/"><span class="logo-mark">${I.plane}</span><span>NCAT Exams${sub ? `<small>${esc(sub)}</small>` : ''}</span></a>`;

/* ---------- state ---------- */
const S = {
  user: null, profile: null,
  bank: [], subjects: [], byId: new Map(), subj: {},
  stats: new Map(), attempts: [], quiz: null, timer: null, pos: new Map(),
  setup: null, bankView: { q: '', s: 'all', show: true, limit: 25 }, reviewFilter: 'wrong', prefill: '',
};
const qKey = () => `afit:quiz:${S.user?.id}`;
const pKey = () => `afit:pending:${S.user?.id}`;
const prKey = () => `afit:progress:${S.user?.id}`;
const saveQuiz = () => S.quiz ? store.set(qKey(), S.quiz) : store.del(qKey());

/* ---------- ui primitives ---------- */
const mount = html => { $('#app').innerHTML = html; };
function toast(msg, kind = '') {
  const el = document.createElement('div');
  el.className = `toast ${kind}`; el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), 3600);
}
function dialog({ title, body, ok = 'OK', cancel = 'Cancel', danger = false }) {
  const d = $('#modal');
  d.innerHTML = `<form method="dialog" class="modal-in"><h3>${esc(title)}</h3><p>${body}</p><div class="modal-actions">${cancel ? `<button class="btn" value="no">${esc(cancel)}</button>` : ''}<button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" value="yes">${esc(ok)}</button></div></form>`;
  return new Promise(res => { d.onclose = () => res(d.returnValue === 'yes'); d.returnValue = ''; d.showModal(); });
}
function formMsg(form, text, kind = 'err') { const m = $('.form-msg', form); m.className = `form-msg show ${kind}`; m.textContent = text; }
function busy(form, on, label) {
  const b = $('button[type=submit]', form);
  if (on) { b.dataset.label = b.textContent; b.textContent = label || 'Please wait…'; b.disabled = true; }
  else { b.textContent = b.dataset.label || b.textContent; b.disabled = false; }
}
function applyTheme(t) { if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; }

/* ---------- data ---------- */
async function loadProfile(user) {
  let { data, error } = await sb.from('afit_profiles').select('*').eq('id', user.id).maybeSingle();
  if (error) throw error;
  if (!data) {
    const full_name = String(user.user_metadata?.full_name || user.email.split('@')[0]).slice(0, 80);
    const ins = await sb.from('afit_profiles').insert({ id: user.id, email: user.email.toLowerCase(), full_name }).select().single();
    if (ins.error) throw ins.error;
    data = ins.data;
  }
  const local = store.get(`afit:progress:${user.id}`, null);
  data.progress ||= {};
  if (local?.c) {
    const c = (data.progress.c ||= {});
    let ahead = false;
    for (const [k, v] of Object.entries(local.c)) if (v > (c[k] || 0)) { c[k] = v; ahead = true; }
    data.progress.last ||= local.last;
    if (ahead) sb.from('afit_profiles').update({ progress: data.progress }).eq('id', user.id).then(() => {});
  }
  sb.from('afit_profiles').update({ last_seen_at: new Date().toISOString() }).eq('id', user.id).then(() => {});
  return data;
}
async function loadStats() {
  const { data, error } = await sb.from('afit_question_stats').select('question_id, subject, seen, correct, last_correct').limit(5000);
  if (error) throw error;
  S.stats = new Map(data.map(r => [r.question_id, r]));
}
async function loadAttempts() {
  const { data, error } = await sb.from('afit_attempts').select('id, client_id, mode, title, subjects, total, answered, correct, score_pct, duration_sec, created_at').order('created_at', { ascending: false }).limit(200);
  if (error) throw error;
  const pending = store.get(pKey(), []).map(j => j.payload).filter(p => !data.some(r => r.client_id === p.client_id));
  S.attempts = [...pending, ...data];
}
let loading = null;
async function setUser(user) {
  if (!user) { S.user = S.profile = S.quiz = null; S.stats = new Map(); S.attempts = []; stopTimer(); return; }
  if (S.user?.id === user.id && S.profile) return;
  if (loading?.id === user.id) return loading.p;
  const p = (async () => {
    S.user = user;
    S.profile = await loadProfile(user);
    S.quiz = store.get(qKey(), null);
    await Promise.all([loadStats(), loadAttempts()]);
    flushPending();
  })();
  loading = { id: user.id, p };
  try { await p; } catch (e) { S.user = null; S.profile = null; throw e; } finally { loading = null; }
}

let flushing = false;
async function flushPending() {
  if (!S.user || flushing) return;
  flushing = true;
  try {
    const q = store.get(pKey(), []);
    while (q.length) {
      const job = q[0];
      const { error } = await sb.from('afit_attempts').upsert({ ...job.payload, user_id: S.user.id }, { onConflict: 'user_id,client_id', ignoreDuplicates: true });
      if (error) { console.warn('save attempt', error.message); break; }
      if (job.items.length) {
        const r = await sb.rpc('afit_record_answers', { p_items: job.items });
        if (r.error) { console.warn('save answers', r.error.message); break; }
      }
      q.shift(); store.set(pKey(), q);
    }
    S.unsynced = q.length;
  } finally {
    flushing = false;
    const el = $('#sync');
    if (el) el.outerHTML = syncBadge();
  }
}
const syncBadge = () => flushing
  ? `<span id="sync" class="sync">${I.cloud} Saving…</span>`
  : S.unsynced
  ? `<span id="sync" class="sync warn">${I.cloud} Saved on this device. It will sync when you're back online.</span>`
  : `<span id="sync" class="sync ok">${I.check} Saved to your account</span>`;

/* ---------- going through the paper in order ---------- */
const progress = () => (S.profile.progress ||= {});
const cursor = s => progress().c?.[s] || 0;
const sourceOk = (st, q) => st.source === 'all' || (st.source === 'new' && !S.stats.has(q.id)) || (st.source === 'missed' && S.stats.get(q.id)?.last_correct === false);
// the next block after where this person stopped, numbered across the chosen subjects
function seqBlock(st) {
  const full = S.bank.filter(q => st.subjects.includes(q.s));
  const left = full.filter(q => S.pos.get(q.id) >= cursor(q.s) && sourceOk(st, q));
  const take = st.count === 'all' ? left : left.slice(0, st.count);
  const at = q => full.indexOf(q) + 1;
  return { ids: take.map(q => q.id), total: full.length, left: left.length, from: take.length ? at(take[0]) : 0, to: take.length ? at(take[take.length - 1]) : 0, started: full.some(q => cursor(q.s) > S.pos.get(q.id)) };
}
function saveProgress() {
  store.set(prKey(), progress());
  sb.from('afit_profiles').update({ progress: progress() }).eq('id', S.user.id).then(({ error }) => { if (error) console.warn('save progress', error.message); });
}
function resetCursor(subjects) {
  const c = (progress().c ||= {});
  subjects.forEach(s => delete c[s]);
  saveProgress();
}
const subjLabel = st => (st.subjects.length === 1 ? S.subj[st.subjects[0]].name : st.subjects.length === S.subjects.length ? 'All subjects' : `${st.subjects.length} subjects`)
  + (st.source === 'new' ? ' · not seen yet' : st.source === 'missed' ? ' · got wrong' : '');
function startSeq(st) {
  st = { ...st, subjects: st.subjects.filter(s => S.subj[s]) };
  const b = seqBlock(st);
  startQuiz({ title: `${subjLabel(st)} · Questions ${b.from}–${b.to}`, mode: st.mode, ids: b.ids, shuffleOpts: st.shuffle, subjects: st.subjects, seq: st });
}

/* ---------- quiz engine ---------- */
function quizScore(Q) {
  let correct = 0, answered = 0;
  Q.items.forEach((it, i) => { const c = Q.ans[i]; if (c !== null) { answered++; if (S.byId.get(it.q).a.includes(c)) correct++; } });
  return { correct, answered, wrong: answered - correct, skipped: Q.items.length - answered, total: Q.items.length };
}
function startQuiz({ title, mode, ids, shuffleOpts = true, subjects, seq = null }) {
  if (!ids.length) return toast('No questions match those settings.', 'err');
  const items = ids.map(id => { const q = S.byId.get(id); const o = q.o.map((_, i) => i); return { q: id, o: shuffleOpts ? shuffle(o) : o }; });
  S.quiz = {
    v: 1, id: uid(), title, mode, seq, subjects: subjects || [...new Set(items.map(it => S.byId.get(it.q).s))],
    items, ans: items.map(() => null), flags: [], idx: 0, elapsed: 0,
    limit: mode === 'timed' ? items.length * 60 : null, startedAt: new Date().toISOString(),
  };
  saveQuiz();
  go('quiz');
}
function startTimer() {
  stopTimer();
  S.timer = setInterval(() => {
    const Q = S.quiz;
    if (!Q || Q.finished || document.hidden && Q.mode !== 'timed') return;
    Q.elapsed++;
    if (Q.elapsed % 5 === 0) saveQuiz();
    const t = $('#qtimer');
    if (t) {
      const left = Q.limit ? Q.limit - Q.elapsed : null;
      t.lastChild.textContent = fmtTime(left ?? Q.elapsed);
      t.classList.toggle('warn', left !== null && left <= 60);
    }
    if (Q.limit && Q.elapsed >= Q.limit) { toast('Time is up.'); finishQuiz(true); }
  }, 1000);
}
function stopTimer() { if (S.timer) clearInterval(S.timer); S.timer = null; }

async function finishQuiz(force = false) {
  const Q = S.quiz;
  if (!Q || Q.finished) return;
  const sc = quizScore(Q);
  if (!force && sc.skipped) {
    const ok = await dialog({ title: 'Finish now?', body: `You haven't answered ${sc.skipped} question${sc.skipped > 1 ? 's' : ''}. Unanswered questions count as wrong.`, ok: 'Finish', cancel: 'Keep going' });
    if (!ok) return;
  }
  stopTimer();
  Q.finished = true;
  Q.finishedAt = new Date().toISOString();
  saveQuiz();
  const payload = {
    client_id: Q.id, mode: Q.mode, title: Q.title, subjects: Q.subjects, total: sc.total, answered: sc.answered,
    correct: sc.correct, score_pct: +((sc.correct / sc.total) * 100).toFixed(2), duration_sec: Q.elapsed,
    answers: Q.items.map((it, i) => ({ q: it.q, o: it.o, c: Q.ans[i] })), created_at: Q.finishedAt,
  };
  const items = Q.items.map((it, i) => {
    if (Q.ans[i] === null) return null;
    const q = S.byId.get(it.q);
    return { q: it.q, s: q.s, ok: q.a.includes(Q.ans[i]) };
  }).filter(Boolean);
  items.forEach(x => {
    const s = S.stats.get(x.q) || { seen: 0, correct: 0 };
    S.stats.set(x.q, { question_id: x.q, subject: x.s, seen: s.seen + 1, correct: s.correct + (x.ok ? 1 : 0), last_correct: x.ok });
  });
  if (Q.seq) {
    const c = (progress().c ||= {});
    Q.items.forEach(it => { const q = S.byId.get(it.q); c[q.s] = Math.max(c[q.s] || 0, S.pos.get(q.id) + 1); });
    progress().last = Q.seq;
    saveProgress();
  }
  S.attempts.unshift(payload);
  const q = store.get(pKey(), []); q.push({ payload, items }); store.set(pKey(), q);
  S.unsynced = q.length;
  S.reviewFilter = sc.correct === sc.total ? 'all' : 'wrong';
  flushPending();
  go('results', true);
}

/* ---------- routing ---------- */
const AUTH = ['login', 'signup', 'forgot'];
function go(path, replace) {
  const h = '#/' + path;
  if (replace) { history.replaceState(null, '', h); route(); }
  else if (location.hash === h) route();
  else location.hash = h;
}
function route() {
  const [name = '', arg] = location.hash.replace(/^#\/?/, '').split('/');
  stopTimer();
  closeMenu();
  if (!S.user) return AUTH.includes(name) ? viewAuth(name) : go('login', true);
  if (S.profile?.must_change_password && name !== 'password') return go('password', true);
  if (AUTH.includes(name)) return go('', true);
  const views = { '': viewDashboard, practice: viewPractice, quiz: viewQuiz, results: viewResults, history: viewHistory, attempt: viewAttempt, bank: viewBank, password: viewPassword };
  (views[name] || viewDashboard)(arg && decodeURIComponent(arg));
  if (name !== 'quiz') window.scrollTo(0, 0);
}

/* ---------- shell ---------- */
function shell(active, body) {
  const links = [['', 'Home', I.home], ['practice', 'Practice', I.play], ['bank', 'Questions', I.book], ['history', 'History', I.hist]];
  const nav = cls => links.map(([p, t, ic]) => `<a href="#/${p}" class="${active === p ? 'active' : ''}">${ic}<span>${t}</span></a>`).join('');
  const theme = store.get('afit:theme', 'auto');
  return `<header class="topbar"><div class="topbar-in">${logo()}<nav class="nav">${nav()}</nav>
    <div class="menu-wrap"><button class="avatar-btn" data-act="menu" aria-haspopup="true" aria-label="Account"><span class="avatar">${esc(initials(S.profile.full_name))}</span><span class="nm">${esc(S.profile.full_name)}</span></button>
    <div class="menu" id="menu"><div class="menu-head"><b>${esc(S.profile.full_name)}</b><span>${esc(S.profile.email)}</span></div>
      <button data-act="goPassword">${I.key} Change password</button>
      <button data-act="theme">${I.moon} Theme: ${theme === 'auto' ? 'Match device' : theme === 'dark' ? 'Dark' : 'Light'}</button>
      <button data-act="signout">${I.out} Sign out</button></div></div></div></header>
  <main class="main">${body}${credit()}</main>
  <nav class="tabbar">${nav()}</nav>`;
}
function closeMenu() { $('#menu')?.classList.remove('open'); }

/* ---------- auth views ---------- */
function authLayout(inner) {
  const n = S.bank.length;
  mount(`<div class="auth">
    <aside class="auth-brand">
      ${logo()}
      <div>
        <h2>NCAT general paper practice</h2>
        <p class="lead">Past questions from the general paper, marked as you go.</p>
        <ul class="feat">
          <li><span class="tick">${I.check}</span><span><b>${n} questions</b> in ${S.subjects.length} subjects: air law, aerodynamics, sheet metal, hardware, drawings and human factors.</span></li>
          <li><span class="tick">${I.check}</span><span>Pick an answer and see straight away if it's right, and what the right answer is.</span></li>
          <li><span class="tick">${I.check}</span><span>Your scores are saved, so you can go back over the ones you missed.</span></li>
        </ul>
      </div>
      <div class="auth-foot">${credit()}</div>
    </aside>
    <section class="auth-main"><div class="auth-card"><div class="auth-mobile-logo">${logo()}</div>${inner}${credit('auth-credit')}</div></section>
  </div>`);
  const first = $('.auth-card input');
  if (first && matchMedia('(min-width: 761px)').matches) first.focus();
}
function viewAuth(name) {
  if (name === 'signup') return authLayout(`
    <div class="auth-head"><h1>Create an account</h1><p>We'll email you a temporary password. You'll pick your own the first time you sign in.</p></div>
    <form data-form="signup" novalidate>
      <label class="field"><span>Full name</span><input name="fullName" autocomplete="name" required maxlength="80"></label>
      <label class="field"><span>Email</span><input name="email" type="email" autocomplete="email" inputmode="email" required></label>
      <div class="form-msg" role="alert"></div>
      <button class="btn btn-primary btn-block btn-lg" type="submit">Create account</button>
    </form>
    <p class="auth-alt">Already have an account? <a href="#/login">Sign in</a></p>`);
  if (name === 'forgot') return authLayout(`
    <div class="auth-head"><h1>Reset password</h1><p>Enter your email and we'll send you a new temporary password.</p></div>
    <form data-form="forgot" novalidate>
      <label class="field"><span>Email</span><input name="email" type="email" autocomplete="email" inputmode="email" required value="${esc(S.prefill)}"></label>
      <div class="form-msg" role="alert"></div>
      <button class="btn btn-primary btn-block btn-lg" type="submit">Send temporary password</button>
    </form>
    <p class="auth-alt"><a href="#/login">Back to sign in</a></p>`);
  authLayout(`
    <div class="auth-head"><h1>Sign in</h1><p>Use the email and password for your NCAT Exams account.</p></div>
    <form data-form="login" novalidate>
      <label class="field"><span>Email</span><input name="email" type="email" autocomplete="email" inputmode="email" required value="${esc(S.prefill)}"></label>
      <div class="field"><span><label for="pw">Password</label><a href="#/forgot" class="link-sm">Forgot password?</a></span>
        <div class="pw"><input id="pw" name="password" type="password" autocomplete="current-password" required><button type="button" class="pw-toggle" data-act="togglePw">Show</button></div></div>
      <div class="form-msg" role="alert"></div>
      <button class="btn btn-primary btn-block btn-lg" type="submit">Sign in</button>
    </form>
    <p class="auth-alt">No account yet? <a href="#/signup">Create one</a></p>`);
}
function authSent(title, msg, email) {
  S.prefill = email;
  $('.auth-card').innerHTML = `<div class="auth-mobile-logo">${logo()}</div><div class="success-ico">${I.mail}</div>
    <div class="auth-head"><h1>${esc(title)}</h1><p>${esc(msg)}</p></div>
    <a class="btn btn-primary btn-block btn-lg" href="#/login">Go to sign in</a>
    <p class="auth-alt">Nothing arrived after a few minutes? <a href="#/forgot">Send it again</a></p>`;
}
async function accountApi(body) {
  const r = await fetch(`${C.supabaseUrl}/functions/v1/afit-account`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', apikey: C.supabaseAnonKey, Authorization: `Bearer ${C.supabaseAnonKey}` },
    body: JSON.stringify(body),
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || `Request failed (${r.status}).`);
  return d;
}
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const forms = {
  async login(f) {
    const email = f.email.value.trim().toLowerCase(), password = f.password.value;
    if (!EMAIL_RE.test(email)) return formMsg(f, 'Enter a valid email address.');
    if (!password) return formMsg(f, 'Enter your password.');
    busy(f, true, 'Signing in…');
    const { data, error } = await sb.auth.signInWithPassword({ email, password });
    if (error) { busy(f, false); return formMsg(f, /invalid/i.test(error.message) ? 'Wrong email or password.' : error.message); }
    try { await setUser(data.user); } catch (e) { busy(f, false); return formMsg(f, `Signed in, but your profile couldn't load: ${e.message}`); }
    S.prefill = '';
    go(S.profile.must_change_password ? 'password' : '', true);
  },
  async signup(f) {
    const fullName = f.fullName.value.trim(), email = f.email.value.trim().toLowerCase();
    if (fullName.length < 2) return formMsg(f, 'Enter your full name.');
    if (!EMAIL_RE.test(email)) return formMsg(f, 'Enter a valid email address.');
    busy(f, true, 'Creating account…');
    try { await accountApi({ action: 'signup', fullName, email }); authSent('Check your email', `We sent a temporary password to ${email}. It can take a minute, and it may land in spam.`, email); }
    catch (e) { busy(f, false); formMsg(f, e.message); }
  },
  async forgot(f) {
    const email = f.email.value.trim().toLowerCase();
    if (!EMAIL_RE.test(email)) return formMsg(f, 'Enter a valid email address.');
    busy(f, true, 'Sending…');
    try { await accountApi({ action: 'reset', email }); authSent('Check your email', `If ${email} has an account, a new temporary password is on its way. Check spam too.`, email); }
    catch (e) { busy(f, false); formMsg(f, e.message); }
  },
  async password(f) {
    const pw = f.password.value, cf = f.confirm.value;
    const r = pwRules(pw);
    if (!r.every(x => x[1])) return formMsg(f, 'Your password needs at least 8 characters, with a letter and a number.');
    if (/^NCAT-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(pw)) return formMsg(f, "Choose a password of your own, not the temporary one.");
    if (pw !== cf) return formMsg(f, "The two passwords don't match.");
    busy(f, true, 'Saving…');
    const { error } = await sb.auth.updateUser({ password: pw });
    if (error) { busy(f, false); return formMsg(f, /different/i.test(error.message) ? 'Choose a password different from your current one.' : error.message); }
    const forced = S.profile.must_change_password;
    if (forced) {
      const u = await sb.from('afit_profiles').update({ must_change_password: false }).eq('id', S.user.id);
      if (u.error) { busy(f, false); return formMsg(f, u.error.message); }
      S.profile.must_change_password = false;
    }
    toast('Password saved.', 'ok');
    go('', true);
  },
};
const pwRules = pw => [['At least 8 characters', pw.length >= 8], ['A letter', /[a-z]/i.test(pw)], ['A number', /\d/.test(pw)]];
function viewPassword() {
  const forced = S.profile.must_change_password;
  const inner = `
    <div class="auth-head"><h1>${forced ? 'Set your password' : 'Change password'}</h1><p>${forced ? `Welcome, ${esc(firstName())}. You signed in with a temporary password, so choose your own before you continue.` : 'Pick a new password for your account.'}</p></div>
    <form data-form="password" novalidate>
      <div class="field"><span><label for="npw">New password</label></span><div class="pw"><input id="npw" name="password" type="password" autocomplete="new-password" required data-live="pw"><button type="button" class="pw-toggle" data-act="togglePw">Show</button></div></div>
      <div class="meter"><i id="meter"></i></div>
      <ul class="rules" id="rules">${pwRules('').map(([t]) => `<li>${t}</li>`).join('')}</ul>
      <label class="field"><span>Confirm new password</span><input name="confirm" type="password" autocomplete="new-password" required></label>
      <div class="form-msg" role="alert"></div>
      <button class="btn btn-primary btn-block btn-lg" type="submit">Save password</button>
    </form>
    <p class="auth-alt">${forced ? `<a href="#" data-act="signout">Sign out</a>` : `<a href="#/">Cancel</a>`}</p>`;
  if (forced) authLayout(inner);
  else { mount(shell('', `<div class="card" style="max-width:480px;margin:0 auto">${inner}</div>`)); }
}

/* ---------- dashboard ---------- */
function subjectStats() {
  const out = {};
  for (const s of S.subjects) out[s.id] = { seen: 0, mastered: 0, missed: 0, tries: 0, right: 0 };
  for (const r of S.stats.values()) {
    const o = out[r.subject]; if (!o || !S.byId.has(r.question_id)) continue;
    o.seen++; o.tries += r.seen; o.right += r.correct;
    if (r.last_correct) o.mastered++; else o.missed++;
  }
  return out;
}
const missedIds = (subjects) => S.bank.filter(q => S.stats.get(q.id)?.last_correct === false && (!subjects || subjects.includes(q.s))).map(q => q.id);
const subjBadge = s => `<span class="subj-badge" style="background:${SUBJECT_COLORS[S.subj[s].i % SUBJECT_COLORS.length]}">${esc(S.subj[s].short)}</span>`;
const subjTag = s => `<span class="tag"><span class="dot" style="background:${SUBJECT_COLORS[S.subj[s].i % SUBJECT_COLORS.length]}"></span>${esc(S.subj[s].name)}</span>`;
const scoreCls = p => (p >= PASS ? 'pass' : 'fail');

function viewDashboard() {
  const A = S.attempts, ss = subjectStats();
  const avg = A.length ? Math.round(A.reduce((t, a) => t + +a.score_pct, 0) / A.length) : null;
  const best = A.length ? Math.round(Math.max(...A.map(a => +a.score_pct))) : null;
  const mastered = Object.values(ss).reduce((t, o) => t + o.mastered, 0);
  const missed = missedIds().length;
  const Q = S.quiz && !S.quiz.finished ? S.quiz : null;
  const last = progress().last, next = !Q && last ? seqBlock({ ...last, subjects: last.subjects.filter(s => S.subj[s]) }) : null;
  const h = new Date().getHours();
  const greet = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';

  mount(shell('', `
  <div class="stack">
    <section class="hero">
      <div><h1>${greet}, ${esc(firstName())}</h1><p>${A.length ? `${A.length} quiz${A.length > 1 ? 'zes' : ''} done so far. Pass mark is ${PASS}%.` : `${S.bank.length} questions ready. Pass mark is ${PASS}%.`}</p></div>
      <div class="actions">
        <a class="btn btn-primary btn-lg" href="#/practice">${I.play} New quiz</a>
        <button class="btn btn-lg" data-act="quick">Quick 20</button>
      </div>
    </section>
    ${Q ? `<div class="card resume"><span class="ico">${I.clock}</span><div class="tx"><b>Unfinished quiz</b><div class="muted" style="font-size:14px">${esc(Q.title)}: ${quizScore(Q).answered} of ${Q.items.length} answered</div></div>
      <button class="btn btn-ghost btn-sm" data-act="discard">Discard</button><a class="btn btn-primary" href="#/quiz">Continue</a></div>` : ''}
    ${next && next.started && next.ids.length ? `<div class="card resume"><span class="ico">${I.play}</span><div class="tx"><b>Next up: questions ${next.from}–${next.to}</b><div class="muted" style="font-size:14px">${esc(subjLabel(last))} · ${next.left} of ${next.total} still to do</div></div><button class="btn btn-primary" data-act="continueLast">Continue</button></div>` : ''}
    <section class="grid g-4">
      <div class="card stat"><div class="k">${I.layers} Quizzes</div><div class="v">${A.length}</div><div class="s">${A.length ? `${A.reduce((t, a) => t + a.answered, 0)} answers given` : 'None yet'}</div></div>
      <div class="card stat"><div class="k">${I.target} Average</div><div class="v">${avg ?? '–'}${avg !== null ? '<small>%</small>' : ''}</div><div class="s">${avg === null ? 'Take a quiz' : avg >= PASS ? 'Above the pass mark' : `${PASS - avg}% below the pass mark`}</div></div>
      <div class="card stat"><div class="k">${I.star} Best</div><div class="v">${best ?? '–'}${best !== null ? '<small>%</small>' : ''}</div><div class="s">${best !== null ? 'Highest score' : '–'}</div></div>
      <div class="card stat"><div class="k">${I.check} Got right</div><div class="v">${mastered}<small>/${S.bank.length}</small></div><div class="s">Correct the last time you saw them</div></div>
    </section>
    ${missed ? `<div class="card resume"><span class="ico" style="background:var(--bad)">${I.x}</span><div class="tx"><b>${missed} question${missed > 1 ? 's' : ''} to go over</b><div class="muted" style="font-size:14px">The ones you got wrong last time.</div></div><button class="btn btn-primary" data-act="reviewMissed">Practise these</button></div>` : ''}
    <section>
      <div class="page-head" style="margin-bottom:14px"><div><h2 style="font-size:20px">Subjects</h2></div><a href="#/bank" class="link-sm">Browse all questions</a></div>
      <div class="grid g-subjects">${S.subjects.map(s => {
        const o = ss[s.id];
        return `<div class="card subj"><div class="subj-top">${subjBadge(s.id)}<div><h4>${esc(s.name)}</h4><span class="sub">${s.count} questions</span></div></div>
          <div class="bar" title="${o.mastered} right, ${o.missed} wrong"><i class="b-ok" style="width:${(o.mastered / s.count) * 100}%"></i><i class="b-bad" style="width:${(o.missed / s.count) * 100}%"></i></div>
          <div class="subj-meta"><span>${o.seen ? `${o.seen}/${s.count} done${o.tries ? ` · ${pct(o.right, o.tries)}% right` : ''}` : 'Not started'}</span><button class="btn btn-sm" data-act="practiceSubject" data-s="${s.id}">Practise</button></div></div>`;
      }).join('')}</div>
    </section>
    <section class="grid g-2">
      <div class="card"><div class="card-head"><h3>Recent quizzes</h3>${A.length ? '<a href="#/history" class="link-sm">See all</a>' : ''}</div>
        ${A.length ? `<div class="list">${A.slice(0, 5).map(attemptRow).join('')}</div>` : `<div class="empty">${I.hist}Your finished quizzes will show up here.</div>`}</div>
      <div class="card"><div class="card-head"><h3>Top scores, last 30 days</h3></div><div id="board"><div class="empty"><div class="spinner" style="margin:0 auto"></div></div></div></div>
    </section>
  </div>`));
  loadBoard();
}
function attemptRow(a) {
  const p = Math.round(+a.score_pct);
  return `<a class="row" href="#/attempt/${encodeURIComponent(a.client_id)}"><div class="grow"><div class="t">${esc(a.title)}</div><div class="m">${fmtDate(a.created_at)} · ${a.correct}/${a.total} · ${fmtDur(a.duration_sec)}${a.mode === 'timed' ? ' · timed' : ''}</div></div><span class="score-pill ${scoreCls(p)}">${p}%</span></a>`;
}
async function loadBoard() {
  const { data, error } = await sb.rpc('afit_leaderboard');
  const el = $('#board'); if (!el) return;
  if (error) { el.innerHTML = `<div class="empty">Couldn't load scores.</div>`; return; }
  el.innerHTML = data.length
    ? `<div class="list">${data.map((r, i) => `<div class="row ${r.is_me ? 'me' : ''}"><span class="rank">${i + 1}</span><div class="grow"><div class="t">${esc(r.name)}${r.is_me ? ' (you)' : ''}</div><div class="m">${r.answered} answered</div></div><span class="score-pill ${scoreCls(+r.accuracy)}">${Math.round(+r.accuracy)}%</span></div>`).join('')}</div>`
    : `<div class="empty">${I.star}Nobody's listed yet. Answer 20 questions to get on the board.</div>`;
}

/* ---------- practice setup ---------- */
function defaultSetup() { return { subjects: S.subjects.map(s => s.id), count: 20, source: 'all', order: 'source', shuffle: true, mode: 'practice' }; }
function setupPool(st) {
  return S.bank.filter(q => st.subjects.includes(q.s) && sourceOk(st, q));
}
function viewPractice() {
  if (!S.setup) S.setup = { ...defaultSetup(), ...store.get('afit:setup', {}) };
  S.setup.subjects = S.setup.subjects.filter(s => S.subj[s]);
  if (!S.setup.subjects.length) S.setup.subjects = S.subjects.map(s => s.id);
  renderPractice();
}
function renderPractice() {
  const st = S.setup, pool = setupPool(st), seq = st.order === 'source', blk = seq ? seqBlock(st) : null;
  const n = seq ? blk.ids.length : st.count === 'all' ? pool.length : Math.min(st.count, pool.length);
  const allOn = st.subjects.length === S.subjects.length;
  const seg = (key, opts) => `<div class="seg" role="group">${opts.map(([v, t]) => `<button type="button" data-act="setup" data-k="${key}" data-v="${v}" aria-pressed="${String(st[key]) === String(v)}">${t}</button>`).join('')}</div>`;
  const newCount = S.bank.filter(q => st.subjects.includes(q.s) && !S.stats.has(q.id)).length;
  const missCount = S.bank.filter(q => st.subjects.includes(q.s) && S.stats.get(q.id)?.last_correct === false).length;
  mount(shell('practice', `
  <div class="page-head"><div><div class="eyebrow">New quiz</div><h1>Set up your quiz</h1><p>Pick the subjects and how many questions you want.</p></div></div>
  <div class="setup-layout">
    <div class="card">
      <div class="setup-sec"><div class="card-head" style="margin-bottom:4px"><h4>Subjects</h4><button class="btn btn-ghost btn-sm" data-act="allSubjects">${allOn ? 'Clear' : 'Select all'}</button></div><p>Mix as many as you like.</p>
        <div class="chips">${S.subjects.map(s => `<button type="button" class="chip" data-act="toggleSubject" data-s="${s.id}" aria-pressed="${st.subjects.includes(s.id)}"><span class="dot" style="background:${SUBJECT_COLORS[S.subj[s.id].i % SUBJECT_COLORS.length]}"></span>${esc(s.name)} <span class="n">${s.count}</span></button>`).join('')}</div></div>
      <div class="setup-sec"><h4>Which questions</h4><p>Go through everything, only ones you haven't seen, or the ones you got wrong.</p>
        ${seg('source', [['all', 'All'], ['new', `Not seen yet (${newCount})`], ['missed', `Got wrong (${missCount})`]])}</div>
      <div class="setup-sec"><h4>How many</h4><p>${seq ? (blk.started ? `${blk.left} of ${blk.total} still to do. You carry on from where you stopped.` : `${blk.total} questions, starting from question 1.`) : `${pool.length} available. Ones you haven't answered come first.`}</p>
        ${seg('count', [[10, '10'], [20, '20'], [50, '50'], [100, '100'], ['all', 'All']])}</div>
      <div class="setup-sec"><h4>Mode</h4><p>Either way you see the right answer as soon as you pick one.</p>
        <div class="mode-cards">
          <button type="button" class="mode-card" data-act="setup" data-k="mode" data-v="practice" aria-pressed="${st.mode === 'practice'}">${I.book}<div><b>Practice</b><span>No clock. Take your time.</span></div></button>
          <button type="button" class="mode-card" data-act="setup" data-k="mode" data-v="timed" aria-pressed="${st.mode === 'timed'}">${I.clock}<div><b>Timed</b><span>1 minute per question. Ends when time runs out.</span></div></button>
        </div></div>
      <div class="setup-sec"><h4 style="margin-bottom:12px">Order</h4>${seg('order', [['random', 'Random'], ['source', 'In order, carry on where I stopped']])}
        <label class="switch" style="margin-top:16px"><span><b style="font-size:14.5px">Shuffle A/B/C</b><br><span class="muted" style="font-size:13px">Stops you remembering the letter instead of the answer.</span></span><input type="checkbox" data-act="shuffleOpts" ${st.shuffle ? 'checked' : ''}></label></div>
    </div>
    <aside class="card summary">
      <div class="eyebrow">Summary</div>
      <div class="big">${n}</div><div class="muted">question${n === 1 ? '' : 's'}</div>
      ${seq && n ? `<div class="range">Questions ${blk.from}–${blk.to} of ${blk.total}</div>` : ''}
      ${seq && !n && blk.total ? `<p class="range">You've done all ${blk.total} questions in these subjects.</p>` : ''}
      <dl><dt>Subjects</dt><dd>${allOn ? 'All' : st.subjects.length}</dd><dt>Mode</dt><dd>${st.mode === 'timed' ? `Timed, ${fmtDur(n * 60)}` : 'Practice'}</dd><dt>Order</dt><dd>${st.order === 'random' ? 'Random' : 'In order'}</dd><dt>Pass mark</dt><dd>${PASS}%</dd></dl>
      ${seq && !n && blk.total ? `<button class="btn btn-primary btn-lg btn-block" data-act="restartSetup">Go round again from question 1</button>`
        : `<button class="btn btn-primary btn-lg btn-block" data-act="startSetup" ${n ? '' : 'disabled'}>${seq && blk.started ? `Continue from question ${blk.from}` : 'Start quiz'}</button>`}
    </aside>
  </div>`));
}

/* ---------- quiz view ---------- */
function viewQuiz() {
  if (!S.quiz) return go('', true);
  if (S.quiz.finished) return go('results', true);
  renderQuiz();
  startTimer();
}
function renderQuiz() {
  const Q = S.quiz, it = Q.items[Q.idx], q = S.byId.get(it.q), chosen = Q.ans[Q.idx], done = chosen !== null;
  const sc = quizScore(Q), last = Q.idx === Q.items.length - 1, flagged = Q.flags.includes(Q.idx);
  const left = Q.limit ? Q.limit - Q.elapsed : null;
  const okNow = done && q.a.includes(chosen);
  const correctPos = it.o.findIndex(o => q.a.includes(o));
  const opts = it.o.map((orig, pos) => {
    let cls = '', res = '';
    if (done) {
      if (q.a.includes(orig)) { cls = 'is-correct'; res = I.check; }
      else if (orig === chosen) { cls = 'is-wrong'; res = I.x; }
      else cls = 'is-dim';
    }
    return `<button class="opt ${cls}" data-act="choose" data-pos="${pos}" ${done ? 'disabled' : ''}><span class="ltr">${L(pos)}</span><span class="txt">${esc(q.o[orig])}</span>${res ? `<span class="res">${res}</span>` : ''}</button>`;
  }).join('');
  const fb = !done ? '' : okNow
    ? `<div class="fb ok">${I.check}<div class="fb-t"><b class="h">Correct</b>${esc(L(it.o.indexOf(chosen)))} is the right answer.</div></div>`
    : `<div class="fb bad">${I.x}<div class="fb-t"><b class="h">Wrong</b>You picked ${L(it.o.indexOf(chosen))}. The answer is <b>${L(correctPos)}</b>: ${esc(q.o[it.o[correctPos]])}</div></div>`;
  const note = done && q.x ? `<div class="note"><b>Note:</b> ${esc(q.x)}</div>` : '';
  const cells = Q.items.map((t, i) => {
    const c = Q.ans[i]; const st = c === null ? '' : S.byId.get(t.q).a.includes(c) ? 'c-ok' : 'c-bad';
    return `<button class="nav-cell ${st} ${i === Q.idx ? 'cur' : ''} ${Q.flags.includes(i) ? 'flag' : ''}" data-act="jump" data-i="${i}" aria-label="Question ${i + 1}">${i + 1}</button>`;
  }).join('');

  mount(`
  <header class="quiz-top"><div class="quiz-top-in">
    <button class="btn btn-ghost icon-btn" data-act="exitQuiz" aria-label="Leave quiz">${I.x}</button>
    <div class="quiz-title"><b>${esc(Q.title)}</b><span>${Q.mode === 'timed' ? 'Timed' : 'Practice'} · pass mark ${PASS}%</span></div>
    <span class="pill" title="Answered">${sc.answered}/${sc.total}</span>
    <span class="pill ${left !== null && left <= 60 ? 'warn' : ''}" id="qtimer">${I.clock}<span>${fmtTime(left ?? Q.elapsed)}</span></span>
  </div><div class="progress"><i style="width:${(sc.answered / Q.items.length) * 100}%"></i></div></header>
  <main class="quiz-main">
    <div class="q-meta"><b style="color:var(--ink)">Question ${Q.idx + 1} of ${Q.items.length}</b>${subjTag(q.s)}<span>No. ${q.n} in the paper</span>${flagged ? `<span class="tag" style="color:var(--warn)">Flagged</span>` : ''}</div>
    <h2 class="q-text">${esc(q.q)}</h2>
    <div class="opts">${opts}</div>
    <div aria-live="polite">${fb}${note}</div>
    <p class="kbd-hint">Keys: <kbd>A</kbd>–<kbd>${L(it.o.length - 1)}</kbd> to answer, <kbd>←</kbd> <kbd>→</kbd> to move, <kbd>F</kbd> to flag</p>
    <details class="navgrid-wrap" ${store.get('afit:navOpen', false) ? 'open' : ''}>
      <summary data-act="navToggle">${I.chev} All questions (${sc.answered}/${Q.items.length} answered${Q.flags.length ? `, ${Q.flags.length} flagged` : ''})</summary>
      <div class="navgrid">${cells}</div>
      <div class="legend"><span><i style="background:var(--ok-soft);border:1px solid var(--ok-line)"></i>Correct</span><span><i style="background:var(--bad-soft);border:1px solid var(--bad-line)"></i>Wrong</span><span><i style="background:var(--surface);border:1px solid var(--line-2)"></i>Not answered</span><span><i style="background:var(--warn)"></i>Flagged</span></div>
    </details>
  </main>
  <footer class="quiz-foot"><div class="quiz-foot-in">
    <button class="btn" data-act="prev" ${Q.idx === 0 ? 'disabled' : ''} aria-label="Previous">${I.left}<span class="hide-sm">Previous</span></button>
    <button class="btn ${flagged ? 'flag-on' : ''}" data-act="flag" aria-pressed="${flagged}">${I.flag}<span class="hide-sm">${flagged ? 'Flagged' : 'Flag'}</span></button>
    <span class="sp"></span>
    <button class="btn btn-ghost hide-sm" data-act="finish">Finish</button>
    ${last ? `<button class="btn btn-primary" data-act="finish">Finish quiz</button>` : `<button class="btn btn-primary" data-act="next">${done ? 'Next' : 'Skip'}${I.right}</button>`}
  </div></footer>`);
}
function choose(pos) {
  const Q = S.quiz; if (!Q || Q.finished) return;
  if (Q.ans[Q.idx] !== null) return;
  const it = Q.items[Q.idx], orig = it.o[pos];
  if (orig === undefined) return;
  Q.ans[Q.idx] = orig;
  saveQuiz();
  if (!S.byId.get(it.q).a.includes(orig)) navigator.vibrate?.(40);
  renderQuiz();
  if (matchMedia('(max-width: 760px)').matches) $('.fb')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
function moveTo(i) {
  const Q = S.quiz; if (!Q) return;
  Q.idx = Math.max(0, Math.min(Q.items.length - 1, i));
  saveQuiz(); renderQuiz(); window.scrollTo(0, 0);
}

/* ---------- results ---------- */
function viewResults() {
  const Q = S.quiz;
  if (!Q || !Q.finished) return go('', true);
  renderResults(Q, { live: true });
}
async function viewAttempt(clientId) {
  let a = S.attempts.find(x => x.client_id === clientId);
  if (!a) return go('history', true);
  if (!a.answers) {
    mount(shell('history', `<div class="empty"><div class="spinner" style="margin:40px auto"></div></div>`));
    const { data, error } = await sb.from('afit_attempts').select('answers').eq('client_id', clientId).maybeSingle();
    if (error || !data) { toast("Couldn't open that quiz.", 'err'); return go('history', true); }
    a.answers = data.answers;
  }
  const answers = a.answers.filter(x => S.byId.has(x.q));
  const Q = { id: a.client_id, title: a.title, mode: a.mode, subjects: a.subjects, items: answers.map(x => ({ q: x.q, o: x.o })), ans: answers.map(x => x.c), elapsed: a.duration_sec, finishedAt: a.created_at, finished: true };
  renderResults(Q, { live: false });
}
function renderResults(Q, { live }) {
  const sc = quizScore(Q), p = pct(sc.correct, sc.total), pass = p >= PASS;
  const R = 74, CIRC = 2 * Math.PI * R;
  const bySubj = {};
  Q.items.forEach((it, i) => { const q = S.byId.get(it.q); const o = bySubj[q.s] ||= { t: 0, c: 0 }; o.t++; if (Q.ans[i] !== null && q.a.includes(Q.ans[i])) o.c++; });
  const wrongIds = Q.items.filter((it, i) => Q.ans[i] === null || !S.byId.get(it.q).a.includes(Q.ans[i])).map(it => it.q);
  const f = S.reviewFilter;
  const reviewItems = Q.items.map((it, i) => ({ it, i, q: S.byId.get(it.q), c: Q.ans[i] })).filter(({ q, c }) =>
    f === 'all' || (f === 'wrong' && (c === null || !q.a.includes(c))) || (f === 'right' && c !== null && q.a.includes(c)));
  const counts = { all: sc.total, wrong: sc.wrong + sc.skipped, right: sc.correct };
  const nb = live && Q.seq ? seqBlock(Q.seq) : null;

  mount(shell(live ? '' : 'history', `
  <div class="stack">
    <div class="card"><div class="result-hero">
      <div class="ring"><svg viewBox="0 0 168 168"><circle class="trk" cx="84" cy="84" r="${R}"/><circle class="val" id="ringval" cx="84" cy="84" r="${R}" stroke="${pass ? 'var(--ok)' : 'var(--bad)'}" stroke-dasharray="${CIRC}" stroke-dashoffset="${CIRC}"/></svg>
        <div class="lbl"><b>${p}%</b><span>${sc.correct} of ${sc.total}</span></div></div>
      <div>
        <span class="verdict ${pass ? 'pass' : 'fail'}">${pass ? I.check : I.x}${pass ? 'Pass' : 'Below pass mark'}</span>
        <h1>${pass ? (p >= 90 ? 'Excellent work' : 'Well done') : p >= PASS - 15 ? 'Nearly there' : 'Keep practising'}</h1>
        <p class="muted" style="margin:6px 0 0">${esc(Q.title)} · ${fmtDate(Q.finishedAt)}</p>
        <div class="metrics">
          <div class="metric"><b style="color:var(--ok)">${sc.correct}</b><span>Correct</span></div>
          <div class="metric"><b style="color:var(--bad)">${sc.wrong}</b><span>Wrong</span></div>
          <div class="metric"><b style="color:var(--warn)">${sc.skipped}</b><span>Not answered</span></div>
          <div class="metric"><b>${fmtTime(Q.elapsed)}</b><span>Time taken</span></div>
        </div>
        ${live ? syncBadge() : ''}
      </div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:20px">
      ${nb ? (nb.ids.length ? `<button class="btn btn-primary btn-lg" data-act="continueSeq">Continue: questions ${nb.from}–${nb.to}${I.right}</button>` : `<button class="btn btn-primary btn-lg" data-act="restartSeq">All ${nb.total} done. Go round again</button>`) : ''}
      ${wrongIds.length ? `<button class="btn ${nb ? '' : 'btn-primary'}" data-act="retryWrong" data-ids="${wrongIds.join(',')}">Retry the ${wrongIds.length} I missed</button>` : ''}
      <button class="btn" data-act="retryAll">Same questions again</button>
      <a class="btn" href="#/practice">New quiz</a>
      <a class="btn btn-ghost" href="#/">Home</a>
    </div></div>
    ${Object.keys(bySubj).length > 1 ? `<div class="card breakdown"><h3 style="margin-bottom:8px">By subject</h3><div class="list">${Object.entries(bySubj).map(([s, o]) => {
      const sp = pct(o.c, o.t);
      return `<div class="row"><span class="lbl">${esc(S.subj[s].name)}</span><div class="bar"><i class="${sp >= PASS ? 'b-ok' : 'b-bad'}" style="width:${sp}%"></i></div><span class="val">${o.c}/${o.t} · ${sp}%</span></div>`;
    }).join('')}</div></div>` : ''}
    <div class="card">
      <div class="card-head" style="flex-wrap:wrap"><h3>Go over your answers</h3>
        <div class="seg">${[['wrong', 'Wrong'], ['right', 'Correct'], ['all', 'All']].map(([v, t]) => `<button data-act="rvFilter" data-v="${v}" aria-pressed="${f === v}">${t} (${counts[v]})</button>`).join('')}</div></div>
      ${reviewItems.length ? reviewItems.map(({ it, i, q, c }) => {
        const ok = c !== null && q.a.includes(c);
        return `<div class="rv"><div class="bq-head"><b style="color:var(--ink)">${i + 1}.</b>${subjTag(q.s)}<span class="rv-status ${c === null ? 'skip' : ok ? 'ok' : 'bad'}">${c === null ? 'Not answered' : ok ? 'Correct' : 'Wrong'}</span></div>
          <div class="rv-q">${esc(q.q)}</div>
          <div class="rv-opts">${it.o.map((orig, pos) => {
            const isAns = q.a.includes(orig), isMine = orig === c;
            const cls = isAns ? 'ok' : isMine ? 'bad' : '';
            return `<div class="rv-opt ${cls}"><span class="ltr">${L(pos)}</span><span class="tx">${esc(q.o[orig])}</span>${isAns ? `<em>${isMine ? 'Your answer · correct' : 'Correct answer'}</em>` : isMine ? '<em>Your answer</em>' : ''}</div>`;
          }).join('')}</div>${q.x ? `<div class="note"><b>Note:</b> ${esc(q.x)}</div>` : ''}</div>`;
      }).join('') : `<div class="empty">${f === 'wrong' ? 'Nothing wrong here. Every question was correct.' : 'Nothing to show.'}</div>`}
    </div>
  </div>`));
  S.resultQ = Q;
  requestAnimationFrame(() => requestAnimationFrame(() => { const r = $('#ringval'); if (r) r.style.strokeDashoffset = CIRC * (1 - p / 100); }));
}

/* ---------- history ---------- */
function viewHistory() {
  const A = S.attempts;
  const avg = A.length ? Math.round(A.reduce((t, a) => t + +a.score_pct, 0) / A.length) : 0;
  const passed = A.filter(a => +a.score_pct >= PASS).length;
  mount(shell('history', `
  <div class="page-head"><div><div class="eyebrow">History</div><h1>Your quizzes</h1><p>${A.length ? `${A.length} done · average ${avg}% · ${passed} passed` : 'Nothing here yet.'}</p></div><a class="btn btn-primary" href="#/practice">${I.play} New quiz</a></div>
  <div class="card">${A.length ? `<div class="list">${A.map(attemptRow).join('')}</div>` : `<div class="empty">${I.hist}Finish a quiz and it will be listed here.</div>`}</div>`));
}

/* ---------- question bank ---------- */
function bankMatches() {
  const v = S.bankView, terms = v.q.toLowerCase().split(/\s+/).filter(Boolean);
  return S.bank.filter(q => (v.s === 'all' || q.s === v.s) && (!terms.length || terms.every(t => (q.q + ' ' + q.o.join(' ')).toLowerCase().includes(t))));
}
function hl(text) {
  const terms = S.bankView.q.split(/\s+/).filter(t => t.length > 1).map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const e = esc(text);
  return terms.length ? e.replace(new RegExp(`(${terms.map(esc).join('|')})`, 'gi'), '<mark>$1</mark>') : e;
}
function bankList() {
  const m = bankMatches(), v = S.bankView;
  if (!m.length) return `<div class="card empty">${I.search}No questions match “${esc(v.q)}”.</div>`;
  return m.slice(0, v.limit).map(q => {
    const st = S.stats.get(q.id);
    return `<div class="card bq"><div class="bq-head">${subjTag(q.s)}<span>No. ${q.n}</span>${st ? `<span class="rv-status ${st.last_correct ? 'ok' : 'bad'}">${st.last_correct ? 'You got this right' : 'You got this wrong'}</span>` : ''}</div>
      <div class="rv-q">${hl(q.q)}</div>
      <div class="rv-opts">${q.o.map((o, i) => `<div class="rv-opt ${v.show && q.a.includes(i) ? 'ok' : ''}"><span class="ltr">${L(i)}</span><span class="tx">${hl(o)}</span>${v.show && q.a.includes(i) ? '<em>Answer</em>' : ''}</div>`).join('')}</div>
      ${v.show && q.x ? `<div class="note"><b>Note:</b> ${esc(q.x)}</div>` : ''}</div>`;
  }).join('') + (m.length > v.limit ? `<div style="text-align:center;margin-top:16px"><button class="btn" data-act="more">Show more (${m.length - v.limit} left)</button></div>` : '');
}
function viewBank() {
  const v = S.bankView;
  mount(shell('bank', `
  <div class="page-head"><div><div class="eyebrow">Questions</div><h1>All questions</h1><p>Search or read through every question with its answer.</p></div></div>
  <div class="toolbar">
    <div class="search">${I.search}<input type="search" id="bankq" placeholder="Search, e.g. rivet, QFE, circadian" value="${esc(v.q)}" aria-label="Search questions"></div>
    <select class="sel" id="banks" aria-label="Subject"><option value="all">All subjects</option>${S.subjects.map(s => `<option value="${s.id}" ${v.s === s.id ? 'selected' : ''}>${esc(s.name)}</option>`).join('')}</select>
    <label class="switch" style="gap:10px"><span style="font-weight:600;font-size:14px">Show answers</span><input type="checkbox" id="bankshow" ${v.show ? 'checked' : ''}></label>
  </div>
  <div class="toolbar" style="justify-content:space-between"><span class="muted" id="bankcount" style="font-size:14px"></span><button class="btn btn-sm" data-act="practiceBank">${I.play} Quiz me on these</button></div>
  <div id="banklist"></div>`));
  refreshBank();
}
function refreshBank() {
  const n = bankMatches().length;
  $('#bankcount').textContent = `${n} question${n === 1 ? '' : 's'}`;
  $('#banklist').innerHTML = bankList();
}

/* ---------- actions ---------- */
const actions = {
  togglePw(el) { const i = el.previousElementSibling; const show = i.type === 'password'; i.type = show ? 'text' : 'password'; el.textContent = show ? 'Hide' : 'Show'; },
  menu(el, e) { e.stopPropagation(); $('#menu').classList.toggle('open'); },
  goPassword() { go('password'); },
  theme() {
    const order = ['auto', 'light', 'dark'], t = order[(order.indexOf(store.get('afit:theme', 'auto')) + 1) % 3];
    store.set('afit:theme', t); applyTheme(t); route();
  },
  async signout(el, e) {
    e.preventDefault();
    stopTimer();
    await sb.auth.signOut();
    await setUser(null);
    go('login', true);
  },
  quick() {
    startQuiz({ title: 'Quick 20 · all subjects', mode: 'practice', ids: shuffle(S.bank.map(q => q.id)).slice(0, 20) });
  },
  async discard() {
    if (!await dialog({ title: 'Discard this quiz?', body: 'Your answers in this quiz will be lost.', ok: 'Discard', danger: true })) return;
    S.quiz = null; saveQuiz(); route();
  },
  reviewMissed() {
    const ids = shuffle(missedIds());
    startQuiz({ title: `Questions I got wrong (${ids.length})`, mode: 'review', ids });
  },
  practiceSubject(el) {
    S.setup = { ...defaultSetup(), ...store.get('afit:setup', {}), subjects: [el.dataset.s], source: 'all' };
    go('practice');
  },
  toggleSubject(el) {
    const s = el.dataset.s, st = S.setup;
    st.subjects = st.subjects.includes(s) ? st.subjects.filter(x => x !== s) : [...st.subjects, s];
    store.set('afit:setup', st); renderPractice();
  },
  allSubjects() {
    const st = S.setup; st.subjects = st.subjects.length === S.subjects.length ? [] : S.subjects.map(s => s.id);
    store.set('afit:setup', st); renderPractice();
  },
  setup(el) {
    const k = el.dataset.k, v = el.dataset.v;
    S.setup[k] = k === 'count' && v !== 'all' ? +v : v;
    store.set('afit:setup', S.setup); renderPractice();
  },
  shuffleOpts(el) { S.setup.shuffle = el.checked; store.set('afit:setup', S.setup); },
  async startSetup() {
    const st = S.setup;
    if (S.quiz && !S.quiz.finished && !await dialog({ title: 'Start a new quiz?', body: 'You have an unfinished quiz. Starting a new one will discard it.', ok: 'Start new quiz' })) return;
    if (st.order === 'source') return startSeq(st);
    const pool = setupPool(st);
    let ids = [...shuffle(pool.filter(q => !S.stats.has(q.id))), ...shuffle(pool.filter(q => S.stats.has(q.id)))].map(q => q.id);
    if (st.count !== 'all') ids = ids.slice(0, st.count);
    startQuiz({ title: `${subjLabel(st)} · ${ids.length} questions`, mode: st.mode, ids, shuffleOpts: st.shuffle, subjects: st.subjects });
  },
  restartSetup() { resetCursor(S.setup.subjects); startSeq(S.setup); },
  continueSeq() { startSeq(S.resultQ.seq); },
  continueLast() { startSeq(progress().last); },
  restartSeq() { resetCursor(S.resultQ.seq.subjects); startSeq(S.resultQ.seq); },
  choose(el) { choose(+el.dataset.pos); },
  next() { moveTo(S.quiz.idx + 1); },
  prev() { moveTo(S.quiz.idx - 1); },
  jump(el) { moveTo(+el.dataset.i); },
  flag() {
    const Q = S.quiz, i = Q.idx;
    Q.flags = Q.flags.includes(i) ? Q.flags.filter(x => x !== i) : [...Q.flags, i];
    saveQuiz(); renderQuiz();
  },
  navToggle() { setTimeout(() => store.set('afit:navOpen', $('.navgrid-wrap')?.open), 0); },
  finish() { finishQuiz(false); },
  async exitQuiz() {
    const ok = await dialog({ title: 'Leave this quiz?', body: 'Your progress is saved. You can carry on from the home page.', ok: 'Leave', cancel: 'Stay' });
    if (ok) { saveQuiz(); go(''); }
  },
  rvFilter(el) { S.reviewFilter = el.dataset.v; const y = window.scrollY; renderResults(S.resultQ, { live: S.resultQ === S.quiz }); window.scrollTo(0, y); },
  retryWrong(el) {
    const ids = el.dataset.ids.split(',').filter(id => S.byId.has(id));
    startQuiz({ title: `Retry: ${S.resultQ.title.replace(/^Retry: /, '')}`, mode: 'review', ids: shuffle(ids) });
  },
  retryAll() {
    const Q = S.resultQ;
    startQuiz({ title: Q.title, mode: Q.mode === 'review' ? 'practice' : Q.mode, ids: Q.items.map(it => it.q), subjects: Q.subjects });
  },
  more() { S.bankView.limit += 25; $('#banklist').innerHTML = bankList(); },
  practiceBank() {
    const ids = bankMatches().map(q => q.id);
    const picked = shuffle(ids).slice(0, 50);
    startQuiz({ title: S.bankView.q ? `Search: “${S.bankView.q}” · ${picked.length} questions` : `${S.bankView.s === 'all' ? 'All subjects' : S.subj[S.bankView.s].name} · ${picked.length} questions`, mode: 'practice', ids: picked });
  },
};

document.addEventListener('click', e => {
  const el = e.target.closest('[data-act]');
  if (!el) { if (!e.target.closest('.menu')) closeMenu(); return; }
  const fn = actions[el.dataset.act];
  if (fn) fn(el, e);
});
document.addEventListener('change', e => {
  const el = e.target;
  if (el.matches('input[data-act="shuffleOpts"]')) return; // handled by click
  if (el.id === 'banks') { S.bankView.s = el.value; S.bankView.limit = 25; refreshBank(); }
  if (el.id === 'bankshow') { S.bankView.show = el.checked; refreshBank(); }
});
let searchT;
document.addEventListener('input', e => {
  const el = e.target;
  if (el.id === 'bankq') { clearTimeout(searchT); searchT = setTimeout(() => { S.bankView.q = el.value.trim(); S.bankView.limit = 25; refreshBank(); }, 160); }
  if (el.dataset.live === 'pw') {
    const r = pwRules(el.value); $$('#rules li').forEach((li, i) => li.classList.toggle('met', r[i][1]));
    const score = r.filter(x => x[1]).length + (el.value.length >= 12 ? 1 : 0) + (/[^a-z0-9]/i.test(el.value) ? 1 : 0);
    const m = $('#meter'); m.style.width = `${Math.min(100, score * 20)}%`; m.style.background = score >= 4 ? 'var(--ok)' : score >= 3 ? 'var(--warn)' : 'var(--bad)';
  }
});
document.addEventListener('submit', e => {
  const f = e.target.closest('form[data-form]');
  if (!f) return;
  e.preventDefault();
  const fn = forms[f.dataset.form];
  if (fn) fn(f).catch(err => { busy(f, false); formMsg(f, err.message || 'Something went wrong.'); });
});
document.addEventListener('keydown', e => {
  if (!location.hash.startsWith('#/quiz') || !S.quiz || S.quiz.finished || $('#modal').open) return;
  if (e.target.matches('input, textarea, select') || e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key.toLowerCase(), it = S.quiz.items[S.quiz.idx];
  const pos = 'abcdef'.indexOf(k) >= 0 ? 'abcdef'.indexOf(k) : '123456'.indexOf(k);
  if (pos >= 0 && pos < it.o.length) { e.preventDefault(); choose(pos); }
  else if (e.key === 'ArrowRight' || (e.key === 'Enter' && S.quiz.ans[S.quiz.idx] !== null && !e.target.matches('button'))) { e.preventDefault(); S.quiz.idx < S.quiz.items.length - 1 ? moveTo(S.quiz.idx + 1) : finishQuiz(false); }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); moveTo(S.quiz.idx - 1); }
  else if (k === 'f') { e.preventDefault(); actions.flag(); }
});

/* ---------- boot ---------- */
async function boot() {
  applyTheme(store.get('afit:theme', 'auto'));
  try {
    const [bank, sess] = await Promise.all([
      fetch('data/questions.json', { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error('Could not load questions.'); return r.json(); }),
      sb.auth.getSession(),
    ]);
    S.bank = bank.questions;
    S.subjects = bank.subjects;
    const SHORT = { law: 'LAW', aero1: 'AE1', aero2: 'AE2', sheet: 'SM', hardware: 'HW', drawing: 'DRG', hf1: 'HF1', hf2: 'HF2' };
    S.subjects.forEach((s, i) => { S.subj[s.id] = { ...s, i, short: SHORT[s.id] || s.name.slice(0, 3).toUpperCase() }; });
    const k = {};
    S.bank.forEach(q => { S.byId.set(q.id, q); S.pos.set(q.id, k[q.s] = (k[q.s] ?? -1) + 1); });
    const user = sess.data.session?.user;
    if (user) { try { await setUser(user); } catch (e) { console.error(e); await sb.auth.signOut(); toast('Please sign in again.', 'err'); } }
  } catch (e) {
    mount(`<div class="boot"><div class="boot-logo">${I.plane}</div><p style="max-width:320px;text-align:center">${esc(e.message || 'Something went wrong while loading.')}<br><br><button class="btn btn-primary" onclick="location.reload()">Try again</button></p></div>`);
    return;
  }
  sb.auth.onAuthStateChange((event) => {
    if (event === 'SIGNED_OUT' && S.user) setUser(null).then(() => go('login', true));
  });
  window.addEventListener('hashchange', route);
  window.addEventListener('online', flushPending);
  document.addEventListener('visibilitychange', () => { if (document.hidden && S.quiz) saveQuiz(); });
  route();
}
boot();
})();
