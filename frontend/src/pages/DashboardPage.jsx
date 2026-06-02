import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '../api/client.js';

const metricCards = [
  ['total_trades', 'Total Trades', 'integer'],
  ['net_pnl', 'Net P&L', 'currency'],
  ['gross_pnl', 'Gross P&L', 'currency'],
  ['win_rate', 'Win Rate', 'percent'],
  ['average_win', 'Average Win', 'currency'],
  ['average_loss', 'Average Loss', 'currency'],
  ['profit_factor', 'Profit Factor', 'decimal'],
  ['expectancy', 'Expectancy', 'currency'],
  ['average_r', 'Average R', 'decimal'],
  ['best_trade', 'Best Trade', 'trade'],
  ['worst_trade', 'Worst Trade', 'trade'],
];

const groupedTables = [
  ['by_symbol', 'By Symbol'],
  ['by_playbook', 'By Playbook'],
  ['by_direction', 'By Direction'],
  ['by_tag', 'By Tag'],
  ['by_followed_playbook', 'By Followed Playbook'],
  ['by_discipline_score_band', 'By Discipline Score Band'],
];

function formatNumber(value, style = 'decimal') {
  if (value === null || value === undefined) {
    return '—';
  }
  if (style === 'integer') {
    return value.toLocaleString();
  }
  if (style === 'percent') {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (style === 'currency') {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  }
  return Number(value).toFixed(2);
}

function formatTrade(trade) {
  if (!trade) {
    return '—';
  }
  return `${trade.symbol} (${formatNumber(trade.pnl, 'currency')})`;
}

function formatMetric(value, style) {
  if (style === 'trade') {
    return formatTrade(value);
  }
  return formatNumber(value, style);
}

function buildQuery(filters) {
  const params = new URLSearchParams();
  if (filters.startDate) {
    params.set('start_date', filters.startDate);
  }
  if (filters.endDate) {
    params.set('end_date', filters.endDate);
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

function DashboardPage() {
  const [filters, setFilters] = useState({ startDate: '', endDate: '' });
  const [analytics, setAnalytics] = useState({ summary: null, equityCurve: [], grouped: {} });
  const [status, setStatus] = useState('Loading analytics…');

  const query = useMemo(() => buildQuery(filters), [filters]);

  useEffect(() => {
    let cancelled = false;
    async function loadAnalytics() {
      setStatus('Loading analytics…');
      try {
        const [summary, equityCurve, grouped] = await Promise.all([
          apiRequest(`/analytics/performance-summary${query}`),
          apiRequest(`/analytics/equity-curve${query}`),
          apiRequest(`/analytics/grouped-performance${query}`),
        ]);
        if (!cancelled) {
          setAnalytics({ summary, equityCurve, grouped });
          setStatus('');
        }
      } catch (error) {
        if (!cancelled) {
          setStatus(error.message);
        }
      }
    }
    loadAnalytics();
    return () => {
      cancelled = true;
    };
  }, [query]);

  const summary = analytics.summary || {};

  return (
    <section id="dashboard" className="panel">
      <p className="eyebrow">Analytics V1</p>
      <h1>Dashboard</h1>
      <p>Read-only analytics derived from closed and reviewed trades, reviews, tags, and playbooks.</p>

      <form className="inline-form analytics-filters">
        <label>
          Start date
          <input
            type="date"
            value={filters.startDate}
            onChange={(event) => setFilters((current) => ({ ...current, startDate: event.target.value }))}
          />
        </label>
        <label>
          End date
          <input
            type="date"
            value={filters.endDate}
            onChange={(event) => setFilters((current) => ({ ...current, endDate: event.target.value }))}
          />
        </label>
        <button type="button" onClick={() => setFilters({ startDate: '', endDate: '' })}>
          Clear dates
        </button>
      </form>

      {status ? <p className="muted">{status}</p> : null}

      <div className="metric-grid">
        {metricCards.map(([key, label, style]) => (
          <article key={key} className="metric-card">
            <span>{label}</span>
            <strong>{formatMetric(summary[key], style)}</strong>
          </article>
        ))}
      </div>

      <h2>Equity Curve</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Trade</th>
              <th>Symbol</th>
              <th>Closed</th>
              <th>P&L</th>
              <th>Cumulative P&L</th>
            </tr>
          </thead>
          <tbody>
            {analytics.equityCurve.map((point) => (
              <tr key={point.trade_id}>
                <td>{point.sequence}</td>
                <td>#{point.trade_id}</td>
                <td>{point.symbol}</td>
                <td>{point.closed_at || '—'}</td>
                <td>{formatNumber(point.pnl, 'currency')}</td>
                <td>{formatNumber(point.cumulative_pnl, 'currency')}</td>
              </tr>
            ))}
            {analytics.equityCurve.length === 0 ? (
              <tr>
                <td colSpan="6">No closed or reviewed trades match the current filters.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <h2>Grouped Performance</h2>
      <div className="analytics-group-grid">
        {groupedTables.map(([key, title]) => (
          <article key={key} className="metadata-card">
            <h3>{title}</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Group</th>
                    <th>Trades</th>
                    <th>Net P&L</th>
                    <th>Win Rate</th>
                    <th>Profit Factor</th>
                    <th>Avg R</th>
                  </tr>
                </thead>
                <tbody>
                  {(analytics.grouped[key] || []).map((row) => (
                    <tr key={row.group}>
                      <td>{row.group}</td>
                      <td>{formatNumber(row.metrics.total_trades, 'integer')}</td>
                      <td>{formatNumber(row.metrics.net_pnl, 'currency')}</td>
                      <td>{formatNumber(row.metrics.win_rate, 'percent')}</td>
                      <td>{formatNumber(row.metrics.profit_factor, 'decimal')}</td>
                      <td>{formatNumber(row.metrics.average_r, 'decimal')}</td>
                    </tr>
                  ))}
                  {(analytics.grouped[key] || []).length === 0 ? (
                    <tr>
                      <td colSpan="6">No data.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default DashboardPage;
