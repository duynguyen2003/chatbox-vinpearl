const VALID_EVENT_TYPES = new Set(['start', 'status', 'delta', 'final', 'error'])

function parseEvent(line) {
  let event
  try {
    event = JSON.parse(line)
  } catch (error) {
    throw new Error('Invalid chat stream event: malformed JSON', { cause: error })
  }

  if (!event || typeof event !== 'object' || !VALID_EVENT_TYPES.has(event.type)) {
    throw new Error('Invalid chat stream event: unsupported payload')
  }
  return event
}

export function createNdjsonParser(onEvent) {
  const decoder = new TextDecoder()
  let buffer = ''

  function drain(completeOnly) {
    const lines = buffer.split('\n')
    buffer = completeOnly ? lines.pop() : ''
    for (const rawLine of lines) {
      const line = rawLine.trim()
      if (line) onEvent(parseEvent(line))
    }
    if (!completeOnly) {
      const line = buffer.trim()
      buffer = ''
      if (line) onEvent(parseEvent(line))
    }
  }

  return {
    push(chunk) {
      buffer += decoder.decode(chunk, { stream: true })
      drain(true)
    },
    finish() {
      buffer += decoder.decode()
      if (!buffer.endsWith('\n')) buffer += '\n'
      drain(true)
    },
  }
}

export async function consumeNdjsonStream(stream, onEvent) {
  const reader = stream.getReader()
  const parser = createNdjsonParser(onEvent)
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      parser.push(value)
    }
    parser.finish()
  } catch (error) {
    await reader.cancel(error).catch(() => {})
    throw error
  } finally {
    reader.releaseLock()
  }
}

