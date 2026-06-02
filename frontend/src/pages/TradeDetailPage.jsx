function attachmentPreviewUrl(attachment) {
  if (!attachment?.id || !attachment.content_type?.startsWith('image/')) {
    return null;
  }
  return `/attachments/${attachment.id}/file`;
}

function ScreenshotMetadata({ title, attachment }) {
  const previewUrl = attachmentPreviewUrl(attachment);

  return (
    <article className="metadata-card screenshot-card">
      <h3>{title}</h3>
      {attachment ? (
        <>
          {previewUrl ? (
            <img alt={`${title} preview`} className="screenshot-preview" src={previewUrl} />
          ) : (
            <div className="screenshot-placeholder">No local image preview available.</div>
          )}
          <dl>
            <dt>File name</dt><dd>{attachment.file_name}</dd>
            <dt>File path</dt><dd>{attachment.file_path || '—'}</dd>
            <dt>Content type</dt><dd>{attachment.content_type || '—'}</dd>
            <dt>Notes</dt><dd>{attachment.notes || '—'}</dd>
          </dl>
        </>
      ) : <p className="muted">No screenshot captured.</p>}
    </article>
  );
}

function TradeDetailPage({ onEditTrade, trade }) {
  return (
    <section id="trade-detail" className="panel">
      <p className="eyebrow">Phase 4 Screenshot usability</p>
      <h2>Trade Detail</h2>
      {!trade ? <p className="muted">Select a trade to view its details.</p> : (
        <div className="detail-layout">
          <div>
            <div className="detail-header">
              <h3>{trade.symbol}</h3>
              <button type="button" onClick={() => onEditTrade(trade)}>Edit trade</button>
            </div>
            <dl className="detail-grid">
              <dt>Direction</dt><dd>{trade.direction}</dd>
              <dt>Status</dt><dd>{trade.status}</dd>
              <dt>Entry</dt><dd>{trade.entry_price ?? '—'}</dd>
              <dt>Exit</dt><dd>{trade.exit_price ?? '—'}</dd>
              <dt>Quantity</dt><dd>{trade.quantity ?? '—'}</dd>
              <dt>P&amp;L</dt><dd>{trade.pnl ?? '—'}</dd>
              <dt>Risk</dt><dd>{trade.risk ?? '—'}</dd>
              <dt>Playbook</dt><dd>{trade.playbook_name || '—'}</dd>
              <dt>Tags</dt><dd>{trade.tags?.map((tag) => tag.name).join(', ') || '—'}</dd>
              <dt>Notes</dt><dd>{trade.notes || '—'}</dd>
            </dl>
          </div>
          <div className="screenshot-grid">
            <ScreenshotMetadata title="Before screenshot" attachment={trade.before_screenshot} />
            <ScreenshotMetadata title="After screenshot" attachment={trade.after_screenshot} />
          </div>
        </div>
      )}
    </section>
  );
}

export default TradeDetailPage;
