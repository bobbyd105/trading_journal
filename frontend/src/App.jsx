import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from './api/client.js';
import { emptyTrade, toTradePayload, tradeToForm } from './domain/trades.js';
import DashboardPage from './pages/DashboardPage.jsx';
import PlaybooksPage from './pages/PlaybooksPage.jsx';
import ReviewsPage from './pages/ReviewsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import TradeDetailPage from './pages/TradeDetailPage.jsx';
import TradesPage from './pages/TradesPage.jsx';

const navigationItems = [
  'Dashboard',
  'Trades',
  'Trade Detail',
  'Playbooks',
  'Reviews',
  'Settings',
];

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

  async function handleCreateTag(tag) {
    await apiRequest('/tags', { method: 'POST', body: JSON.stringify(tag) });
    setMessage('Tag created');
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
          onSaveTag={handleCreateTag}
          onSaveTrade={handleSaveTrade}
          onSelectTrade={setSelectedTradeId}
          playbooks={playbooks}
          tags={tags}
          trades={trades}
        />
        <TradeDetailPage onEditTrade={handleEditTrade} trade={selectedTrade} />
        <PlaybooksPage onSavePlaybook={handleSavePlaybook} playbooks={playbooks} />
        <ReviewsPage onDataChanged={refreshData} onMessage={setMessage} />
        <SettingsPage />
      </main>
    </div>
  );
}

export default App;
