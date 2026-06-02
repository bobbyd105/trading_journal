import { useState } from 'react';

const statuses = ['draft', 'closed', 'reviewed', 'archived'];

function updateScreenshot(form, slot, field, value) {
  const current = form[slot] || { file_name: '', file_path: '', content_type: '', notes: '' };
  const next = { ...current, [field]: value };
  const hasMetadata = Object.values(next).some((item) => item !== null && item !== '');
  return { ...form, [slot]: hasMetadata ? next : null };
}

function TradeForm({ editingTradeId, form, onCancelEdit, onFormChange, onSaveTag, onSaveTrade, onUploadAttachment, playbooks, tags }) {
  const [tagName, setTagName] = useState('');
  const [selectedFiles, setSelectedFiles] = useState({});

  async function handleCreateTag(event) {
    event.preventDefault();
    const name = tagName.trim();
    if (!name) {
      return;
    }
    await onSaveTag({ name });
    setTagName('');
  }

  function setField(field, value) {
    onFormChange({ ...form, [field]: value });
  }

  function toggleTag(tagId) {
    const nextTags = form.tags.includes(tagId)
      ? form.tags.filter((id) => id !== tagId)
      : [...form.tags, tagId];
    setField('tags', nextTags);
  }

  return (
    <form className="crud-form" onSubmit={onSaveTrade}>
      <h3>{editingTradeId ? 'Edit trade' : 'Create trade'}</h3>
      <div className="form-grid">
        <label>
          Symbol
          <input required value={form.symbol} onChange={(event) => setField('symbol', event.target.value)} />
        </label>
        <label>
          Direction
          <select value={form.direction} onChange={(event) => setField('direction', event.target.value)}>
            <option value="long">Long</option>
            <option value="short">Short</option>
          </select>
        </label>
        <label>
          Entry price
          <input step="any" type="number" value={form.entry_price} onChange={(event) => setField('entry_price', event.target.value)} />
        </label>
        <label>
          Exit price
          <input step="any" type="number" value={form.exit_price} onChange={(event) => setField('exit_price', event.target.value)} />
        </label>
        <label>
          Quantity
          <input step="any" type="number" value={form.quantity} onChange={(event) => setField('quantity', event.target.value)} />
        </label>
        <label>
          P&amp;L
          <input step="any" type="number" value={form.pnl} onChange={(event) => setField('pnl', event.target.value)} />
        </label>
        <label>
          Risk
          <input step="any" type="number" value={form.risk} onChange={(event) => setField('risk', event.target.value)} />
        </label>
        <label>
          Status
          <select value={form.status} onChange={(event) => setField('status', event.target.value)}>
            {statuses.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </label>
        <label>
          Playbook
          <select value={form.playbook_id} onChange={(event) => setField('playbook_id', event.target.value)}>
            <option value="">No playbook</option>
            {playbooks.map((playbook) => (
              <option key={playbook.id} value={playbook.id}>{playbook.name}</option>
            ))}
          </select>
        </label>
      </div>

      <fieldset>
        <legend>Tags</legend>
        <div className="inline-form">
          <label>
            New tag
            <input value={tagName} onChange={(event) => setTagName(event.target.value)} />
          </label>
          <button type="button" onClick={handleCreateTag}>Create tag</button>
        </div>
        <div className="pill-row">
          {tags.length === 0 ? <span className="muted">No tags created yet.</span> : null}
          {tags.map((tag) => (
            <label key={tag.id} className="check-pill">
              <input checked={form.tags.includes(tag.id)} type="checkbox" onChange={() => toggleTag(tag.id)} />
              {tag.name}
            </label>
          ))}
        </div>
      </fieldset>

      <label>
        Notes
        <textarea value={form.notes} onChange={(event) => setField('notes', event.target.value)} />
      </label>

      <div className="screenshot-grid">
        {['before_screenshot', 'after_screenshot'].map((slot) => {
          const label = slot === 'before_screenshot' ? 'Before screenshot' : 'After screenshot';
          const selectedFile = selectedFiles[slot] || null;
          return (
            <fieldset key={slot}>
              <legend>{label}</legend>
              <p className="muted">Store a local file path or upload into the app-managed attachments folder. The database only saves metadata.</p>
              <label>
                Select local image
                <input
                  accept="image/*"
                  disabled={!editingTradeId}
                  type="file"
                  onChange={(event) => setSelectedFiles({ ...selectedFiles, [slot]: event.target.files?.[0] || null })}
                />
              </label>
              <button
                disabled={!editingTradeId || !selectedFile}
                type="button"
                onClick={() => onUploadAttachment(slot, selectedFile, form[slot]?.notes || '')}
              >
                Upload selected file
              </button>
              {!editingTradeId ? <p className="muted">Save the trade before uploading a local file.</p> : null}
              <label>
                File name
                <input value={form[slot]?.file_name || ''} onChange={(event) => onFormChange(updateScreenshot(form, slot, 'file_name', event.target.value))} />
              </label>
              <label>
                File path
                <input value={form[slot]?.file_path || ''} onChange={(event) => onFormChange(updateScreenshot(form, slot, 'file_path', event.target.value))} />
              </label>
              <label>
                Content type
                <input placeholder="image/png" value={form[slot]?.content_type || ''} onChange={(event) => onFormChange(updateScreenshot(form, slot, 'content_type', event.target.value))} />
              </label>
              <label>
                Notes
                <input value={form[slot]?.notes || ''} onChange={(event) => onFormChange(updateScreenshot(form, slot, 'notes', event.target.value))} />
              </label>
            </fieldset>
          );
        })}
      </div>

      <div className="button-row">
        <button type="submit">{editingTradeId ? 'Update trade' : 'Create trade'}</button>
        {editingTradeId ? <button type="button" onClick={onCancelEdit}>Cancel edit</button> : null}
      </div>
    </form>
  );
}

function TradesPage({
  editingTradeId,
  form,
  onCancelEdit,
  onDeleteTrade,
  onEditTrade,
  onFormChange,
  onSaveTag,
  onSaveTrade,
  onSelectTrade,
  onUploadAttachment,
  playbooks,
  tags,
  trades,
}) {
  return (
    <section id="trades" className="panel">
      <p className="eyebrow">Phase 2 V1-Lite</p>
      <h2>Trades</h2>
      <p>Log trade records exactly as entered. Instruments stay optional metadata and do not replace symbols.</p>
      <TradeForm
        editingTradeId={editingTradeId}
        form={form}
        onCancelEdit={onCancelEdit}
        onFormChange={onFormChange}
        onSaveTag={onSaveTag}
        onSaveTrade={onSaveTrade}
        onUploadAttachment={onUploadAttachment}
        playbooks={playbooks}
        tags={tags}
      />
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Direction</th>
              <th>Status</th>
              <th>Quantity</th>
              <th>P&amp;L</th>
              <th>Playbook</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => (
              <tr key={trade.id}>
                <td>{trade.symbol}</td>
                <td>{trade.direction}</td>
                <td>{trade.status}</td>
                <td>{trade.quantity ?? '—'}</td>
                <td>{trade.pnl ?? '—'}</td>
                <td>{trade.playbook_name || '—'}</td>
                <td className="button-row">
                  <button type="button" onClick={() => onSelectTrade(trade.id)}>View</button>
                  <button type="button" onClick={() => onEditTrade(trade)}>Edit</button>
                  <button type="button" className="danger" onClick={() => onDeleteTrade(trade.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {trades.length === 0 ? (
              <tr><td colSpan="7" className="muted">No trades logged yet.</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default TradesPage;
