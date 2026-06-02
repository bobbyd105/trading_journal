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

function App() {
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
        <DashboardPage />
        <TradesPage />
        <TradeDetailPage />
        <PlaybooksPage />
        <SettingsPage />
      </main>
    </div>
  );
}

export default App;
