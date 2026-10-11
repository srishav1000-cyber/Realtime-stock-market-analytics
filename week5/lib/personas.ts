export type Persona = 'day' | 'retail' | 'institutional' | 'executive';

export const PERSONAS: { id: Persona; icon: string; label: string; blurb: string }[] = [
  { id: 'day', icon: '⚡', label: 'Day Trader', blurb: 'Depth, tape speed, rolling VWAP, volatility' },
  { id: 'retail', icon: '📊', label: 'Retail Investor', blurb: 'Portfolio P&L, RSI, dividends, watchlist' },
  { id: 'institutional', icon: '🏛️', label: 'Institutional Analyst', blurb: 'Heatmap, correlation, breadth, Sharpe' },
  { id: 'executive', icon: '👔', label: 'Executive', blurb: 'Risk score, market-cap trend, HHI, sentiment' },
];

export const personaOf = (id: Persona) => PERSONAS.find((p) => p.id === id)!;
