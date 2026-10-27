#!/usr/bin/env node
/*
 * Chatbot daily cost alert.
 *
 * Reads today's token usage (chatbot/usage/YYYY-MM-DD.jsonl, written by the chatbot for every AI call),
 * prices it with prices.json, and emails an alert over SMTP once the day's spend passes the limit
 * (DAILY_COST_LIMIT_USD, default $1). It only sends one email per day. It NEVER stops the chatbot.
 *
 * The chatbot starts this script in the background after each AI call (chatbot/usage.py), so it runs
 * only when there is a request: no cron, nothing running in between. Once today's email is sent, the
 * chatbot stops starting it until the next day.
 *
 *   node cost-alert.js            check once (what the chatbot runs)
 *   node cost-alert.js --dry-run  print the email instead of sending it
 *
 * Settings come from the environment or ../.env (the chatbot's .env):
 *   DAILY_COST_LIMIT_USD=1
 *   SMTP_HOST=  SMTP_PORT=587  SMTP_SECURE=false  SMTP_USER=  SMTP_PASS=
 *   ALERT_FROM=  ALERT_TO=          (ALERT_TO may be a comma-separated list)
 *   USAGE_DIR=../usage
 */
'use strict';

const fs = require('fs');
const path = require('path');

const HERE = __dirname;

function loadEnv(file) {
  // KEY=VALUE lines; real environment variables win.
  if (!fs.existsSync(file)) return;
  for (const raw of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || !line.includes('=')) continue;
    const i = line.indexOf('=');
    const key = line.slice(0, i).trim();
    const value = line.slice(i + 1).trim().replace(/^["']|["']$/g, '');
    if (!(key in process.env)) process.env[key] = value;
  }
}

function config(env = process.env) {
  return {
    limit: Number(env.DAILY_COST_LIMIT_USD || 1),
    usageDir: path.resolve(HERE, env.USAGE_DIR || '../usage'),
    stateDir: path.resolve(HERE, env.ALERT_STATE_DIR || env.USAGE_DIR || '../usage'),
    smtp: {
      host: env.SMTP_HOST,
      port: Number(env.SMTP_PORT || 587),
      secure: String(env.SMTP_SECURE || 'false').toLowerCase() === 'true',   // true for port 465
      auth: env.SMTP_USER ? { user: env.SMTP_USER, pass: env.SMTP_PASS } : undefined,
    },
    from: env.ALERT_FROM || env.SMTP_USER,
    to: env.ALERT_TO,
  };
}

function utcDay(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

function loadPrices() {
  return JSON.parse(fs.readFileSync(path.join(HERE, 'prices.json'), 'utf8'));
}

/** Cost in USD of one usage record. Cached input tokens are billed at the cached rate. */
function costOf(rec, prices) {
  const p = prices[rec.model] || prices._default;
  const cached = Math.min(rec.cached || 0, rec.input || 0);
  const fresh = (rec.input || 0) - cached;
  return (fresh * p.input + cached * p.cached + (rec.output || 0) * p.output) / 1e6;
}

/** Totals for one day's usage file. Bad lines are skipped, never fatal. */
function summarize(day, cfg, prices = loadPrices()) {
  const file = path.join(cfg.usageDir, `${day}.jsonl`);
  const out = { day, total: 0, calls: 0, byProvider: {}, unknownModels: new Set() };
  if (!fs.existsSync(file)) return out;
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    let rec;
    try { rec = JSON.parse(line); } catch { continue; }
    if (!prices[rec.model]) out.unknownModels.add(rec.model);
    const c = costOf(rec, prices);
    out.total += c;
    out.calls += 1;
    const b = (out.byProvider[rec.provider] ||= { cost: 0, calls: 0 });
    b.cost += c;
    b.calls += 1;
  }
  return out;
}

function alertFile(day, cfg) {
  return path.join(cfg.stateDir, `.cost-alert-sent-${day}`);
}

function buildEmail(s, cfg) {
  const lines = Object.entries(s.byProvider)
    .map(([name, b]) => `  ${name}: $${b.cost.toFixed(4)} (${b.calls} AI calls)`);
  return {
    from: cfg.from,
    to: cfg.to,
    subject: `Caprae chatbot: AI spend passed $${cfg.limit.toFixed(2)} today ($${s.total.toFixed(2)})`,
    text: [
      `The site chatbot's AI spend for ${s.day} (UTC) is $${s.total.toFixed(4)}, above the daily limit of $${cfg.limit.toFixed(2)}.`,
      '',
      `AI calls today: ${s.calls} (each visitor message usually makes 2: a quick check and the answer)`,
      ...lines,
      s.unknownModels.size ? `\nPriced at the default rate (not in prices.json): ${[...s.unknownModels].join(', ')}` : '',
      '',
      'The chatbot is still running. This is an alert only; nothing has been switched off.',
      'If the traffic looks unusual, check the chatbot logs, or lower PER_IP_PER_DAY / DAILY_REQUEST_LIMIT in chatbot/.env.',
      '',
      'One alert is sent per day.',
    ].filter((l) => l !== null).join('\n'),
  };
}

/** Check today's spend; send one email per day once it passes the limit. Returns what happened. */
async function check({ cfg = config(), now = new Date(), dryRun = false, transport } = {}) {
  const day = utcDay(now);
  const s = summarize(day, cfg);
  const result = { day, total: s.total, calls: s.calls, limit: cfg.limit, emailed: false, reason: '' };

  if (s.total <= cfg.limit) { result.reason = 'under limit'; return result; }
  if (fs.existsSync(alertFile(day, cfg))) { result.reason = 'already emailed today'; return result; }

  const mail = buildEmail(s, cfg);
  if (dryRun) {
    console.log(`--- DRY RUN: email that would be sent ---\nTo: ${mail.to}\nSubject: ${mail.subject}\n\n${mail.text}\n---`);
    result.reason = 'dry run';
    return result;
  }
  if (!cfg.smtp.host || !cfg.to || !cfg.from) {
    result.reason = 'over limit, but SMTP_HOST / ALERT_TO / ALERT_FROM are not set';
    return result;
  }
  const t = transport || require('nodemailer').createTransport(cfg.smtp);
  await t.sendMail(mail);
  fs.mkdirSync(cfg.stateDir, { recursive: true });
  fs.writeFileSync(alertFile(day, cfg), new Date().toISOString());
  result.emailed = true;
  result.reason = 'over limit: email sent';
  return result;
}

function report(r) {
  console.log(`[${new Date().toISOString()}] ${r.day}: $${r.total.toFixed(4)} from ${r.calls} AI calls ` +
              `(limit $${r.limit.toFixed(2)}) - ${r.reason}`);
}

async function main() {
  loadEnv(path.join(HERE, '..', '.env'));
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const cfg = config();
  try {
    report(await check({ cfg, dryRun }));
  } catch (e) {
    console.error(`[${new Date().toISOString()}] check failed: ${e.message}`);
  }
}

if (require.main === module) main();

module.exports = { check, summarize, costOf, config, loadEnv, utcDay, buildEmail };
