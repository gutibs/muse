#!/usr/bin/env node
/**
 * Bump de versión del APK — fuente única de la lógica de versionado.
 *
 * Lee la versión actual de android/app/build.gradle, calcula la siguiente según
 * el nivel (patch|minor|major), incrementa el versionCode en +1 (entero
 * monotónico que exige Play Store) y escribe build.gradle + package.json
 * sincronizados.
 *
 * Convención (ver CLAUDE.md): versionName humano `V<major>.<minor>.<patch>` en
 * build.gradle; package.json lleva el mismo semver SIN la `V` (npm exige semver).
 *
 * Uso: node scripts/bump-version.mjs <patch|minor|major>
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const LEVELS = ['patch', 'minor', 'major'];
const level = process.argv[2];

if (!LEVELS.includes(level)) {
	console.error(`Uso: node scripts/bump-version.mjs <${LEVELS.join('|')}>`);
	process.exit(1);
}

const appDir = join(dirname(fileURLToPath(import.meta.url)), '..');
const gradlePath = join(appDir, 'android', 'app', 'build.gradle');
const pkgPath = join(appDir, 'package.json');

const gradle = readFileSync(gradlePath, 'utf8');

const codeMatch = gradle.match(/versionCode\s+(\d+)/);
const nameMatch = gradle.match(/versionName\s+"V?(\d+)\.(\d+)\.(\d+)"/);

if (!codeMatch || !nameMatch) {
	console.error('No pude parsear versionCode/versionName en build.gradle.');
	process.exit(1);
}

const oldCode = Number(codeMatch[1]);
let [, xs, ys, zs] = nameMatch;
let [x, y, z] = [Number(xs), Number(ys), Number(zs)];

if (level === 'patch') z += 1;
else if (level === 'minor') { y += 1; z = 0; }
else if (level === 'major') { x += 1; y = 0; z = 0; }

const newCode = oldCode + 1;
const oldName = `V${nameMatch[1]}.${nameMatch[2]}.${nameMatch[3]}`;
const newName = `V${x}.${y}.${z}`;
const newSemver = `${x}.${y}.${z}`;

const newGradle = gradle
	.replace(/versionCode\s+\d+/, `versionCode ${newCode}`)
	.replace(/versionName\s+"V?\d+\.\d+\.\d+"/, `versionName "${newName}"`);
writeFileSync(gradlePath, newGradle);

const pkg = readFileSync(pkgPath, 'utf8');
const newPkg = pkg.replace(/("version":\s*")[^"]+(")/, `$1${newSemver}$2`);
writeFileSync(pkgPath, newPkg);

console.log(`bump (${level})`);
console.log(`  versionName ${oldName} → ${newName}`);
console.log(`  versionCode ${oldCode} → ${newCode}`);
console.log(`  package.json version → ${newSemver}`);
