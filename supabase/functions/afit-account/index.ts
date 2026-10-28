// NCAT Exams account mailer.
// POST { action: 'signup', fullName, email }  -> creates the login with a temporary password and emails it
// POST { action: 'reset', email }             -> issues a fresh temporary password and emails it
// People sign in with the temporary password and must choose their own before using the app.
// Secrets (shared with the project): SENDGRID_API_KEY, SENDGRID_FROM_EMAIL. Optional: NCAT_APP_URL.
import { createClient } from 'npm:@supabase/supabase-js@2.45.4';

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json' } });
const fail = (error: string, status = 400) => json({ error }, status);

const EMAIL_RE = /^[^\s@<>,;"]+@[^\s@<>,;"]+\.[^\s@<>,;"]+$/;
const APP_URL = (Deno.env.get('NCAT_APP_URL') || 'https://afit-exams.vercel.app/').replace(/\/?$/, '/');
const RESET_COOLDOWN_MS = 2 * 60 * 1000;
const esc = (s: string) => s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));

const db = () => createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!, { auth: { persistSession: false } });

function tempPassword() {
  const abc = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  const s = [...bytes].map(b => abc[b % abc.length]).join('');
  return `NCAT-${s.slice(0, 4)}-${s.slice(4)}`;
}

async function sendMail(to: string, name: string, password: string, kind: 'signup' | 'reset') {
  const key = Deno.env.get('SENDGRID_API_KEY'), from = Deno.env.get('SENDGRID_FROM_EMAIL');
  if (!key || !from) throw new Error('Email sending is not set up.');
  const first = name.split(' ')[0] || 'there';
  const subject = kind === 'signup' ? 'Welcome to NCAT Exams — your temporary password' : 'NCAT Exams — your new temporary password';
  const intro = kind === 'signup'
    ? 'Your NCAT Exams account is ready. Use the temporary password below to sign in. You’ll be asked to choose your own password straight away.'
    : 'We received a request to reset your NCAT Exams password. Use the temporary password below to sign in, then choose a new password. If you didn’t ask for this, sign in and change your password.';
  const text = `Hi ${first},\n\n${intro}\n\nEmail: ${to}\nTemporary password: ${password}\n\nSign in: ${APP_URL}\n\n— NCAT Exams`;
  const html = `<!doctype html><html><body style="margin:0;background:#eef2f7;font-family:Segoe UI,Arial,sans-serif;color:#0f1f33">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2f7;padding:32px 12px"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(15,31,51,.08)">
<tr><td style="background:#0b2545;padding:22px 28px;color:#ffffff;font-size:20px;font-weight:700;letter-spacing:.3px">✈ NCAT Exams</td></tr>
<tr><td style="padding:28px">
<p style="margin:0 0 14px;font-size:16px">Hi ${esc(first)},</p>
<p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#334155">${esc(intro)}</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;border-radius:12px"><tr><td style="padding:16px 18px">
<div style="font-size:12px;text-transform:uppercase;letter-spacing:.8px;color:#64748b">Email</div>
<div style="font-size:15px;margin:2px 0 12px">${esc(to)}</div>
<div style="font-size:12px;text-transform:uppercase;letter-spacing:.8px;color:#64748b">Temporary password</div>
<div style="font-family:Consolas,Menlo,monospace;font-size:22px;font-weight:700;letter-spacing:1.5px;color:#0b2545;margin-top:4px">${esc(password)}</div>
</td></tr></table>
<p style="margin:24px 0 0"><a href="${APP_URL}" style="display:inline-block;background:#1d6fd8;color:#ffffff;text-decoration:none;font-weight:600;padding:12px 22px;border-radius:10px">Sign in to NCAT Exams</a></p>
<p style="margin:22px 0 0;font-size:13px;color:#64748b;line-height:1.5">For your security, this password only gets you as far as choosing your own password.</p>
</td></tr></table></td></tr></table></body></html>`;
  const r = await fetch('https://api.sendgrid.com/v3/mail/send', {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: to }] }],
      from: { email: from, name: 'NCAT Exams' },
      subject,
      content: [{ type: 'text/plain', value: text }, { type: 'text/html', value: html }],
    }),
  });
  if (!r.ok) { console.error('SendGrid', r.status, (await r.text()).slice(0, 300)); throw new Error(`The email couldn’t be sent (${r.status}).`); }
}

