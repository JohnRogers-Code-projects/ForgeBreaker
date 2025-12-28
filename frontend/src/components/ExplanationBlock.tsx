import { useState } from 'react'

interface ExplanationBlockProps {
  summary: string
  conditional?: string  // Renamed from 'uncertainty' - what changes this interpretation
  assumptions?: string[]
  compact?: boolean
}

export function ExplanationBlock({
  summary,
  conditional,
  assumptions,
  compact = false,
}: ExplanationBlockProps) {
  const [expanded, setExpanded] = useState(false)
  const hasDetails = conditional || (assumptions && assumptions.length > 0)

  if (compact) {
    return (
      <div
        className="flex items-start gap-2 text-sm"
        style={{ color: 'var(--color-text-secondary)' }}
      >
        <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
          ?
        </span>
        <span>{summary}</span>
      </div>
    )
  }

  return (
    <div
      className="rounded p-3"
      style={{
        backgroundColor: 'var(--color-bg-elevated)',
        border: '1px solid var(--color-border)',
      }}
    >
      <div
        className={`flex items-start gap-2 ${hasDetails ? 'cursor-pointer' : ''}`}
        onClick={() => hasDetails && setExpanded(!expanded)}
      >
        <span
          className="text-xs font-medium mt-0.5"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          Note
        </span>
        <div className="flex-1">
          <p
            className="text-sm leading-relaxed"
            style={{ color: 'var(--color-text-primary)' }}
          >
            {summary}
          </p>
        </div>
        {hasDetails && (
          <span
            className="text-xs"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            {expanded ? '−' : '+'}
          </span>
        )}
      </div>

      {expanded && hasDetails && (
        <div
          className="mt-3 pt-3 border-t space-y-2"
          style={{ borderColor: 'var(--color-border)' }}
        >
          {conditional && (
            <div className="flex items-start gap-2">
              <span
                className="text-xs font-medium"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Given:
              </span>
              <p
                className="text-sm"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                {conditional}
              </p>
            </div>
          )}
          {assumptions && assumptions.length > 0 && (
            <div className="flex items-start gap-2">
              <span
                className="text-xs font-medium"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Depends on:
              </span>
              <div className="flex flex-wrap gap-1">
                {assumptions.map((assumption, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-1.5 py-0.5 rounded"
                    style={{
                      backgroundColor: 'var(--color-bg-surface)',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    {assumption}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Inline explanation for use next to metrics
 */
export function InlineExplanation({ text }: { text: string }) {
  return (
    <span
      className="text-xs ml-1"
      style={{ color: 'var(--color-text-secondary)' }}
      title={text}
    >
      *
    </span>
  )
}

/**
 * Tooltip-style explanation that appears on hover
 */
export function ExplanationTooltip({
  children,
  summary,
  conditional,
}: {
  children: React.ReactNode
  summary: string
  conditional?: string
}) {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        {children}
      </div>
      {showTooltip && (
        <div
          className="absolute z-50 w-64 p-3 rounded-lg shadow-lg text-sm"
          style={{
            backgroundColor: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border)',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: '8px',
          }}
        >
          <p style={{ color: 'var(--color-text-primary)' }}>{summary}</p>
          {conditional && (
            <p
              className="mt-2 text-xs"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Given: {conditional}
            </p>
          )}
          <div
            className="absolute w-2 h-2 rotate-45"
            style={{
              backgroundColor: 'var(--color-bg-elevated)',
              borderRight: '1px solid var(--color-border)',
              borderBottom: '1px solid var(--color-border)',
              bottom: '-5px',
              left: '50%',
              transform: 'translateX(-50%)',
            }}
          />
        </div>
      )}
    </div>
  )
}
