import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bot, Send, Sparkles, Square, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { clearStoredMessages, loadStoredMessages, saveStoredMessages, streamChatMessage } from '../services/api'
import RichMessage from './RichMessage'
import StructuredMessage from './StructuredMessage'
import '../styles/components/ChatWidget.css'

export function openAiChat(promptText) {
  window.dispatchEvent(new CustomEvent('open-ai-chat', { detail: { prompt: promptText } }))
}

function stopGeneratingLabel(language) {
  return {
    en: 'Stop generating',
    vi: 'Dừng tạo câu trả lời',
    ko: '답변 생성 중지',
    ja: '回答の生成を停止',
    zh: '停止生成回答',
  }[language] || 'Stop generating'
}

function streamStatusLabel(language, stage) {
  const labels = {
    en: { analyzing: 'Understanding your request…', generating: 'Writing the answer…' },
    vi: { analyzing: 'Đang phân tích yêu cầu…', generating: 'Đang viết câu trả lời…' },
    ko: { analyzing: '요청을 분석하고 있습니다…', generating: '답변을 작성하고 있습니다…' },
    ja: { analyzing: 'リクエストを分析しています…', generating: '回答を作成しています…' },
    zh: { analyzing: '正在分析您的请求…', generating: '正在生成回答…' },
  }
  return labels[language]?.[stage] || labels.en[stage] || labels.en.analyzing
}

