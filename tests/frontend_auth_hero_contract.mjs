import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const auth = await readFile(new URL('../src/Frontend/pages/Auth.jsx', import.meta.url), 'utf8')
const styles = await readFile(new URL('../src/Frontend/styles/pages/Auth.css', import.meta.url), 'utf8')

assert.match(auth, /function titleTokens\(/)
assert.match(auth, /Intl\.Segmenter/)
assert.match(auth, /Array\.from\(text\)/)
assert.match(auth, /auth-hero__word/)
assert.match(auth, /auth-hero__char/)
assert.match(auth, /--auth-char-index/)
assert.doesNotMatch(auth, /auth-hero__eyebrow/)
assert.match(styles, /auth-hero-char-reveal/)
assert.match(styles, /auth-hero__word \{[\s\S]*white-space: nowrap/)
assert.match(styles, /animation-delay: calc\(var\(--auth-char-index\) \* 45ms\)/)
assert.doesNotMatch(styles, /auth-hero__eyebrow/)
assert.match(styles, /prefers-reduced-motion: reduce/)

console.log('Auth hero character reveal contract passed')
