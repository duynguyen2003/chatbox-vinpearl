import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const chatbot = await readFile(new URL('../src/Frontend/pages/Chatbot.jsx', import.meta.url), 'utf8')
const widget = await readFile(new URL('../src/Frontend/components/ChatWidget.jsx', import.meta.url), 'utf8')

for (const [name, source] of [['Chatbot', chatbot], ['ChatWidget', widget]]) {
  assert.match(source, /streamChatMessage/)
  assert.match(source, /AbortController/)
  assert.match(source, /isStreaming/)
  assert.match(source, /abort\(\)/)
  assert.match(source, /RichMessage/)
  assert.match(source, /StructuredMessage/)
  assert.match(source, /type="button"/)
  console.log(`${name} streaming contract passed`)
}
