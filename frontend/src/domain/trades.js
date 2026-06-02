export const emptyTrade = {
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

export function toTradePayload(form) {
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

export function tradeToForm(trade) {
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
