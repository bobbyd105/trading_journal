import { useState } from 'react';

const emptyPlaybook = { name: '', description: '', is_active: true };

function PlaybooksPage({ onSavePlaybook, playbooks }) {
  const [form, setForm] = useState(emptyPlaybook);

  async function handleSubmit(event) {
    event.preventDefault();
    await onSavePlaybook({
      ...form,
      description: form.description || null,
      is_active: Boolean(form.is_active),
    });
    setForm(emptyPlaybook);
  }

  function editPlaybook(playbook) {
    setForm({
      id: playbook.id,
      name: playbook.name,
      description: playbook.description || '',
      is_active: Boolean(playbook.is_active),
    });
  }

  return (
    <section id="playbooks" className="panel">
      <p className="eyebrow">Phase 2 V1-Lite</p>
      <h2>Playbooks</h2>
      <p>Create simple strategy labels that can be attached to trades without adding analytics logic.</p>
      <form className="crud-form" onSubmit={handleSubmit}>
        <h3>{form.id ? 'Edit playbook' : 'Create playbook'}</h3>
        <div className="form-grid">
          <label>
            Name
            <input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          </label>
          <label>
            Active
            <select value={String(form.is_active)} onChange={(event) => setForm({ ...form, is_active: event.target.value === 'true' })}>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </label>
        </div>
        <label>
          Description
          <textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
        </label>
        <div className="button-row">
          <button type="submit">{form.id ? 'Update playbook' : 'Create playbook'}</button>
          {form.id ? <button type="button" onClick={() => setForm(emptyPlaybook)}>Cancel edit</button> : null}
        </div>
      </form>
      <div className="card-list">
        {playbooks.map((playbook) => (
          <article key={playbook.id} className="list-card">
            <div>
              <strong>{playbook.name}</strong>
              <p>{playbook.description || 'No description'}</p>
              <span className="muted">{playbook.is_active ? 'Active' : 'Inactive'}</span>
            </div>
            <button type="button" onClick={() => editPlaybook(playbook)}>Edit</button>
          </article>
        ))}
        {playbooks.length === 0 ? <p className="muted">No playbooks created yet.</p> : null}
      </div>
    </section>
  );
}

export default PlaybooksPage;
