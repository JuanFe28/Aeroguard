#!/usr/bin/env node
/**
 * AeroGuard C-UAS — JavaScript Syntax & Module Grammar Validator
 * Verifica de forma estricta la sintaxis y gramática ECMAScript de todos
 * los archivos .js del frontend mediante el motor V8 nativo (node --check).
 * No requiere npm install ni dependencias de terceros.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PROJECT_ROOT = path.resolve(__dirname, '..');
const TARGET_DIR = path.join(PROJECT_ROOT, 'frontend', 'src');

let totalFiles = 0;
let totalErrors = 0;

console.log('='.repeat(70));
console.log(' [AEROGUARD C-UAS] Validacion de Sintaxis JavaScript (Node V8 engine)');
console.log('='.repeat(70));

function walkDir(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== 'node_modules' && entry.name !== '.git') {
        walkDir(fullPath);
      }
    } else if (entry.isFile() && entry.name.endsWith('.js')) {
      checkFile(fullPath);
    }
  }
}

function checkFile(filePath) {
  totalFiles++;
  const relPath = path.relative(PROJECT_ROOT, filePath).replace(/\\/g, '/');

  try {
    execFileSync(process.execPath, ['--check', filePath], {
      stdio: 'pipe',
      encoding: 'utf-8',
    });
    console.log(`  [OK]   ${relPath}`);
  } catch (err) {
    totalErrors++;
    console.error(`  [FAIL] ${relPath}`);
    const output = (err.stderr || err.stdout || err.message).trim();
    const indented = output
      .split('\n')
      .map((l) => '         ' + l)
      .join('\n');
    console.error(indented);
  }
}

if (fs.existsSync(TARGET_DIR)) {
  walkDir(TARGET_DIR);
} else {
  console.error(`[ERROR] Directorio objetivo no encontrado: ${TARGET_DIR}`);
  process.exit(1);
}

console.log('-'.repeat(70));
console.log(` Total auditados: ${totalFiles} archivos JS | Errores: ${totalErrors}`);
console.log('='.repeat(70));

if (totalErrors > 0) {
  console.error('[ERROR] Se encontraron errores de sintaxis en el codigo JavaScript.');
  process.exit(1);
} else {
  console.log('[SUCCESS] Sintaxis JavaScript 100% valida en todos los modulos SPA.');
  process.exit(0);
}
