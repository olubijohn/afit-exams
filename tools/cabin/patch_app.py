"""Departments in the NCAT app: pick one after signing in (asked again in every new browser session); only that
department's papers, questions, quizzes and progress show. Cabin Crew also gets Study cards.
  python -I patch_app.py ../../assets/app.js"""
import sys
p = sys.argv[1]; s = open(p, encoding='utf-8').read()


def rep(old, new, count=1):
    global s
    n = s.count(old); assert n == count, f'{n}x for: {old[:90]}'
    s = s.replace(old, new)


# state
rep("  setup: null, bankView: { q: '', s: 'all', show: true, limit: 25 }, reviewFilter: 'wrong', prefill: '',\n};",
    "  setup: null, bankView: { q: '', s: 'all', show: true, limit: 25 }, reviewFilter: 'wrong', prefill: '',\n  dept: null, departments: [], cards: [], everyPaper: [], everySubject: [], everyQ: [],\n};")

# setPaper: fall back to the department's first paper; remember the paper per department
rep("  if (!paperOf(id)) id = 'general';", "  if (!paperOf(id)) id = paperOf('general') ? 'general' : (S.papers[0]?.id || 'general');")
rep("  store.set('afit:paper', id);", "  store.set('afit:paper', id); if (S.dept) store.set('afit:paper:' + S.dept, id);")

# setDept + session storage of the choice
rep("// switch paper: only its subjects, questions, progress and quizzes show\nfunction setPaper(id, push) {",
    """// department (Aircraft Maintenance, Cabin Crew, ...): only its papers, questions and progress show.
// Chosen after signing in; asked again in every new browser session.
const deptName = () => S.departments.find(d => d.id === S.dept)?.name || '';
function sessDept(v) { try { if (v === undefined) return sessionStorage.getItem('afit:dept'); v ? sessionStorage.setItem('afit:dept', v) : sessionStorage.removeItem('afit:dept'); } catch { return null; } }
function setDept(d, want) {
  S.dept = S.departments.some(x => x.id === d) ? d : null; sessDept(S.dept);
  const show = S.dept || 'ame';
  const pids = new Set(S.everyPaper.filter(p => (p.dept || 'ame') === show).map(p => p.id));
  S.papers = S.everyPaper.filter(p => pids.has(p.id));
  S.allSubjects = S.everySubject.filter(x => pids.has(x.paper));
  const sids = new Set(S.allSubjects.map(x => x.id));
  S.full = S.everyQ.filter(q => sids.has(q.s));
  const pick = [want, store.get('afit:paper:' + show, null), store.get('afit:paper', null), S.papers[0]?.id].find(id => id && pids.has(id));
  setPaper(pick || S.papers[0]?.id);
}
// switch paper: only its subjects, questions, progress and quizzes show
function setPaper(id, push) {""")

# boot: keep everything, then show the chosen department
rep("    setPaper(fromPath || store.get('afit:paper', 'general'));",
    """    S.departments = bank.departments || [{ id: 'ame', name: 'Aircraft Maintenance (AME)' }];
    S.cards = bank.cards || [];
    S.everyPaper = S.papers.map(p => ({ ...p, dept: p.dept || 'ame' })); S.everySubject = S.allSubjects; S.everyQ = S.full;
    const pathDept = fromPath ? (S.everyPaper.find(p => p.id === fromPath)?.dept) : null;
    const chosen = sessDept();
    setDept(chosen || null, chosen && (!pathDept || pathDept === chosen) ? fromPath : null);""")

# router: choose a department first; new views
rep("  if (S.profile?.must_change_password && name !== 'password') return go('password', true);",
    "  if (S.profile?.must_change_password && name !== 'password') return go('password', true);\n  if (!S.dept && name !== 'password' && name !== 'dept' && !AUTH.includes(name)) return go('dept', true);")
rep("folder: viewFolder };", "folder: viewFolder, dept: viewDept, cards: viewCards };")

# signing out forgets the department
rep("  if (!user) { teardownChat(); S.user = S.profile = S.quiz = null;", "  if (!user) { teardownChat(); sessDept(null); S.dept = null; S.user = S.profile = S.quiz = null;")

