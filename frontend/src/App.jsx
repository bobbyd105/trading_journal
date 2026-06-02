import { useEffect, useMemo, useState } from 'react';

import DashboardPage from './pages/DashboardPage.jsx';
import PlaybooksPage from './pages/PlaybooksPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import TradeDetailPage from './pages/TradeDetailPage.jsx';
import TradesPage from './pages/TradesPage.jsx';

const navigationItems = [
  'Dashboard',
  'Trades',
  'Trade Detail',
  'Playbooks',
  'Settings',
];

const emptyTrade = {
  symbol: '',
  direction: 'long',
  entry_price: '',
  exit_price: '',
  quantity: '',
  pnl: '',
  risk: '',
  playbook_id: '',
  status: 'draft',
  tags: [],
  notes: '',
  before_screenshot: null,
  after_screenshot: null,
};

function normalizeNumber(value) {
  return value === '' || value === null || value === undefined ? null : Number(value);
}

function toTradePayload(form) {
  return {
    symbol: form.symbol,
    direction: form.direction,
    entry_price: normalizeNumber(form.entry_price),
    exit_price: normalizeNumber(form.exit_price),
    quantity: normalizeNumber(form.quantity),
    pnl: normalizeNumber(form.pnl),
    risk: normalizeNumber(form.risk),
    playbook_id: form.playbook_id ? Number(form.playbook_id) : null,
    status: form.status,
    tags: form.tags.map(Number),
    notes: form.notes || null,
    before_screenshot: form.before_screenshot,
    after_screenshot: form.after_screenshot,
  };
}

function tradeToForm(trade) {
  return {
    symbol: trade.symbol ?? '',
    direction: trade.direction ?? 'long',
    entry_price: trade.entry_price ?? '',
    exit_price: trade.exit_price ?? '',
    quantity: trade.quantity ?? '',
    pnl: trade.pnl ?? '',
    risk: trade.risk ?? '',
    playbook_id: trade.playbook_id ?? '',
    status: trade.status ?? 'draft',
    tags: (trade.tags ?? []).map((tag) => tag.id),
    notes: trade.notes ?? '',
    before_screenshot: trade.before_screenshot,
    after_screenshot: trade.after_screenshot,
  };
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function App() {
  const [trades, setTrades] = useState([]);
  const [playbooks, setPlaybooks] = useState([]);
  const [tags, setTags] = useState([]);
  const [selectedTradeId, setSelectedTradeId] = useState(null);
  const [tradeForm, setTradeForm] = useState(emptyTrade);
  const [editingTradeId, setEditingTradeId] = useState(null);
  const [message, setMessage] = useState('');

  const selectedTrade = useMemo(
    () => trades.find((trade) => trade.id === selectedTradeId) || trades[0] || null,
    [selectedTradeId, trades],
  );

  async function refreshData() {
    const [tradeData, playbookData, tagData] = await Promise.all([
      apiRequest('/trades'),
      apiRequest('/playbooks'),
      apiRequest('/tags'),
    ]);
    setTrades(tradeData);
    setPlaybooks(playbookData);
    setTags(tagData);
    if (!selectedTradeId && tradeData.length > 0) {
      setSelectedTradeId(tradeData[0].id);
    }
  }

  useEffect(() => {
    refreshData().catch((error) => setMessage(error.message));
  }, []);

  async function handleSaveTrade(event) {
    event.preventDefault();
    const payload = toTradePayload(tradeForm);
    const path = editingTradeId ? `/trades/${editingTradeId}` : '/trades';
    const method = editingTradeId ? 'PUT' : 'POST';
    const savedTrade = await apiRequest(path, { method, body: JSON.stringify(payload) });
    setMessage(`Saved ${savedTrade.symbol}`);
    setSelectedTradeId(savedTrade.id);
    setEditingTradeId(null);
    setTradeForm(emptyTrade);
    await refreshData();
  }

  function handleEditTrade(trade) {
    setEditingTradeId(trade.id);
    setTradeForm(tradeToForm(trade));
    window.location.hash = 'trades';
  }

  async function handleDeleteTrade(tradeId) {
    await apiRequest(`/trades/${tradeId}`, { method: 'DELETE' });
    setMessage('Trade deleted');
    setSelectedTradeId(null);
    await refreshData();
  }

  async function handleSavePlaybook(playbook) {
    const path = playbook.id ? `/playbooks/${playbook.id}` : '/playbooks';
    const method = playbook.id ? 'PUT' : 'POST';
    await apiRequest(path, { method, body: JSON.stringify(playbook) });
    setMessage('Playbook saved');
    await refreshData();
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">Trading Journal</div>
        <nav>
          {navigationItems.map((item) => (
            <a key={item} href={`#${item.toLowerCase().replaceAll(' ', '-')}`}>
              {item}
            </a>
          ))}
        </nav>
      </aside>
      <main className="content">
        {message ? <p className="notice">{message}</p> : null}
        <DashboardPage />
        <TradesPage
          editingTradeId={editingTradeId}
          form={tradeForm}
          onCancelEdit={() => {
            setEditingTradeId(null);
            setTradeForm(emptyTrade);
          }}
          onDeleteTrade={handleDeleteTrade}
          onEditTrade={handleEditTrade}
          onFormChange={setTradeForm}
          onSaveTrade={handleSaveTrade}
          onSelectTrade={setSelectedTradeId}
          playbooks={playbooks}
          tags={tags}
          trades={trades}
        />
        <TradeDetailPage onEditTrade={handleEditTrade} trade={selectedTrade} />
        <PlaybooksPage onSavePlaybook={handleSavePlaybook} playbooks={playbooks} />
        <SettingsPage />
      </main>
    </div>
  );
}

export default App;
