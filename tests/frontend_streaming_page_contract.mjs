import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const chatbot = await readFile(new URL('../src/Frontend/pages/Chatbot.jsx', import.meta.url), 'utf8')
const widget = await readFile(new URL('../src/Frontend/components/ChatWidget.jsx', import.meta.url), 'utf8')
const chatStatus = await readFile(new URL('../src/Frontend/services/chatStatus.js', import.meta.url), 'utf8')
const rootStyles = await readFile(new URL('../src/Frontend/index.css', import.meta.url), 'utf8')
const chatbotStyles = await readFile(new URL('../src/Frontend/styles/pages/Chatbot.css', import.meta.url), 'utf8')
const widgetStyles = await readFile(new URL('../src/Frontend/styles/components/ChatWidget.css', import.meta.url), 'utf8')
const sourcePills = await readFile(new URL('../src/Frontend/components/SourcePills.jsx', import.meta.url), 'utf8')

for (const [name, source] of [['Chatbot', chatbot], ['ChatWidget', widget]]) {
  assert.match(source, /streamChatMessage/)
  assert.match(source, /AbortController/)
  assert.match(source, /isStreaming/)
  assert.match(source, /abort\(\)/)
  assert.match(source, /RichMessage/)
  assert.match(source, /StructuredMessage/)
  assert.match(source, /streamStatusLabel/)
  assert.match(source, /type="button"/)
  console.log(`${name} streaming contract passed`)
}

for (const stage of ['analyzing', 'understanding', 'planning', 'searching', 'evaluating', 'composing', 'verifying', 'generating']) {
  assert.match(chatStatus, new RegExp(`${stage}:`))
}
console.log('Streaming progress labels contract passed')

assert.match(widget, /const \[isComposerExpanded, setIsComposerExpanded\] = useState\(false\)/)
assert.match(widget, /chat-widget__form--\$\{isComposerExpanded \? 'expanded' : 'compact'\}/)
assert.match(widget, /<textarea/)
assert.match(widget, /onFocus=\{handleInputFocus\}/)
assert.match(widget, /onKeyDown=\{handleInputKeyDown\}/)
assert.match(widget, /event\.nativeEvent\.isComposing/)
console.log('ChatWidget composer expansion contract passed')

assert.match(chatbot, /Maximize2/)
assert.match(chatbot, /Minimize2/)
assert.match(chatbot, /isFullscreen/)
assert.match(chatbot, /chatbot-page--fullscreen/)
assert.match(chatbot, /chatbot-page__avatar-icon--large/)
assert.doesNotMatch(chatbot, /VINPEARL_LOGO_URL/)
console.log('Chatbot fullscreen/icon contract passed')

assert.match(sourcePills, /function decodeSourceValue/)
assert.match(sourcePills, /function parseUrlLike/)
assert.match(sourcePills, /normalizeSource\(source, sourcesLabel\)/)
assert.match(sourcePills, /href=\{normalized\.href\}/)
console.log('Source pills URL normalization contract passed')

for (const token of ['--chat-accent', '--chat-surface', '--chat-border', '--chat-ink']) {
  assert.match(rootStyles, new RegExp(`${token}:`))
  assert.match(chatbotStyles, new RegExp(`var\\(${token}\\)`))
  assert.match(widgetStyles, new RegExp(`var\\(${token}\\)`))
}
console.log('Shared chat palette contract passed')