# shell: Study cards tab for a department that has cards, department in the menu
rep("  const links = [['', 'Home', I.home], ['practice', 'Practice', I.play], ['bank', 'Questions', I.book], ['chat', 'Chat', I.chat], ['history', 'History', I.hist]];",
    "  const links = [['', 'Home', I.home], ['practice', 'Practice', I.play], ['bank', 'Questions', I.book], ...(S.cards.some(c => (c.dept || 'cabin') === S.dept) ? [['cards', 'Study cards', I.book]] : []), ['chat', 'Chat', I.chat], ['history', 'History', I.hist]];")
rep("      <button data-act=\"goPassword\">${I.key} Change password</button>",
    "      ${S.dept ? `<button data-act=\"goDept\">${I.home} ${esc(deptName())} · Switch department</button>` : ''}\n      <button data-act=\"goPassword\">${I.key} Change password</button>")

# actions
rep("  goPassword() { go('password'); },",
    "  goPassword() { go('password'); },\n  goDept() { closeMenu(); go('dept'); },\n  pickDept(el, e) { e?.preventDefault(); setDept(el.dataset.d); toast(`${deptName()}`); go('', true); },\n  cardsSrc(el) { S.cardSrc = el.dataset.src; viewCards(); },")

# views
rep("function viewDashboard() {", r"""function viewDept() {
  const icon = id => id === 'cabin' ? I.users || I.home : I.plane || I.book;
  mount(`<div class="dept-page"><div class="dept-in">${logo()}
    <h1>Which department?</h1><p class="lead">Choose where you want to practise. You only see that department's questions. You can switch later from the account menu.</p>
    <div class="grid dept-grid">${S.departments.map(d => {
      const n = S.everyQ.filter(q => (S.everyPaper.find(p => p.id === S.subj[q.s]?.paper)?.dept || 'ame') === d.id).length;
      return `<button class="card dept-card ${S.dept === d.id ? 'on' : ''}" data-act="pickDept" data-d="${d.id}"><span class="dept-ic">${icon(d.id)}</span><b>${esc(d.name)}</b><span class="sub">${esc(d.sub || '')}</span><span class="sub"><b>${n.toLocaleString()}</b> questions</span></button>`;
    }).join('')}</div>
    <p class="muted small" style="margin-top:18px">Signed in as ${esc(S.profile?.full_name || '')} · <a href="#" data-act="signout">Sign out</a></p></div></div>`);
}
function viewCards() {
  const all = S.cards.filter(c => (c.dept || 'cabin') === S.dept);
  const srcs = [...new Set(all.map(c => c.src))];
  if (!S.cardSrc || !srcs.includes(S.cardSrc)) S.cardSrc = srcs[0];
  const list = all.filter(c => c.src === S.cardSrc);
  mount(shell('cards', `<div class="page-head"><div><div class="eyebrow">${esc(deptName())}</div><h1>Study cards</h1><p>Questions with written answers. Read the question, think of the answer, then tap to check.</p></div></div>
    <div class="seg-row">${srcs.map(x => `<button class="btn ${x === S.cardSrc ? 'btn-primary' : ''}" data-act="cardsSrc" data-src="${esc(x)}">${esc(x)} · ${all.filter(c => c.src === x).length}</button>`).join('')}</div>
    <div class="cards-list">${list.map((c, i) => `<details class="card study-card"><summary><span class="sc-n">${i + 1}</span><span class="sc-q">${esc(c.q)}</span><span class="sc-tap">Show answer</span></summary><div class="sc-a">${esc(c.a)}</div></details>`).join('') || '<p class="muted">No study cards here yet.</p>'}</div>`, { noPapers: true }));
}
function viewDashboard() {""")

# the sign-in page talks about every department
rep("        <p class=\"lead\">Past questions for the general paper, piston engines, pressurised and unpressurised airframe and compass, marked as you go.</p>",
    "        <p class=\"lead\">Past questions for Aircraft Maintenance (AME) licence papers and Cabin Crew, marked as you go. Choose your department after you sign in.</p>")
open(p, 'w', encoding='utf-8', newline='').write(s)
print('app.js patched')
