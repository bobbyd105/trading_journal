import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '../api/client.js';
import { emptyReview, reviewToForm, toReviewPayload } from '../domain/reviews.js';

const reviewStatuses = ['not_started', 'in_progress', 'complete'];
const followedPlaybookOptions = ['yes', 'partial', 'no', 'not_applicable'];
const scoreFields = [
  ['setup_quality_score', 'Setup quality'],
  ['entry_quality_score', 'Entry quality'],
  ['exit_quality_score', 'Exit quality'],
  ['risk_management_score', 'Risk management'],
  ['discipline_score', 'Discipline'],
];

function TradeReviewList({ emptyText, onSelectTrade, selectedTradeId, title, trades }) {
  return (
    <section className="metadata-card">
      <h3>{title}</h3>
      <div className="card-list compact-list">
        {trades.map((trade) => (
          <button
            key={trade.id}
            className={trade.id === selectedTradeId ? 'list-button active' : 'list-button'}
            type="button"
            onClick={() => onSelectTrade(trade)}
          >
            <strong>{trade.symbol}</strong>
            <span>{trade.direction} · {trade.status} · P&amp;L {trade.pnl ?? '—'}</span>
          </button>
        ))}
        {trades.length === 0 ? <p className="muted">{emptyText}</p> : null}
      </div>
    </section>
  );
}

function ReviewForm({ form, isEditing, onChange, onDelete, onSubmit, selectedTrade }) {
  function setField(field, value) {
    onChange({ ...form, [field]: value });
  }

  return (
    <form className="crud-form" onSubmit={onSubmit}>
      <div className="detail-header">
        <div>
          <h3>{isEditing ? 'Edit review' : 'Create review'}</h3>
          <p className="muted">{selectedTrade ? `Linked trade: ${selectedTrade.symbol}` : 'Select a trade to review.'}</p>
        </div>
        {isEditing ? <button className="danger" type="button" onClick={onDelete}>Delete review</button> : null}
      </div>

      <div className="form-grid">
        <label>
          Review status
          <select value={form.review_status} onChange={(event) => setField('review_status', event.target.value)}>
            {reviewStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </label>
        <label>
          Followed playbook
          <select value={form.followed_playbook} onChange={(event) => setField('followed_playbook', event.target.value)}>
            {followedPlaybookOptions.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </label>
        <label>
          Reviewed at
          <input type="datetime-local" value={form.reviewed_at || ''} onChange={(event) => setField('reviewed_at', event.target.value)} />
        </label>
      </div>

      <div className="form-grid">
        {scoreFields.map(([field, label]) => (
          <label key={field}>
            {label} (1-5)
            <input min="1" max="5" type="number" value={form[field]} onChange={(event) => setField(field, event.target.value)} />
          </label>
        ))}
      </div>

      <label>
        Summary
        <textarea value={form.summary} onChange={(event) => setField('summary', event.target.value)} />
      </label>
      <div className="form-grid">
        <label>
          What went well
          <textarea value={form.what_went_well} onChange={(event) => setField('what_went_well', event.target.value)} />
        </label>
        <label>
          What to improve
          <textarea value={form.what_to_improve} onChange={(event) => setField('what_to_improve', event.target.value)} />
        </label>
      </div>
      <label>
        Lesson learned
        <textarea value={form.lesson_learned} onChange={(event) => setField('lesson_learned', event.target.value)} />
      </label>

      <button disabled={!selectedTrade} type="submit">{isEditing ? 'Update review' : 'Create review'}</button>
    </form>
  );
}

function ReviewsPage({ onDataChanged, onMessage }) {
  const [needsReview, setNeedsReview] = useState([]);
  const [reviewedTrades, setReviewedTrades] = useState([]);
  const [selectedTrade, setSelectedTrade] = useState(null);
  const [selectedReviewId, setSelectedReviewId] = useState(null);
  const [reviewForm, setReviewForm] = useState(emptyReview);

  const selectedTradeId = selectedTrade?.id || null;
  const selectedReviewedTrade = useMemo(
    () => reviewedTrades.find((trade) => trade.id === selectedTradeId) || null,
    [reviewedTrades, selectedTradeId],
  );

  async function refreshReviews(nextSelectedTrade = selectedTrade) {
    const [needsReviewData, reviewedTradeData] = await Promise.all([
      apiRequest('/trades/reviews/needs-review'),
      apiRequest('/trades/reviews/reviewed'),
    ]);
    setNeedsReview(needsReviewData);
    setReviewedTrades(reviewedTradeData);

    const stillSelected = [...needsReviewData, ...reviewedTradeData].find((trade) => trade.id === nextSelectedTrade?.id);
    if (!stillSelected) {
      setSelectedTrade(null);
      setSelectedReviewId(null);
      setReviewForm(emptyReview);
    }
  }

  useEffect(() => {
    refreshReviews(null).catch((error) => onMessage(error.message));
  }, []);

  async function handleSelectTrade(trade) {
    setSelectedTrade(trade);
    if (trade.review) {
      setSelectedReviewId(trade.review.id);
      setReviewForm(reviewToForm(trade.review));
      return;
    }

    const review = await apiRequest(`/trades/${trade.id}/review`).catch((error) => {
      if (error.message === 'review not found') {
        return null;
      }
      throw error;
    });
    setSelectedReviewId(review?.id || null);
    setReviewForm(reviewToForm(review));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!selectedTrade) {
      return;
    }
    const payload = toReviewPayload(reviewForm);
    const path = selectedReviewId ? `/reviews/${selectedReviewId}` : `/trades/${selectedTrade.id}/review`;
    const method = selectedReviewId ? 'PUT' : 'POST';
    const saved = await apiRequest(path, { method, body: JSON.stringify(payload) });
    setSelectedReviewId(saved.id);
    setReviewForm(reviewToForm(saved));
    onMessage(`Review saved for ${selectedTrade.symbol}`);
    await refreshReviews(selectedTrade);
    await onDataChanged();
  }

  async function handleDelete() {
    if (!selectedReviewId) {
      return;
    }
    await apiRequest(`/reviews/${selectedReviewId}`, { method: 'DELETE' });
    onMessage('Review deleted');
    setSelectedReviewId(null);
    setReviewForm(emptyReview);
    await refreshReviews(selectedTrade);
    await onDataChanged();
  }

  return (
    <section id="reviews" className="panel">
      <p className="eyebrow">Phase 3 MVP</p>
      <h2>Reviews</h2>
      <p>Review closed trades, capture lessons, and mark completed reviews without adding analytics or psychology workflows.</p>
      <div className="detail-layout">
        <div className="card-list">
          <TradeReviewList
            emptyText="No closed trades are waiting for review."
            onSelectTrade={handleSelectTrade}
            selectedTradeId={selectedTradeId}
            title="Needs Review"
            trades={needsReview}
          />
          <TradeReviewList
            emptyText="No completed reviews yet."
            onSelectTrade={handleSelectTrade}
            selectedTradeId={selectedTradeId}
            title="Reviewed"
            trades={reviewedTrades}
          />
        </div>
        <ReviewForm
          form={reviewForm}
          isEditing={Boolean(selectedReviewId || selectedReviewedTrade?.review)}
          onChange={setReviewForm}
          onDelete={handleDelete}
          onSubmit={handleSubmit}
          selectedTrade={selectedTrade}
        />
      </div>
    </section>
  );
}

export default ReviewsPage;
