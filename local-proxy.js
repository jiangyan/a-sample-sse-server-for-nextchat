#!/usr/bin/env node

const readline = require('readline');
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));
const yargs = require('yargs/yargs');

const argv = yargs(process.argv.slice(2)).argv;
const remoteUrl = argv.url || process.env.REMOTE_MCP_URL;

if (!remoteUrl) {
  console.error("Usage: node local-proxy.js --url=<REMOTE_MCP_SERVER_URL>");
  process.exit(1);
}

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false,
});

rl.on('line', async (line) => {
  try {
    const req = JSON.parse(line);
    const res = await fetch(remoteUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    const text = await res.text();
    // Only forward response if non-empty and status is not 202
    if (!text || res.status === 202) {
      // Notification or no output expected; do nothing
      return;
    }
    let data;
    try {
      data = JSON.parse(text);
    } catch (err) {
      throw new Error(`Invalid JSON from server: ${text}`);
    }
    process.stdout.write(JSON.stringify(data) + '\n');
  } catch (err) {
    process.stderr.write(JSON.stringify({
      error: { code: -32000, message: err.message }
    }) + '\n');
  }
});

process.on('SIGINT', () => process.exit(0));