import { useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext'
import '../styles/components/StructuredMessage.css'

function decodeSourceValue(value) {
  let decoded = String(value || '').trim()
  for (let attempt = 0; attempt < 2 && decoded; attempt += 1) {
    try {
      const next = decodeURIComponent(decoded)
      if (next === decoded) break
      decoded = next
    } catch {
      break
    }
  }
  return decoded
}

function parseUrlLike(value) {
  const decoded = decodeSourceValue(value)
  if (!decoded) return null

  let candidate = decoded
  if (candidate.startsWith('//')) candidate = `https:${candidate}`
  else if (!/^[a-z][a-z\d+.-]*:\/\//i.test(candidate) && /^[\w.-]+\.[a-z]{2,}(?:[/:?#]|$)/i.test(candidate)) {
    candidate = `https://${candidate}`
  }

  try {
    const url = new URL(candidate)
    if (!url.hostname) return null
    return {
      href: url.href,
      label: url.hostname.replace(/^www\./, ''),
    }
  } catch {
    return null
  }
}

function shortenLabel(value, fallback) {
  const label = decodeSourceValue(value) || fallback
  if (label.length <= 72) return label
  return `${label.slice(0, 69)}…`
}

function normalizeSource(source, fallbackLabel) {
  const path = decodeSourceValue(source?.path)
  const sourceFile = decodeSourceValue(source?.source_file)
  const pathUrl = parseUrlLike(path)
  const fileUrl = parseUrlLike(sourceFile)

  if (pathUrl) return { href: pathUrl.href, label: pathUrl.label, title: pathUrl.href }
  if (fileUrl) return { href: fileUrl.href, label: fileUrl.label, title: fileUrl.href }

  return {
    href: path || null,
    label: shortenLabel(sourceFile, fallbackLabel),
    title: path || sourceFile || fallbackLabel,
  }
}

/**
 * SourcePills shows source citations as inline pills.
 * Displays up to `maxVisible` directly, with a "+N more" expander.
 */
export function SourcePills({ sources }) {
  const { t } = useLanguage()
  const [expanded, setExpanded] = useState(false)
  const maxVisible = 3

  if (!sources || sources.length === 0) return null

  const visible = expanded ? sources : sources.slice(0, maxVisible)
  const hiddenCount = sources.length - maxVisible
  const sourcesLabel = (t.aiSources || t.sourcesLabel || 'Nguồn').replace(/:$/, '')
  const moreLabel = t.moreSourcesCount
    ? t.moreSourcesCount.replace('{{count}}', hiddenCount)
    : 'nguồn khác'

  return (
    <div className="source-pills">
      <span className="source-pills__label">
        {sourcesLabel}
      </span>
      <div className="source-pills__list">
        {visible.map((source, idx) => {
          const normalized = normalizeSource(source, sourcesLabel)

          if (normalized.href) {
            return (
              <a
                key={`src-${idx}`}
                className="source-pills__pill source-pills__pill--link"
                href={normalized.href}
                target="_blank"
                rel="noopener noreferrer"
                title={normalized.title}
              >
                <span>{normalized.label}</span>
                <ExternalLink className="source-pills__ext-icon" />
              </a>
            )
          }

          return (
            <span key={`src-${idx}`} className="source-pills__pill" title={normalized.title}>
              <span>{normalized.label}</span>
            </span>
          )
        })}

        {!expanded && hiddenCount > 0 && (
          <button
            className="source-pills__more"
            type="button"
            onClick={() => setExpanded(true)}
          >
            +{hiddenCount} {moreLabel}
          </button>
        )}
      </div>
    </div>
  )
}

export default SourcePills
