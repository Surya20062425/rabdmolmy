#!/usr/bin/env node
const { spawnSync } = require('child_process');

// Find Python — prefer the one that has void installed
const python = process.platform === 'win32' ? 'python' : 'python3';
const args = process.argv.slice(2);

// Run void.cli as a module, forwarding stdio
const result = spawnSync(python, ['-m', 'void.cli', ...args], {
  stdio: 'inherit',
  windowsHide: true,
});

process.exit(result.status || 0);
