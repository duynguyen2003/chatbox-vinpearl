import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Bot,
  Headphones,
  History,
  Maximize2,
  Minimize2,
  RotateCcw,
  Send,
  ShieldAlert,
  Square,
  User,
} from 'lucide-react'
import ChatHistorySidebar from '../components/ChatHistorySidebar'
import HotelCard from '../components/HotelCard'
import RichMessage from '../components/RichMessage'
import StructuredMessage from '../components/StructuredMessage'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import {
  clearStoredMessages,
  fetchChatSessionMessages,
  fetchChatSessions,
  getChatSessionId,
  loadStoredMessages,
  saveStoredMessages,
  setChatSessionId,
  startNewChatSession,
  streamChatMessage,
} from '../services/api'
import { streamStatusLabel } from '../services/chatStatus'
import '../styles/pages/Chatbot.css'

const CHAT_DRAFT_KEY = 'vinpearl_chat_draft_v2'

// Only frontend-generated/system messages should follow the current UI locale.
// Real user/assistant conversation history must stay in the language it was sent in.
const LOCAL_SYSTEM_MESSAGE_KEYS = {
  'msg-welcome': 'chatbotWelcome',
  'msg-reset': 'chatbotReset',
  'msg-logout': 'chatbotWelcome',
  'msg-empty-history': 'chatbotWelcome',
  'msg-login': 'chatbotWelcome',
}

function localSystemMessageKey(message) {
  if (message?.localizationKey) return message.localizationKey
  if (LOCAL_SYSTEM_MESSAGE_KEYS[message?.id]) return LOCAL_SYSTEM_MESSAGE_KEYS[message.id]
  if (message?.isError || String(message?.id || '').startsWith('error-')) return 'assistantUnavailable'
  if (String(message?.id || '').startsWith('err-')) return 'chatError'
  return null
}

function localizeSystemMessages(messages, translations, language) {
  let changed = false
  const nextMessages = messages.map((message) => {
    const localizationKey = localSystemMessageKey(message)
    if (!localizationKey || !translations[localizationKey]) return message

    const nextText = translations[localizationKey]
    if (
      message.text === nextText
      && message.language === language
      && message.localizationKey === localizationKey
    ) {
      return message
    }

    changed = true
    return {
      ...message,
      text: nextText,
      language,
      localizationKey,
    }
  })

  return changed ? nextMessages : messages
}

