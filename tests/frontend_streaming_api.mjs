import assert from 'node:assert/strict'

import { createNdjsonParser } from '../src/Frontend/services/chatStream.js'

const encoder = new TextEncoder()
const received = []
const parser = createNdjsonParser((event) => received.push(event))
const payload = [
  JSON.stringify({ type: 'delta', text: 'Xin chào ' }),
  JSON.stringify({ type: 'delta', text: 'Phú Quốc 🌴' }),
  JSON.stringify({ type: 'final', answer: 'Xin chào Phú Quốc 🌴' }),
].join('\n') + '\n'

const bytes = encoder.encode(payload)
parser.push(bytes.slice(0, 7))
parser.push(bytes.slice(7, bytes.length - 3))
parser.push(bytes.slice(bytes.length - 3))
parser.finish()

assert.deepEqual(received.map((event) => event.type), ['delta', 'delta', 'final'])
assert.equal(received[1].text, 'Phú Quốc 🌴')
assert.equal(received[2].answer, 'Xin chào Phú Quốc 🌴')

assert.throws(
  () => {
    const malformed = createNdjsonParser(() => {})
    malformed.push(encoder.encode('{not-json}\n'))
  },
  /Invalid chat stream event/,
)

console.log('frontend streaming API contract passed')

