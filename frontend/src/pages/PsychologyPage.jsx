import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '../api/client.js';

const emptyPsychologyForm = {
  confidence_score: 3,
  fear_score: 3,
  fomo_score: 3,
  discipline_score: 3,
  clarity_score: 3,
  notes: '',
};

const scoreFields = [
  ['confidence_score', 'Confidence'],
  ['fear_score', 'Fear'],
  ['fomo_score', 'FOMO'],
  ['discipline_score', 'Discipline'],
  ['clarity_score', 'Clarity'],
];

function formFromEntry(entry) {
  if (!entry) {
    return emptyPsychologyForm;
  }
  return {
    confidence_score: entry.confidence_score,
    fear_score: entry.fear_score,
    fomo_score: entry.fomo_score,
    discipline_score: entry.discipline_score,
    clarity_score: entry.clarity_score,
    notes: entry.notes || '',
  };
}

function toPsychologyPayload(form) {
  return {
    confidence_score: Number(form.confidence_score),
    fear_score: Number(form.fear_score),
    fomo_score: Number(form.fomo_score),
    discipline_score: Number(form.discipline_score),
    clarity_score: Number(form.clarity_score),
    notes: form.notes || null,
  };
}

function TradeList({ entriesByTradeId, onSelectTrade, title, trades }) {
  return (
    <div className="metadata-card">
      <h3>{title}</h3>
      <div className="card-list compact-list">
        {trades.map((trade) => {
          const entry = entriesByTradeId.get(trade.id);
          return (
            <button className="list-button" key={trade.id} type="button" onClick={() => onSelectTrade(trade.id)}>
              <strong>{trade.symbol} #{trade.id}</strong>
              <span>{trade.direction} · {trade.status}{entry ? ` · Discipline ${entry.discipline_score}/5` : ''}</span>
            </button>
          );
        })}
        {trades.length === 0 ? <p className="muted">Nothing to show.</p> : null}
      </div>
    </div>
  );
}

function PsychologyPage({ onDataChanged, onMessage, trades }) {
  const [entries, setEntries] = useState([]);
  const [selectedTradeId, setSelectedTradeId] = useState('');
  const [form, setForm] = useState(emptyPsychologyForm);

  const entriesByTradeId = useMemo(
    () => new Map(entries.map((entry) => [entry.trade_id, entry])),
    [entries],
  );

  const selectedTrade = trades.find((trade) => trade.id === Number(selectedTradeId)) || null;
  const selectedEntry = selectedTrade ? entriesByTradeId.get(selectedTrade.id) : null;
  const tradesWithPsychology = trades.filter((trade) => entriesByTradeId.has(trade.id));
  const tradesWithoutPsychology = trades.filter((trade) => !entriesByTradeId.has(trade.id));

  async function refreshPsychology() {
    const data = await apiRequest('/psychology');
    setEntries(data);
  }

  useEffect(() => {
    refreshPsychology().catch((error) => onMessage(error.message));
  }, []);

  useEffect(() => {
    if (selectedEntry) {
      setForm(formFromEntry(selectedEntry));
    } else {
      setForm(emptyPsychologyForm);
    }
  }, [selectedEntry]);

  async function handleSelectTrade(tradeId) {
    setSelectedTradeId(String(tradeId));
  }

  async function handleSave(event) {
    event.preventDefault();
    if (!selectedTrade) {
      onMessage('Select a trade before saving psychology notes.');
      return;
    }
    const method = selectedEntry ? 'PUT' : 'POST';
    await apiRequest(`/trades/${selectedTrade.id}/psychology`, {
      method,
      body: JSON.stringify(toPsychologyPayload(form)),
    });
    onMessage(`Saved psychology entry for ${selectedTrade.symbol}`);
    await refreshPsychology();
    await onDataChanged();
  }

  async function handleDelete() {
    if (!selectedTrade || !selectedEntry) {
      return;
    }
    await apiRequest(`/trades/${selectedTrade.id}/psychology`, { method: 'DELETE' });
    onMessage(`Deleted psychology entry for ${selectedTrade.symbol}`);
    setForm(emptyPsychologyForm);
    await refreshPsychology();
    await onDataChanged();
  }

  return (
    <section id="psychology" className="panel">
      <p className="eyebrow">Psychology V1</p>
      <h2>Psychology</h2>
      <p>Capture one lightweight psychology entry per trade. Scores use a simple 1-5 scale.</p>

      <div className="detail-layout">
        <TradeList
          entriesByTradeId={entriesByTradeId}
          onSelectTrade={handleSelectTrade}
          title="Trades without psychology"
          trades={tradesWithoutPsychology}
        />
        <TradeList
          entriesByTradeId={entriesByTradeId}
          onSelectTrade={handleSelectTrade}
          title="Trades with psychology"
          trades={tradesWithPsychology}
        />
      </div>

      <form className="crud-form" onSubmit={handleSave}>
        <h3>{selectedEntry ? 'Update psychology entry' : 'Add psychology entry'}</h3>
        <label>
          Trade
          <select value={selectedTradeId} onChange={(event) => handleSelectTrade(event.target.value)}>
            <option value="">Select a trade</option>
            {trades.map((trade) => (
              <option key={trade.id} value={trade.id}>{trade.symbol} #{trade.id} · {trade.direction} · {trade.status}</option>
            ))}
          </select>
        </label>

        <div className="form-grid">
          {scoreFields.map(([field, label]) => (
            <label key={field}>
              {label} score
              <select value={form[field]} onChange={(event) => setForm({ ...form, [field]: event.target.value })}>
                {[1, 2, 3, 4, 5].map((score) => <option key={score} value={score}>{score}</option>)}
              </select>
            </label>
          ))}
        </div>

        <label>
          Notes
          <textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
        </label>

        <div className="button-row">
          <button type="submit" disabled={!selectedTrade}>{selectedEntry ? 'Update entry' : 'Create entry'}</button>
          {selectedEntry ? <button className="danger" type="button" onClick={handleDelete}>Delete entry</button> : null}
        </div>
      </form>
    </section>
  );
}

export default PsychologyPage;