async function signup(fullName: string, email: string) {
  if (fullName.length < 2 || fullName.length > 80) return fail('Enter your full name.');
  const sb = db();
  const { data: existing } = await sb.from('afit_profiles').select('id').eq('email', email).maybeSingle();
  if (existing) return fail('An account with this email already exists. Sign in, or use “Forgot password” to get a new temporary password.', 409);

  const since = new Date(Date.now() - 10 * 60 * 1000).toISOString();
  const { count } = await sb.from('afit_profiles').select('id', { count: 'exact', head: true }).gte('created_at', since);
  if ((count ?? 0) > 40) return fail('Too many sign-ups right now. Please try again in a few minutes.', 429);

  const password = tempPassword();
  const { data: created, error } = await sb.auth.admin.createUser({ email, password, email_confirm: true, user_metadata: { full_name: fullName, app: 'afit-exams' } });
  if (error || !created?.user) {
    if (/already|registered|exists/i.test(error?.message ?? '')) return fail('This email already has a login on our platform. Sign in with that password instead.', 409);
    console.error('createUser', error?.message);
    return fail('We couldn’t create your account. Please try again.', 500);
  }
  const id = created.user.id;
  const { error: pErr } = await sb.from('afit_profiles').insert({ id, email, full_name: fullName, managed: true, must_change_password: true, temp_issued_at: new Date().toISOString() });
  if (pErr) { await sb.auth.admin.deleteUser(id); console.error('profile', pErr.message); return fail('We couldn’t create your account. Please try again.', 500); }
  try {
    await sendMail(email, fullName, password, 'signup');
  } catch (e) {
    await sb.auth.admin.deleteUser(id); // profile goes with it (on delete cascade)
    return fail(`${(e as Error).message} Please try again.`, 502);
  }
  return json({ ok: true, message: `We’ve emailed a temporary password to ${email}. Check your inbox (and spam folder), then sign in.` });
}

async function reset(email: string) {
  const generic = json({ ok: true, message: `If ${email} has an NCAT Exams account, a new temporary password is on its way. Check your inbox and spam folder.` });
  const sb = db();
  const { data: p } = await sb.from('afit_profiles').select('id, full_name, managed, temp_issued_at').eq('email', email).maybeSingle();
  if (!p || !p.managed) return generic;
  if (p.temp_issued_at && Date.now() - new Date(p.temp_issued_at).getTime() < RESET_COOLDOWN_MS)
    return fail('A temporary password was sent a moment ago. Please wait two minutes before asking again.', 429);
  const password = tempPassword();
  const { error } = await sb.auth.admin.updateUserById(p.id, { password });
  if (error) { console.error('updateUser', error.message); return fail('We couldn’t reset the password. Please try again.', 500); }
  await sb.from('afit_profiles').update({ must_change_password: true, temp_issued_at: new Date().toISOString() }).eq('id', p.id);
  try { await sendMail(email, p.full_name, password, 'reset'); } catch (e) { return fail((e as Error).message, 502); }
  return generic;
}

Deno.serve(async req => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });
  if (req.method !== 'POST') return fail('Use POST', 405);
  try {
    const body = await req.json().catch(() => ({}));
    const email = String(body.email ?? '').trim().toLowerCase();
    if (!EMAIL_RE.test(email) || email.length > 200) return fail('Enter a valid email address.');
    if (body.action === 'signup') return await signup(String(body.fullName ?? '').trim().replace(/\s+/g, ' '), email);
    if (body.action === 'reset') return await reset(email);
    return fail('Unknown action.');
  } catch (e) {
    console.error(e);
    return fail('Something went wrong. Please try again.', 500);
  }
});
