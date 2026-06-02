const metrics = ['Net P&L', 'Win Rate', 'Profit Factor', 'Average R', 'Total Trades'];

function DashboardPage() {
  return (
    <section id="dashboard" className="panel">
      <p className="eyebrow">Phase 1 foundation</p>
      <h1>Dashboard</h1>
      <p>Analytics placeholders are reserved for Phase 4 and will derive from canonical trade records.</p>
      <div className="metric-grid">
        {metrics.map((metric) => (
          <article key={metric} className="metric-card">
            <span>{metric}</span>
            <strong>—</strong>
          </article>
        ))}
      </div>
    </section>
  );
}

export default DashboardPage;