function displayTime(value) {
  const date = value ? new Date(value) : new Date()
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function historyMessageToUi(message) {
  return {
    id: `history-${message.id}`,
    sender: message.role === 'user' ? 'user' : 'assistant',
    text: message.content,
    timestamp: displayTime(message.created_at),
    language: message.language || 'unknown',
    route: message.route,
    ticketId: message.ticket_id,
    sources: [],
    relatedHotels: [],
  }
}

function loadStoredDraft() {
  try {
    return sessionStorage.getItem(CHAT_DRAFT_KEY) || ''
  } catch {
    return ''
  }
}

function saveStoredDraft(value) {
  try {
    sessionStorage.setItem(CHAT_DRAFT_KEY, value)
  } catch {
    // Ignore storage failures; chat still works without draft persistence.
  }
}

function clearStoredDraft() {
  try {
    sessionStorage.removeItem(CHAT_DRAFT_KEY)
  } catch {
    // Ignore storage failures.
  }
}

function historyButtonLabel(language) {
  return {
    en: 'History',
    vi: 'Lịch sử',
    ko: '기록',
    ja: '履歴',
    zh: '记录',
  }[language] || 'History'
}

function newChatLabel(language) {
  return {
    en: 'New chat',
    vi: 'Chat mới',
    ko: '새 채팅',
    ja: '新しいチャット',
    zh: '新对话',
  }[language] || 'New chat'
}

function closeHistoryLabel(language) {
  return {
    en: 'Close chat history',
    vi: 'Đóng lịch sử chat',
    ko: '채팅 기록 닫기',
    ja: 'チャット履歴を閉じる',
    zh: '关闭聊天记录',
  }[language] || 'Close chat history'
}

function fullscreenLabel(language, active) {
  const labels = {
    en: { open: 'Open fullscreen chat', close: 'Exit fullscreen chat' },
    vi: { open: 'Mở chat toàn màn hình', close: 'Thoát toàn màn hình' },
    ko: { open: '전체 화면 채팅 열기', close: '전체 화면 채팅 닫기' },
    ja: { open: 'チャットを全画面で開く', close: '全画面チャットを閉じる' },
    zh: { open: '打开全屏聊天', close: '退出全屏聊天' },
  }
  return labels[language]?.[active ? 'close' : 'open'] || labels.en[active ? 'close' : 'open']
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

function Chatbot() {
  const { language, t } = useLanguage()
  const { user, loading: authLoading } = useAuth()
  const [searchParams] = useSearchParams()
  const initialPrompt = searchParams.get('prompt') || ''
  const handledPromptRef = useRef(null)
  const messagesContainerRef = useRef(null)
  const inputRef = useRef(null)
  const previousUserIdRef = useRef(undefined)
  const abortControllerRef = useRef(null)
  const shouldAutoScrollRef = useRef(true)

  function createSystemMessage(id, localizationKey = 'chatbotWelcome') {
    return {
      id,
      sender: 'assistant',
      text: t[localizationKey] || t.chatbotWelcome,
      timestamp: displayTime(),
      language,
      localizationKey,
    }
  }

  const [messages, setMessages] = useState(() => {
    const storedMessages = loadStoredMessages()
    if (Array.isArray(storedMessages) && storedMessages.length > 0) {
      return storedMessages
    }
    return [createSystemMessage('msg-welcome')]
  })
  const [input, setInput] = useState(() => loadStoredDraft())
  const [loading, setLoading] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(() => getChatSessionId())
  const [conversationReady, setConversationReady] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)

  useEffect(() => () => abortControllerRef.current?.abort(), [])

  useEffect(() => {
    document.body.classList.toggle('chatbot-fullscreen', isFullscreen)
    return () => document.body.classList.remove('chatbot-fullscreen')
  }, [isFullscreen])

  useEffect(() => {
    if (!isFullscreen) return undefined

    function handleFullscreenEscape(event) {
      if (event.key === 'Escape') setIsFullscreen(false)
    }

    window.addEventListener('keydown', handleFullscreenEscape)
    return () => window.removeEventListener('keydown', handleFullscreenEscape)
  }, [isFullscreen])

  useEffect(() => {
    const messagesContainer = messagesContainerRef.current
    if (!messagesContainer || !shouldAutoScrollRef.current) return

    messagesContainer.scrollTo({
      top: messagesContainer.scrollHeight,
      behavior: messages.length > 1 ? 'smooth' : 'auto',
    })
  }, [messages, loading])

  function handleMessagesScroll(event) {
    const element = event.currentTarget
    const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight
    shouldAutoScrollRef.current = distanceFromBottom < 96
  }

  // While the assistant is responding, the input is intentionally disabled.
  // Restore focus as soon as it becomes available again so users can continue
  // the conversation without an extra mouse click.
  useEffect(() => {
    if (loading || !conversationReady) return undefined

    const frame = window.requestAnimationFrame(() => {
      inputRef.current?.focus({ preventScroll: true })
    })

    return () => window.cancelAnimationFrame(frame)
  }, [loading, conversationReady])

  // Keep only local/system UI messages synchronized with the selected language.
  // This also upgrades old sessionStorage messages created before localizationKey existed.
  useEffect(() => {
    setMessages((current) => localizeSystemMessages(current, t, language))
  }, [language, t.chatbotWelcome, t.chatbotReset, t.assistantUnavailable, t.chatError])

  // Guest chats may be restored from sessionStorage. Authenticated chats are
  // restored from PostgreSQL instead, which prevents account A's visible chat
  // content from leaking into account B on a shared browser.
  useEffect(() => {
    if (authLoading) return
    if (!user) saveStoredMessages(messages)
  }, [authLoading, messages, user])

  useEffect(() => {
    saveStoredDraft(input)
  }, [input])

  useEffect(() => {
    if (authLoading) return undefined

    let cancelled = false
    setConversationReady(false)

    async function syncConversationForAuthState() {
      const previousUserId = previousUserIdRef.current
      const nextUserId = user?.id || null
      previousUserIdRef.current = nextUserId

      if (!user) {
        setSessions([])
        setHistoryOpen(false)

        if (previousUserId) {
          // Logging out must never leave the previous account's session ID or
          // messages active for the next person using this browser.
          clearStoredMessages()
          clearStoredDraft()
          const freshSessionId = startNewChatSession()
          setActiveSessionId(freshSessionId)
          setMessages([createSystemMessage('msg-logout')])
          setInput('')
        } else {
          setActiveSessionId(getChatSessionId())
        }

        if (!cancelled) setConversationReady(true)
        return
      }

      setHistoryLoading(true)
      try {
        const rows = await fetchChatSessions()
        if (cancelled) return
        setSessions(rows)

        const currentSessionId = getChatSessionId()
        const currentSessionExists = rows.some((item) => item.id === currentSessionId)

        if (currentSessionExists) {
          const payload = await fetchChatSessionMessages(currentSessionId)
          if (cancelled) return
          const restored = (payload.messages || []).map(historyMessageToUi)
          setActiveSessionId(currentSessionId)
          setMessages(
            restored.length
              ? restored
              : [createSystemMessage('msg-empty-history')],
          )
          clearStoredMessages()
        } else if (previousUserId === null) {
          // The user has just logged in during this SPA session. Keep a guest
          // conversation visible; the next message will let the backend claim
          // that anonymous session for this authenticated user.
          setActiveSessionId(currentSessionId)
        } else {
          // First authenticated load with an unknown/stale session, or a direct
          // account switch: rotate IDs to avoid a 403 against another user's chat.
          clearStoredMessages()
          const freshSessionId = startNewChatSession()
          setActiveSessionId(freshSessionId)
          setMessages([createSystemMessage('msg-login')])
        }
      } catch (error) {
        if (!cancelled) console.error('Could not load chat history:', error)
      } finally {
        if (!cancelled) {
          setHistoryLoading(false)
          setConversationReady(true)
        }
      }
    }

    syncConversationForAuthState()
    return () => {
      cancelled = true
    }
  }, [authLoading, user?.id])

  useEffect(() => {
    if (!conversationReady) return

    const promptAlreadyInHistory = messages.some(
      (message) => message.sender === 'user' && message.text === initialPrompt,
    )

    if (
      initialPrompt
      && handledPromptRef.current !== initialPrompt
      && !promptAlreadyInHistory
    ) {
      handledPromptRef.current = initialPrompt
      handleSendPrompt(initialPrompt)
    }
  }, [conversationReady, initialPrompt, messages])

  async function refreshSessions() {
    if (!user) return
    try {
      const rows = await fetchChatSessions()
      setSessions(rows)
    } catch (error) {
      console.error('Could not refresh chat history:', error)
    }
  }

  async function loadHistorySession(sessionId) {
    if (!user || historyLoading) return

    abortControllerRef.current?.abort()
    setHistoryLoading(true)
    try {
      const payload = await fetchChatSessionMessages(sessionId)
      const restored = (payload.messages || []).map(historyMessageToUi)
      setChatSessionId(sessionId)
      setActiveSessionId(sessionId)
      shouldAutoScrollRef.current = true
      setMessages(
        restored.length
          ? restored
          : [createSystemMessage('msg-empty-history')],
      )
      clearStoredMessages()
      setHistoryOpen(false)
    } catch (error) {
      console.error('Could not load selected chat session:', error)
    } finally {
      setHistoryLoading(false)
    }
  }

  async function handleSendPrompt(promptText) {
    if (!promptText.trim() || loading || !conversationReady) return

    const userMessage = {
      id: `user-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      sender: 'user',
      text: promptText,
      timestamp: displayTime(),
      language,
    }

    const assistantId = `assistant-stream-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
    const controller = new AbortController()
    abortControllerRef.current?.abort()
    abortControllerRef.current = controller
    const streamingMessage = {
      id: assistantId,
      sender: 'assistant',
      text: '',
      timestamp: displayTime(),
      language,
      isStreaming: true,
      streamStatus: 'analyzing',
      sources: [],
      relatedHotels: [],
    }

    shouldAutoScrollRef.current = true
    setMessages((current) => [...current, userMessage, streamingMessage])
    setInput('')
    clearStoredDraft()
    setLoading(true)

    try {
      const aiResponse = await streamChatMessage(promptText, language, {
        signal: controller.signal,
        sessionId: activeSessionId,
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
          ? { ...aiResponse, id: assistantId, isStreaming: false }
          : message
      )))
      if (aiResponse.sessionId) {
        setActiveSessionId(aiResponse.sessionId)
      }
      if (user) await refreshSessions()
    } catch (error) {
      if (error?.name === 'AbortError') {
        setMessages((current) => current.flatMap((message) => {
          if (message.id !== assistantId) return [message]
          return message.text ? [{ ...message, isStreaming: false, wasStopped: true }] : []
        }))
      } else {
        console.error('Chat request failed:', error)
        setMessages((current) => current.map((message) => (
          message.id === assistantId
            ? {
                ...message,
                text: message.text || t.assistantUnavailable,
                localizationKey: message.text ? undefined : 'assistantUnavailable',
                isStreaming: false,
                isError: !message.text,
                streamError: true,
                errorDetail: error instanceof Error ? error.message : String(error),
              }
            : message
        )))
      }
    } finally {
      if (abortControllerRef.current === controller) abortControllerRef.current = null
      setLoading(false)
    }
  }

  function stopStreaming() {
    abortControllerRef.current?.abort()
  }

  function handleFormSubmit(event) {
    event.preventDefault()
    handleSendPrompt(input)
  }

  function startFreshConversation() {
    abortControllerRef.current?.abort()
    const sessionId = startNewChatSession()
    setActiveSessionId(sessionId)
    setHistoryOpen(false)
    clearStoredDraft()
    setInput('')
    shouldAutoScrollRef.current = true
    setMessages([createSystemMessage('msg-reset', 'chatbotReset')])
  }

  return (
    <main className={`chatbot-page${isFullscreen ? ' chatbot-page--fullscreen' : ''}`}>
      {user && historyOpen && (
        <button
          className="chatbot-page__history-backdrop"
          type="button"
          aria-label={closeHistoryLabel(language)}
          onClick={() => setHistoryOpen(false)}
        />
      )}

      <div
        className={`chatbot-page__shell ${
          user ? 'chatbot-page__shell--with-history' : 'chatbot-page__shell--solo'
        }`}
      >
        {user && (
          <ChatHistorySidebar
            sessions={sessions}
            activeSessionId={activeSessionId}
            loading={historyLoading}
            open={historyOpen}
            language={language}
            onClose={() => setHistoryOpen(false)}
            onNewConversation={startFreshConversation}
            onSelectSession={loadHistorySession}
          />
        )}

        <div className="chatbot-page__container">
          <section className="chatbot-page__header">
            <div className="chatbot-page__identity">
              <div className="chatbot-page__avatar chatbot-page__avatar--brand">
                <Bot className="chatbot-page__avatar-icon chatbot-page__avatar-icon--large" />
              </div>
              <div>
                <div className="chatbot-page__title-row">
                  <h1 className="chatbot-page__title">VinTravel AI</h1>
                </div>
                <p className="chatbot-page__subtitle">{t.chatbotSubtitle}</p>
              </div>
            </div>

            <div className="chatbot-page__header-actions">
              {user && (
                <button
                  className="chatbot-page__history-toggle"
                  type="button"
                  onClick={() => setHistoryOpen(true)}
                >
                  <History className="chatbot-page__action-icon" />
                  <span>{historyButtonLabel(language)}</span>
                </button>
              )}
              <button
                className="chatbot-page__reset"
                type="button"
                title={t.resetConversation}
                onClick={startFreshConversation}
              >
                <RotateCcw className="chatbot-page__action-icon" />
                <span>{user ? newChatLabel(language) : t.clearChat}</span>
              </button>
              <button
                className="chatbot-page__fullscreen"
                type="button"
                title={fullscreenLabel(language, isFullscreen)}
                aria-label={fullscreenLabel(language, isFullscreen)}
                aria-pressed={isFullscreen}
                onClick={() => setIsFullscreen((active) => !active)}
              >
                {isFullscreen ? <Minimize2 className="chatbot-page__action-icon" /> : <Maximize2 className="chatbot-page__action-icon" />}
              </button>
              <Link className="chatbot-page__support-link" to="/support">
                <Headphones className="chatbot-page__action-icon" />
                <span>{t.createTicket}</span>
              </Link>
            </div>
          </section>

          <section
            ref={messagesContainerRef}
            className="chatbot-page__messages"
            aria-label={t.chatMessages}
            onScroll={handleMessagesScroll}
          >
            {messages.map((message) => (
              <article
                className={`chatbot-page__message-row ${
                  message.sender === 'user' ? 'chatbot-page__message-row--user' : ''
                }`}
                key={message.id}
              >
                <div
                  className={`chatbot-page__avatar ${
                    message.sender === 'user'
                      ? 'chatbot-page__avatar--user'
                      : 'chatbot-page__avatar--assistant'
                  }`}
                >
                  {message.sender === 'user' ? (
                    <User className="chatbot-page__avatar-icon" />
                  ) : (
                    <Bot className="chatbot-page__avatar-icon" />
                  )}
                </div>

                <div className="chatbot-page__message-content">
                  <div
                    className={`chatbot-page__bubble ${
                      message.sender === 'user'
                        ? 'chatbot-page__bubble--user'
                        : message.isError
                          ? 'chatbot-page__bubble--error'
                          : 'chatbot-page__bubble--assistant'
                    }`}
                  >
                    {message.isStreaming && !message.text ? (
                      <span className="chatbot-page__stream-status" role="status">
                        {streamStatusLabel(language, message.streamStatus)}
                      </span>
                    ) : message.sender === 'user' || message.isError || message.isStreaming ? (
                      <RichMessage text={message.text} isUser={message.sender === 'user'} />
                    ) : (
                      <StructuredMessage text={message.text} sources={message.sources} />
                    )}
                    {message.isStreaming && message.text && (
                      <span className="chatbot-page__stream-cursor" aria-hidden="true" />
                    )}
                    <span className="chatbot-page__timestamp">{message.timestamp}</span>
                  </div>

                  {message.ticketId && (
                    <div className="chatbot-page__ticket" role="status">
                      <strong>{t.supportTicket}:</strong>{' '}
                      <span>{message.ticketId}</span>
                    </div>
                  )}

                  {message.relatedHotels && message.relatedHotels.length > 0 && (
                    <div className="chatbot-page__related-hotels">
                      {message.relatedHotels.map((hotel, index) => (
                        <HotelCard key={`${message.id}-${hotel.id}-${index}`} hotel={hotel} />
                      ))}
                    </div>
                  )}
                </div>
              </article>
            ))}

          </section>

          <form className="chatbot-page__form" onSubmit={handleFormSubmit}>
            <input
              ref={inputRef}
              className="chatbot-page__input"
              type="text"
              placeholder={t.chatbotPlaceholder}
              value={input}
              disabled={loading || !conversationReady}
              onChange={(event) => setInput(event.target.value)}
            />
            {loading ? (
              <button
                className="chatbot-page__send chatbot-page__send--stop"
                type="button"
                title={stopGeneratingLabel(language)}
                aria-label={stopGeneratingLabel(language)}
                onClick={stopStreaming}
              >
                <Square className="chatbot-page__send-icon" />
              </button>
            ) : (
              <button
                className="chatbot-page__send"
                type="submit"
                disabled={!conversationReady || !input.trim()}
              >
                <Send className="chatbot-page__send-icon" />
              </button>
            )}
          </form>

          <div className="chatbot-page__escalation">
            <p>
              <ShieldAlert className="chatbot-page__escalation-icon" />
              <span>{t.chatbotEscalation}</span>
              <Link to="/support">{t.chatbotSubmitTicket}</Link>
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}

export default Chatbot