function ChatWidget() {
  const { language, t } = useLanguage()
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [isOpen, setIsOpen] = useState(false)
  const [isComposerExpanded, setIsComposerExpanded] = useState(false)
  const [quickInput, setQuickInput] = useState('')
  const [messages, setMessages] = useState(() => {
    const storedMessages = loadStoredMessages()
    return Array.isArray(storedMessages) && storedMessages.length > 0
      ? storedMessages
      : []
  })
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const threadRef = useRef(null)
  const inputRef = useRef(null)
  const previousUserIdRef = useRef(undefined)
  const abortControllerRef = useRef(null)
  const shouldAutoScrollRef = useRef(true)
  const requestActiveRef = useRef(false)

  useEffect(() => () => abortControllerRef.current?.abort(), [])

  useEffect(() => {
    async function handleOpenAiChat(event) {
      setIsOpen(true)
      const prompt = event.detail?.prompt
      if (!prompt) return
      await handleSend(prompt)
    }

    window.addEventListener('open-ai-chat', handleOpenAiChat)
    return () => window.removeEventListener('open-ai-chat', handleOpenAiChat)
  }, [language, t.chatError])

  useEffect(() => {
    if (isOpen && messages.length > 0 && shouldAutoScrollRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, loading, isOpen])

  // Frontend-generated error messages should follow the selected UI language.
  // Real chat history remains untouched.
  useEffect(() => {
    setMessages((current) => {
      let changed = false
      const next = current.map((message) => {
        const isLocalError = message.localizationKey === 'chatError'
          || String(message.id || '').startsWith('err-')
        if (!isLocalError) return message
        if (message.text === t.chatError && message.language === language) return message
        changed = true
        return {
          ...message,
          text: t.chatError,
          language,
          localizationKey: 'chatError',
        }
      })
      return changed ? next : current
    })
  }, [language, t.chatError])

  useEffect(() => {
    if (authLoading || user) return
    if (messages.length > 0) {
      saveStoredMessages(messages)
    }
  }, [authLoading, messages, user])

  useEffect(() => {
    if (authLoading) return

    const previousUserId = previousUserIdRef.current
    const nextUserId = user?.id || null
    previousUserIdRef.current = nextUserId

    // Authenticated chat content belongs in PostgreSQL, not shared browser
    // sessionStorage. Also clear visible widget state when identity changes so
    // another account on the same browser never inherits the previous user's UI.
    if (user) {
      clearStoredMessages()
      if (previousUserId === undefined || (previousUserId && previousUserId !== user.id)) {
        setMessages([])
      }
      return
    }

    if (previousUserId) {
      clearStoredMessages()
      setMessages([])
    }
  }, [authLoading, user?.id])

  function handleTriggerClick() {
    shouldAutoScrollRef.current = true
    setIsComposerExpanded(false)
    setIsOpen(true)
  }

  function handleInputFocus() {
    setIsComposerExpanded(true)
  }

  function handleInputBlur() {
    if (!quickInput.trim() && !loading) setIsComposerExpanded(false)
  }

  function handleInputKeyDown(event) {
    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return
    event.preventDefault()
    handleSend()
  }

  function handleThreadScroll(event) {
    const element = event.currentTarget
    const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight
    shouldAutoScrollRef.current = distanceFromBottom < 72
  }

  async function handleSend(promptText) {
    const prompt = (promptText || quickInput).trim()
    if (!prompt || requestActiveRef.current) return

    requestActiveRef.current = true
    setIsComposerExpanded(false)
    setQuickInput('')

    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: prompt,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    const assistantId = `assistant-stream-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
    const controller = new AbortController()
    abortControllerRef.current?.abort()
    abortControllerRef.current = controller
    const streamingMessage = {
      id: assistantId,
      sender: 'assistant',
      text: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      language,
      isStreaming: true,
      streamStatus: 'analyzing',
      sources: [],
    }

    shouldAutoScrollRef.current = true
    setMessages((prev) => [...prev, userMsg, streamingMessage])
    setLoading(true)

    try {
      const response = await streamChatMessage(prompt, language, {
        signal: controller.signal,
        onEvent(event) {
          if (event.type !== 'delta' && event.type !== 'status') return
          setMessages((current) => current.map((message) => {
            if (message.id !== assistantId) return message
            if (event.type === 'delta') {
              return { ...message, text: `${message.text}${event.text}` }
            }
            return { ...message, streamStatus: event.stage }
          }))
        },
      })
      setMessages((current) => current.map((message) => (
        message.id === assistantId
          ? { ...response, id: assistantId, isStreaming: false }
          : message
      )))
    } catch (error) {
      if (error?.name === 'AbortError') {
        setMessages((current) => current.flatMap((message) => {
          if (message.id !== assistantId) return [message]
          return message.text ? [{ ...message, isStreaming: false, wasStopped: true }] : []
        }))
      } else {
        setMessages((current) => current.map((message) => (
          message.id === assistantId
            ? {
                ...message,
                text: message.text || t.chatError,
                language,
                localizationKey: message.text ? undefined : 'chatError',
                isStreaming: false,
                isError: !message.text,
                streamError: true,
              }
            : message
        )))
      }
    } finally {
      if (abortControllerRef.current === controller) abortControllerRef.current = null
      requestActiveRef.current = false
      setLoading(false)
    }
  }

  function stopStreaming() {
    abortControllerRef.current?.abort()
  }

  function handleQuickSend(event) {
    event.preventDefault()
    handleSend()
  }

  return (
    <div className="chat-widget">
      {!isOpen && (
        <button
          className="chat-widget__trigger"
          type="button"
          onClick={handleTriggerClick}
          title={t.navAiChat}
        >
          <Sparkles className="chat-widget__trigger-icon" />
          <span className="chat-widget__trigger-label">{t.navAiChat}</span>
          <span className="chat-widget__status-dot" aria-hidden="true">
            <span className="chat-widget__status-ping" />
            <span className="chat-widget__status-core" />
          </span>
        </button>
      )}

      {isOpen && (
        <section className="chat-widget__panel" aria-label={t.navAiChat}>
          <header className="chat-widget__header">
            <div className="chat-widget__identity">
              <div className="chat-widget__avatar">
                <Bot className="chat-widget__avatar-icon" />
              </div>
              <div>
                <h4 className="chat-widget__title">{t.chatWidgetTitle}</h4>
                <p className="chat-widget__online">
                  <span className="chat-widget__online-dot" />
                  {t.chatWidgetOnline}
                </p>
              </div>
            </div>

            <button
              className="chat-widget__close"
              type="button"
              aria-label={t.close}
              onClick={() => {
                setIsComposerExpanded(false)
                setIsOpen(false)
              }}
            >
              <X className="chat-widget__close-icon" />
            </button>
          </header>

          <div className="chat-widget__body" aria-busy={loading}>
            {messages.length === 0 ? (
              <>
                <div className="chat-widget__welcome">
                  {t.chatWidgetWelcome}
                  <div className="chat-widget__topics">{t.chatWidgetTopics}</div>
                </div>

                <div className="chat-widget__chips">
                  <button
                    className="chat-widget__chip"
                    type="button"
                    onClick={() =>
                      handleSend(t.chatPromptPhuQuoc)
                    }
                  >
                    {t.chatWidgetChipPhuQuoc}
                  </button>
                  <button
                    className="chat-widget__chip"
                    type="button"
                    onClick={() =>
                      handleSend(t.chatPromptFamily)
                    }
                  >
                    {t.chatWidgetChipFamily}
                  </button>
                </div>
              </>
            ) : (
              <div
                ref={threadRef}
                className="chat-widget__thread"
                onScroll={handleThreadScroll}
              >
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`chat-widget__msg chat-widget__msg--${msg.sender}`}
                  >
                    <div className="chat-widget__msg-bubble">
                      {msg.isStreaming && !msg.text ? (
                        <span className="chat-widget__stream-status" role="status">
                          {streamStatusLabel(language, msg.streamStatus)}
                        </span>
                      ) : msg.sender === 'user' || msg.isStreaming || msg.isError ? (
                        <RichMessage text={msg.text} isUser={msg.sender === 'user'} />
                      ) : (
                        <StructuredMessage
                          text={msg.text}
                          sources={msg.sources}
                          showActions={false}
                        />
                      )}
                      {msg.isStreaming && msg.text && (
                        <span className="chat-widget__stream-cursor" aria-hidden="true" />
                      )}
                      <span className="chat-widget__msg-time">{msg.timestamp}</span>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          <form
            className={`chat-widget__form chat-widget__form--${isComposerExpanded ? 'expanded' : 'compact'}`}
            onSubmit={handleQuickSend}
          >
            <textarea
              ref={inputRef}
              className="chat-widget__input"
              rows={1}
              placeholder={t.chatWidgetPlaceholder}
              value={quickInput}
              onChange={(event) => setQuickInput(event.target.value)}
              onFocus={handleInputFocus}
              onBlur={handleInputBlur}
              onKeyDown={handleInputKeyDown}
              disabled={loading}
            />
            {loading ? (
              <button
                className="chat-widget__send chat-widget__send--stop"
                type="button"
                title={stopGeneratingLabel(language)}
                aria-label={stopGeneratingLabel(language)}
                onClick={stopStreaming}
              >
                <Square className="chat-widget__send-icon" />
              </button>
            ) : (
              <button className="chat-widget__send" type="submit" disabled={!quickInput.trim()}>
                <Send className="chat-widget__send-icon" />
              </button>
            )}
          </form>

          <button
            className="chat-widget__full-chat"
            type="button"
            onClick={() => {
              abortControllerRef.current?.abort()
              setIsOpen(false)
              navigate('/chat')
            }}
          >
            {t.chatWidgetOpenFull}
          </button>
        </section>
      )}
    </div>
  )
}

export default ChatWidget
