/**
 * ApiErrorBanner — shown when an API call fails.
 * Detects network errors and shows a Tailscale hint when running as a PWA.
 */

const isStandalone = window.matchMedia('(display-mode: standalone)').matches;

function isNetworkError(msg: string): boolean {
  return (
    msg.includes('Failed to fetch') ||
    msg.includes('NetworkError') ||
    msg.includes('Load failed') ||
    msg.includes('Network request failed') ||
    msg.includes('fetch')
  );
}

interface Props {
  error: string;
  onRetry?: () => void;
}

export default function ApiErrorBanner({ error, onRetry }: Props) {
  const isNetwork = isNetworkError(error);

  if (isNetwork && isStandalone) {
    return (
      <div style={{
        background: '#1a1a2e', border: '1px solid #2e2e4e',
        borderRadius: '10px', padding: '24px', textAlign: 'center',
        marginTop: '2rem',
      }}>
        <div style={{ fontSize: '2rem', marginBottom: '12px' }}>📡</div>
        <div style={{ fontWeight: 600, marginBottom: '8px' }}>Mac not reachable</div>
        <div style={{ fontSize: '0.83rem', color: 'var(--txt-2)', lineHeight: 1.6, marginBottom: '16px' }}>
          This tab needs your Mac. Make sure:<br />
          <strong style={{ color: 'var(--txt)' }}>1.</strong> Tailscale is on on your iPhone<br />
          <strong style={{ color: 'var(--txt)' }}>2.</strong> Your Mac is awake<br />
          <strong style={{ color: 'var(--txt)' }}>3.</strong> The API URL is set in the sync panel
        </div>
        {onRetry && (
          <button onClick={onRetry} className="btn-primary" style={{ padding: '8px 20px', fontSize: '0.85rem' }}>
            Try again
          </button>
        )}
        <div style={{ fontSize: '0.75rem', color: 'var(--txt-2)', marginTop: '12px' }}>
          Or switch to <strong>My Vinyl</strong> to browse offline
        </div>
      </div>
    );
  }

  return (
    <div className="error-banner" style={{ marginTop: '1rem' }}>
      {error}
      {onRetry && (
        <button onClick={onRetry} style={{
          marginLeft: '12px', background: 'none', border: '1px solid currentColor',
          color: 'inherit', borderRadius: '4px', padding: '2px 10px',
          fontSize: '0.8rem', cursor: 'pointer',
        }}>
          Retry
        </button>
      )}
    </div>
  );
}
