// Tests use fake usage records and a local SMTP server: no AI calls, no real email.
'use strict';

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { SMTPServer } = require('smtp-server');
const { check, summarize, costOf, utcDay } = require('../cost-alert');

const PRICES = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'prices.json'), 'utf8'));
// One real visitor message on Gemini 3.5 Flash-Lite (measured): classify 365 in / 14 out, answer 6492 in / 153 out.
const CLASSIFY = { provider: 'gemini', model: 'gemini-3.5-flash-lite', step: 'classify', input: 365, cached: 0, output: 14 };
const ANSWER = { provider: 'gemini', model: 'gemini-3.5-flash-lite', step: 'answer', input: 6492, cached: 0, output: 153 };

function tempUsage(records, extraLines = []) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cc-cost-'));
  const lines = records.map((r) => JSON.stringify({ ts: 0, ...r })).concat(extraLines);
  fs.writeFileSync(path.join(dir, `${utcDay()}.jsonl`), lines.join('\n') + '\n');
  return dir;
}

function messages(n) {
  const out = [];
  for (let i = 0; i < n; i++) out.push(CLASSIFY, ANSWER);
  return out;
}

async function smtp() {
  const received = [];
  const server = new SMTPServer({
    authOptional: true, disabledCommands: ['STARTTLS'], logger: false,
    onData(stream, session, cb) {
      let data = '';
      stream.on('data', (c) => { data += c; });
      stream.on('end', () => { received.push({ data, to: session.envelope.rcptTo.map((r) => r.address) }); cb(); });
    },
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  return { server, received, port: server.server.address().port };
}

function cfgFor(dir, port, extra = {}) {
  return {
    limit: 1, usageDir: dir, stateDir: dir,
    smtp: { host: '127.0.0.1', port, secure: false, ignoreTLS: true },
    from: 'bot@capraecapital.com', to: 'alerts@capraecapital.com', ...extra,
  };
}

test('cost of one measured message matches the published Gemini prices', () => {
  const perMessage = costOf(CLASSIFY, PRICES) + costOf(ANSWER, PRICES);
  // 365*0.30 + 14*2.50 + 6492*0.30 + 153*2.50 = 109.5 + 35 + 1947.6 + 382.5 = 2474.6 / 1e6
  assert.strictEqual(Number(perMessage.toFixed(7)), 0.0024746);
});

test('cached input tokens are billed at the cached rate', () => {
  const rec = { model: 'deepseek-flash', input: 1000, cached: 800, output: 0 };
  assert.strictEqual(Number(costOf(rec, PRICES).toFixed(8)), Number(((200 * 0.30 + 800 * 0.006) / 1e6).toFixed(8)));
});

test('unknown models use the (higher) default rate, and bad lines are skipped', () => {
  const dir = tempUsage([{ provider: 'x', model: 'mystery-model', input: 1e6, output: 0 }], ['not json', '{"broken":']);
  const s = summarize(utcDay(), { usageDir: dir }, PRICES);
  assert.strictEqual(s.calls, 1);
  assert.strictEqual(s.total, PRICES._default.input);
  assert.ok(s.unknownModels.has('mystery-model'));
});

test('under the limit: no email', async () => {
  const { server, received, port } = await smtp();
  const dir = tempUsage(messages(100));                     // 100 messages ~ $0.24
  const r = await check({ cfg: cfgFor(dir, port) });
  server.close();
  assert.strictEqual(r.emailed, false);
  assert.strictEqual(r.reason, 'under limit');
  assert.strictEqual(received.length, 0);
});

test('over the limit: exactly one email per day, sent over SMTP', async () => {
  const { server, received, port } = await smtp();
  const dir = tempUsage(messages(420));                     // 420 messages ~ $1.04
  const first = await check({ cfg: cfgFor(dir, port) });
  const second = await check({ cfg: cfgFor(dir, port) });   // same day again
  server.close();
  assert.strictEqual(first.emailed, true);
  assert.ok(first.total > 1);
  assert.strictEqual(second.emailed, false);
  assert.strictEqual(second.reason, 'already emailed today');
  assert.strictEqual(received.length, 1);
  assert.deepStrictEqual(received[0].to, ['alerts@capraecapital.com']);
  assert.match(received[0].data, /Subject: Caprae chatbot: AI spend passed \$1\.00 today \(\$1\.04\)/);
  assert.match(received[0].data, /still running/);
});

test('over the limit without SMTP settings: reports it, does not crash', async () => {
  const dir = tempUsage(messages(500));
  const r = await check({ cfg: cfgFor(dir, 0, { smtp: { host: undefined }, to: undefined }) });
  assert.strictEqual(r.emailed, false);
  assert.match(r.reason, /SMTP_HOST/);
});

test('no usage file yet (no chats today): $0, no email', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cc-cost-'));
  const r = await check({ cfg: cfgFor(dir, 0) });
  assert.strictEqual(r.total, 0);
  assert.strictEqual(r.emailed, false);
});

test('command line --dry-run prints the email', () => {
  const dir = tempUsage(messages(450));
  const out = execFileSync(process.execPath, [path.join(__dirname, '..', 'cost-alert.js'), '--dry-run'],
    { env: { ...process.env, USAGE_DIR: dir, ALERT_TO: 'alerts@capraecapital.com', ALERT_FROM: 'bot@capraecapital.com' }, encoding: 'utf8' });
  assert.match(out, /DRY RUN/);
  assert.match(out, /AI spend passed \$1\.00 today/);
});
