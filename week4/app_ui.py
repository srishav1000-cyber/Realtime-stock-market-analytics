"""UpCircuit ⚡ — unified trading & surveillance UI (Streamlit + Plotly).
Run: streamlit run week4/app_ui.py
Env: FINNHUB_KEY, GEMINI_API_KEY, API_URL (default http://localhost:8000), API_KEY
Deps: streamlit>=1.37 plotly yfinance pandas numpy requests google-genai
"""
import os, re, time, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import numpy as np, pandas as pd, requests, streamlit as st, yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")
FINNHUB = os.getenv("FINNHUB_KEY", "")
INDICES = {"NIFTY 50": "^NSEI", "SENSEX": "^BSESN", "BANKNIFTY": "^NSEBANK", "INDIA VIX": "^INDIAVIX"}
UNIVERSE = {
    "Large": {"RELIANCE.NS": "Energy", "TCS.NS": "IT", "HDFCBANK.NS": "Banking", "INFY.NS": "IT",
              "ICICIBANK.NS": "Banking", "TATAMOTORS.NS": "Auto", "KOTAKBANK.NS": "Banking", "SBIN.NS": "Banking"},
    "Mid": {"APOLLOTYRE.NS": "Auto", "BHARATFORG.NS": "Auto", "PERSISTENT.NS": "IT", "VOLTAS.NS": "Industrials"},
    "Small": {"IDEA.NS": "Telecom", "SOUTHBANK.NS": "Banking", "RPOWER.NS": "Energy"},
}
SECTOR = {s: sec for g in UNIVERSE.values() for s, sec in g.items()}
INTERVALS = {"1m": ("1d", "1m"), "5m": ("5d", "5m"), "15m": ("5d", "15m"), "1D": ("6mo", "1d"),
             "1W": ("2y", "1wk"), "1M": ("5y", "1mo"), "1Y": ("1y", "1d"), "5Y": ("5y", "1wk")}
MODES = ["🟢 Retail Investor", "⚡ Day Trader", "🏛️ Institutional Analyst", "👔 Executive & Compliance"]
POLICY = {"PLI Scheme 2.0": r"\bPLI\b", "Green Hydrogen Mission": r"hydrogen", "Defence Modernisation": r"defen[cs]e",
          "Order Win": r"order|bags|secures|wins|contract"}
POS, NEG = r"surge|gain|win|secure|bags|rally|profit|record|upgrade|boost", r"fall|slump|loss|probe|fraud|cut|downgrade|crash|penalty"

st.set_page_config("UpCircuit ⚡", "⚡", layout="wide")
st.markdown("""<style>
.stApp{background:#0b0e14;color:#e6e8ee}
.card{background:#141a24;border:1px solid #232c3b;border-radius:10px;padding:12px 14px}
.up{color:#00c076}.dn{color:#ff4d4f}.badge{background:#1d2b3f;color:#6cb6ff;border-radius:6px;padding:2px 8px;font-size:.72rem;margin-right:4px}
.breach{background:#7a1020;border:1px solid #ff4d4f;border-radius:8px;padding:10px 14px;font-weight:600}
.meter{height:5px;background:#2a3344;border-radius:3px}.meter>div{height:5px;background:#00c076;border-radius:3px}
</style>""", unsafe_allow_html=True)

# ---------------- data layer ----------------
@st.cache_data(ttl=30, show_spinner=False)
def history(sym, period, interval):
    df = yf.Ticker(sym).history(period=period, interval=interval)
    return df.tz_convert("Asia/Kolkata") if not df.empty and df.index.tz else df

@st.cache_data(ttl=30, show_spinner=False)
def snapshot(symbols: tuple):
    def one(s):
        try:
            h = history(s, "5d", "1m")
            day = h[h.index.date == h.index.date[-1]]
            prev = h[h.index.date < h.index.date[-1]]["Close"]
            pc = prev.iloc[-1] if len(prev) else day["Open"].iloc[0]
            ltp = day["Close"].iloc[-1]
            return dict(Symbol=s, Sector=SECTOR.get(s, "Index"), LTP=ltp, Open=day["Open"].iloc[0], PrevClose=pc,
                        High=day["High"].max(), Low=day["Low"].min(), **{"Chg%": (ltp / pc - 1) * 100,
                        "vsOpen%": (ltp / day["Open"].iloc[0] - 1) * 100}, Volume=int(day["Volume"].sum()),
                        Turnover=float((day["Close"] * day["Volume"]).sum()))
        except Exception:
            return None
    with ThreadPoolExecutor(8) as ex:
        rows = [r for r in ex.map(one, symbols) if r]
    return pd.DataFrame(rows)

def with_indicators(df, intraday):
    d = df.copy()
    d["SMA20"] = d.Close.rolling(20).mean()
    sd = d.Close.rolling(20).std()
    d["BBU"], d["BBL"] = d.SMA20 + 2 * sd, d.SMA20 - 2 * sd
    tp = (d.High + d.Low + d.Close) / 3
    if intraday:
        d["VWAP"] = (tp * d.Volume).groupby(d.index.date).cumsum() / d.Volume.groupby(d.index.date).cumsum()
    else:
        d["VWAP"] = (tp * d.Volume).rolling(20).sum() / d.Volume.rolling(20).sum()
    ch = d.Close.diff()
    rs = ch.clip(lower=0).ewm(alpha=1 / 14).mean() / (-ch.clip(upper=0)).ewm(alpha=1 / 14).mean()
    d["RSI"] = 100 - 100 / (1 + rs)
    d["Sigma"] = d.Close.pct_change().rolling(20).std() * 100
    d["VolMA"] = d.Volume.rolling(20).mean()
    return d

@st.cache_data(ttl=300, show_spinner=False)
def news():
    items = []
    queries = {"order win crore NSE": "Order Win", "PLI scheme India stocks": "PLI Scheme 2.0",
               "National Green Hydrogen Mission": "Green Hydrogen Mission", "defence modernisation India stocks": "Defence Modernisation"}
    for q, _ in queries.items():
        try:
            r = requests.get("https://news.google.com/rss/search", timeout=8,
                             params={"q": q + " when:7d", "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
            for it in ET.fromstring(r.content).iter("item"):
                items.append(dict(title=it.findtext("title"), link=it.findtext("link"), src="Google News RSS",
                                  ts=it.findtext("pubDate")))
        except Exception:
            pass
    if FINNHUB:
        try:
            for n in requests.get("https://finnhub.io/api/v1/news", params={"category": "general", "token": FINNHUB}, timeout=8).json()[:15]:
                items.append(dict(title=n["headline"], link=n["url"], src="Finnhub", ts=datetime.fromtimestamp(n["datetime"]).strftime("%a, %d %b %H:%M")))
        except Exception:
            pass
    seen, out = set(), []
    for i in items:
        if i["title"] and i["title"] not in seen:
            seen.add(i["title"])
            i["tags"] = [k for k, p in POLICY.items() if re.search(p, i["title"], re.I)]
            i["score"] = len(re.findall(POS, i["title"], re.I)) - len(re.findall(NEG, i["title"], re.I))
            out.append(i)
    return out

def api(method, path, **kw):
    try:
        r = requests.request(method, API_URL + path, headers={"X-API-Key": API_KEY}, timeout=4, **kw)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def place_order(sym, side, qty, price):
    res = api("POST", "/api/v1/orders", json=dict(symbol=sym, side=side, qty=qty, price=price))
    st.session_state.setdefault("orders", []).append(dict(t=datetime.now().strftime("%H:%M:%S"), sym=sym, side=side, qty=qty, px=round(price, 2), venue="API" if res else "PAPER"))
    st.toast(f"{side} {qty} {sym} @ {price:.2f} ({'API' if res else 'paper'})")

# ---------------- components ----------------
def pct(v): return f"<span class='{'up' if v >= 0 else 'dn'}'>{v:+.2f}%</span>"

@st.fragment(run_every=30)
def index_bar():
    snap = snapshot(tuple(INDICES.values()))
    cols = st.columns(4)
    for c, (name, sym) in zip(cols, INDICES.items()):
        r = snap[snap.Symbol == sym]
        if r.empty: c.warning(f"{name}: n/a"); continue
        r = r.iloc[0]; rng = (r.LTP - r.Low) / max(r.High - r.Low, 1e-9) * 100
        c.markdown(f"<div class='card'><b>{name}</b><br><span style='font-size:1.4rem'>{r.LTP:,.2f}</span> {pct(r['Chg%'])}"
                   f"<div class='meter'><div style='width:{rng:.0f}%'></div></div>"
                   f"<small>L {r.Low:,.0f} · H {r.High:,.0f}</small></div>", unsafe_allow_html=True)

def book(ltp, seed):
    rng = np.random.default_rng(seed); tick = round(max(ltp * 0.0002, 0.05), 2)
    lv = np.arange(1, 6)
    return (pd.DataFrame({"Bid": ltp - lv * tick, "BidQty": rng.integers(50, 2000, 5)}),
            pd.DataFrame({"Ask": ltp + lv * tick, "AskQty": rng.integers(50, 2000, 5)}))

def depth_panel(ltp, sym):
    bids, asks = book(ltp, int(time.time() // 5))
    st.caption("⚠️ Level-2 is **simulated** around LTP — yfinance has no depth feed. Plug in SmartAPI WebSocket for real depth.")
    fig = go.Figure([go.Bar(y=bids.Bid.round(2).astype(str), x=bids.BidQty, orientation="h", marker_color="#00c076", name="Bid"),
                     go.Bar(y=asks.Ask.round(2).astype(str), x=asks.AskQty, orientation="h", marker_color="#ff4d4f", name="Ask")])
    fig.update_layout(template="plotly_dark", height=240, margin=dict(l=0, r=0, t=10, b=0), barmode="group")
    st.plotly_chart(fig, use_container_width=True)

@st.dialog("📈 Chart", width="large")
def chart_dialog(sym):
    c1, c2 = st.columns([3, 2])
    iv = c1.radio("Interval", list(INTERVALS), horizontal=True, key=f"iv_{sym}")
    ind = c2.multiselect("Overlays", ["VWAP", "SMA20", "Bollinger", "RSI"], ["VWAP", "SMA20"], key=f"ov_{sym}")
    sr = st.text_input("Support/Resistance levels (comma-separated)", key=f"sr_{sym}")
    p, i = INTERVALS[iv]; df = history(sym, p, i)
    if df.empty: st.error("No data returned."); return
    d = with_indicators(df, i.endswith("m") and i != "1mo")
    rows = 3 if "RSI" in ind else 2
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, row_heights=[.6, .2, .2][:rows], vertical_spacing=.03)
    fig.add_trace(go.Candlestick(x=d.index, open=d.Open, high=d.High, low=d.Low, close=d.Close, name=sym,
                                 increasing_line_color="#00c076", decreasing_line_color="#ff4d4f"), 1, 1)
    if "VWAP" in ind: fig.add_scatter(x=d.index, y=d.VWAP, name="VWAP", line=dict(color="#f5a623", width=1.3), row=1, col=1)
    if "SMA20" in ind: fig.add_scatter(x=d.index, y=d.SMA20, name="SMA20", line=dict(color="#6cb6ff", width=1.3), row=1, col=1)
    if "Bollinger" in ind:
        for k in ("BBU", "BBL"): fig.add_scatter(x=d.index, y=d[k], name=k, line=dict(color="#8a8fa3", dash="dot", width=1), row=1, col=1)
    fig.add_bar(x=d.index, y=d.Volume, name="Volume", marker_color=np.where(d.Close >= d.Open, "#00c07688", "#ff4d4f88"), row=2, col=1)
    if "RSI" in ind:
        fig.add_scatter(x=d.index, y=d.RSI, name="RSI", line=dict(color="#c792ea"), row=3, col=1)
        for lvl in (30, 70): fig.add_hline(y=lvl, line_dash="dot", line_color="#555", row=3, col=1)
    for lvl in re.findall(r"\d+\.?\d*", sr): fig.add_hline(y=float(lvl), line_color="#f5a623", line_dash="dash", row=1, col=1)
    fig.update_layout(template="plotly_dark", height=620, xaxis_rangeslider_visible=False, dragmode="drawline",
                      newshape_line_color="#f5a623", margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True, config={"modeBarButtonsToAdd": ["drawline", "drawopenpath", "drawrect", "eraseshape"]})
    ltp = float(d.Close.iloc[-1]); b, o = st.columns([2, 3])
    with b: depth_panel(ltp, sym)
    with o:
        q = st.number_input("Qty", 1, 100000, 1, key=f"q_{sym}")
        x, y = st.columns(2)
        if x.button(f"BUY @ {ltp:.2f}", type="primary", use_container_width=True, key=f"b_{sym}"): place_order(sym, "BUY", q, ltp)
        if y.button(f"SELL @ {ltp:.2f}", use_container_width=True, key=f"s_{sym}"): place_order(sym, "SELL", q, ltp)

def stock_table(df, key):
    show = df[["Symbol", "LTP", "Chg%", "vsOpen%", "Volume"]].round(2).reset_index(drop=True)
    ev = st.dataframe(show, key=key, on_select="rerun", selection_mode="single-row", hide_index=True, use_container_width=True)
    sel = ev.selection.rows
    if sel and st.session_state.get("last_open") != (key, sel[0], time.time() // 1 * 0):
        st.session_state["last_open"] = (key, sel[0], 0)
        chart_dialog(show.Symbol[sel[0]])

def market_tables():
    cap = st.radio("Cap", list(UNIVERSE), horizontal=True, label_visibility="collapsed")
    df = snapshot(tuple(UNIVERSE[cap]))
    if df.empty: st.warning("No data (market closed or rate-limited)."); return df
    t = st.tabs(["Most Traded (turnover)", "Top Gainers", "Top Losers", "Volume Leaders"])
    views = [df.sort_values("Turnover", ascending=False), df.sort_values("Chg%", ascending=False),
             df.sort_values("Chg%"), df.sort_values("Volume", ascending=False)]
    for tab, v, n in zip(t, views, ("mb", "tg", "tl", "vl")):
        with tab: stock_table(v, f"{n}_{cap}")
    return df

def news_feed(limit=12, only_tags=False):
    for n in news()[:60]:
        if only_tags and not n["tags"]: continue
        limit -= 1
        if limit < 0: break
        badges = "".join(f"<span class='badge'>{t}</span>" for t in n["tags"])
        st.markdown(f"{badges}[{n['title']}]({n['link']})  \n<small>{n['src']} · {n['ts']}</small>", unsafe_allow_html=True)

def tools_menu():
    with st.popover("🛠 Quick Tools"):
        tool = st.selectbox("Tool", ["Basket Orders", "Place GTT Order", "Alerts Manager", "Scalper Mode", "Option Strategies"])
        syms = list(SECTOR)
        if tool == "Basket Orders":
            pick = st.multiselect("Symbols", syms); q = st.number_input("Qty each", 1, 10000, 1)
            if st.button("Submit basket") and pick:
                for s in pick: place_order(s, "BUY", q, float(snapshot((s,)).LTP.iloc[0]))
        elif tool == "Place GTT Order":
            s = st.selectbox("Symbol", syms); trig = st.number_input("Trigger price", 0.0); q = st.number_input("Qty", 1, 10000, 1)
            if st.button("Save GTT"): st.session_state.setdefault("gtt", []).append((s, trig, q)); st.success("GTT stored (paper)")
        elif tool == "Alerts Manager":
            s = st.selectbox("Symbol", syms); lvl = st.number_input("Alert at price", 0.0)
            if st.button("Add alert"): st.session_state.setdefault("alerts", []).append((s, lvl))
            st.write(st.session_state.get("alerts", []))
        elif tool == "Scalper Mode":
            st.session_state["scalper"] = st.toggle("5s refresh", st.session_state.get("scalper", False))
        else:
            st.info("Needs an F&O chain feed (not in yfinance). Not implemented.")

def check_alerts(snap):
    for s, lvl in st.session_state.get("alerts", []):
        r = snap[snap.Symbol == s]
        if not r.empty and abs(r.LTP.iloc[0] - lvl) / lvl < 0.002: st.toast(f"🔔 {s} near {lvl}")

# ---------------- stakeholder modes ----------------
def retail(df):
    l, r = st.columns([3, 2])
    with l:
        st.subheader("Watchlist")
        w = df[["Symbol", "LTP", "Chg%", "vsOpen%"]].round(2)
        st.dataframe(w, hide_index=True, use_container_width=True)
        spark = go.Figure([go.Scatter(x=(h := history(s, "1d", "5m")).index, y=h.Close, name=s) for s in df.Symbol[:4]])
        spark.update_layout(template="plotly_dark", height=220, margin=dict(l=0, r=0, t=10, b=0)); st.plotly_chart(spark, use_container_width=True)
    with r:
        st.subheader("Order Wins & Policy Radar"); news_feed(10)

def day_trader(df):
    sym = st.selectbox("Symbol", df.Symbol); d = with_indicators(history(sym, "1d", "1m"), True)
    if d.empty: return st.warning("No intraday data")
    last = d.iloc[-1]; op = d.Open.iloc[0]
    k = st.columns(4)
    k[0].metric("σ (20-bar %)", f"{last.Sigma:.3f}"); k[1].metric("VWAP dev", f"{(last.Close / last.VWAP - 1) * 100:+.2f}%")
    k[2].metric("To +5% band", f"{(op * 1.05 / last.Close - 1) * 100:.2f}%"); k[3].metric("To −5% band", f"{(last.Close / (op * .95) - 1) * 100:.2f}%")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[.75, .25])
    fig.add_trace(go.Candlestick(x=d.index, open=d.Open, high=d.High, low=d.Low, close=d.Close), 1, 1)
    fig.add_scatter(x=d.index, y=d.VWAP, name="VWAP", row=1, col=1); fig.add_bar(x=d.index, y=d.Volume, row=2, col=1)
    for m in (1.05, .95): fig.add_hline(y=op * m, line_color="#ff4d4f", line_dash="dot", row=1, col=1)
    fig.update_layout(template="plotly_dark", height=520, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=10, b=0))
    c1, c2 = st.columns([3, 1]); c1.plotly_chart(fig, use_container_width=True)
    with c2: depth_panel(float(last.Close), sym)

def institutional(df):
    l, r = st.columns(2)
    allv = snapshot(tuple(SECTOR))
    fig = go.Figure(go.Treemap(labels=allv.Symbol, parents=allv.Sector, values=allv.Turnover.clip(lower=1), marker=dict(colors=allv["Chg%"], colorscale="RdYlGn", cmid=0), customdata=allv["Chg%"].round(2), texttemplate="%{label}<br>%{customdata}%"))
    fig.update_layout(template="plotly_dark", height=380, margin=dict(l=0, r=0, t=30, b=0), title="Sector heatmap"); l.plotly_chart(fig, use_container_width=True)
    sc = [n["score"] for n in news()]; net = np.clip(np.mean(sc) if sc else 0, -2, 2)
    g = go.Figure(go.Indicator(mode="gauge+number", value=net, title={"text": "News sentiment (lexicon)"}, gauge={"axis": {"range": [-2, 2]}, "bar": {"color": "#6cb6ff"}}))
    g.update_layout(template="plotly_dark", height=250); r.plotly_chart(g, use_container_width=True)
    rows = []
    for s in df.Symbol:
        d = with_indicators(history(s, "1d", "1m"), True); surge = d[d.Volume > 3 * d.VolMA]
        rows.append(dict(Symbol=s, SurgeBars=len(surge), MaxMultiple=round((d.Volume / d.VolMA).max(), 1) if len(d) > 20 else 0))
    a = pd.DataFrame(rows); r.subheader("Volume anomaly density (>3× 20-bar MA)")
    r.plotly_chart(go.Figure(go.Bar(x=a.Symbol, y=a.SurgeBars)).update_layout(template="plotly_dark", height=250, margin=dict(l=0, r=0, t=10, b=0)), use_container_width=True)

def gemini_postmortem(a):
    key = os.getenv("GEMINI_API_KEY")
    if not key: return "Set GEMINI_API_KEY to generate post-mortems."
    try:
        from google import genai
        return genai.Client(api_key=key).models.generate_content(model="gemini-2.5-flash", contents=f"Write a 4-sentence compliance post-mortem for this circuit-breaker event; no speculation beyond data: {a}").text
    except Exception as e: return f"Gemini error: {e}"

def compliance(df):
    alerts = api("GET", "/api/v1/alerts/history", params={"limit": 50})
    if alerts is None:
        st.info(f"FastAPI at {API_URL} unreachable — showing local ±5% scan of live data.")
        alerts = [dict(id=f"local-{r.Symbol}", symbol=r.Symbol, change_pct=round(r["vsOpen%"], 2), status="OPEN")
                  for _, r in df.iterrows() if abs(r["vsOpen%"]) >= 5]
    alerts = alerts if isinstance(alerts, list) else alerts.get("alerts", [])
    live = [a for a in alerts if str(a.get("status", "OPEN")) != "REVIEWED"]
    if live: st.markdown(f"<div class='breach'>🚨 {len(live)} active circuit-breaker breach(es): {', '.join(str(a.get('symbol')) for a in live[:6])}</div>", unsafe_allow_html=True)
    else: st.success("No active breaches")
    t0 = time.time(); tr = api("GET", "/api/v1/trades", params={"limit": 200}); lat = (time.time() - t0) * 1000
    tel = api("GET", "/api/v1/telemetry") or {}
    k = st.columns(3)
    k[0].metric("Ticks/sec", tel.get("ticks_per_sec", "n/a")); k[1].metric("Consumer lag", tel.get("consumer_lag", "n/a"))
    k[2].metric("API latency (ms)", f"{lat:.0f}" if tr is not None else "down")
    st.subheader("Incident review")
    for a in alerts[:10]:
        aid = str(a.get("id")); c = st.columns([2, 2, 3, 3])
        c[0].write(f"**{a.get('symbol')}**"); c[1].write(f"{a.get('change_pct', '')}%")
        key = f"st_{aid}"; cur = st.session_state.get(key, a.get("status", "OPEN"))
        new = c[2].segmented_control("Status", ["OPEN", "REVIEWED", "ESCALATED"], default=cur, key=f"seg_{aid}", label_visibility="collapsed") or cur
        if new != cur: st.session_state[key] = new; api("PATCH", f"/api/v1/alerts/{aid}", json={"status": new})
        if c[3].button("AI post-mortem", key=f"pm_{aid}"): st.session_state[f"pm_txt_{aid}"] = gemini_postmortem(a)
        if f"pm_txt_{aid}" in st.session_state: st.caption(st.session_state[f"pm_txt_{aid}"])

# ---------------- main ----------------
def main():
    h1, h2 = st.columns([5, 1]); h1.title("UpCircuit ⚡"); h1.caption("Real-Time Stock Market Surveillance & Trading Engine · data: yfinance (≈15 min delayed for NSE), Google News RSS, Finnhub")
    with h2: tools_menu()
    mode = st.radio("Mode", MODES, horizontal=True, label_visibility="collapsed")
    index_bar()
    cards = st.columns(6)
    for c, (n, i) in zip(cards, [("Stock Discovery", "🔍"), ("News Discovery", "📰"), ("Mutual Funds", "💼"), ("F&O", "📊"), ("ETF Discovery", "🧺"), ("IPO Radar", "🚀")]):
        c.markdown(f"<div class='card' style='text-align:center'>{i}<br><small>{n}</small></div>", unsafe_allow_html=True)
    st.divider()
    big = snapshot(tuple(UNIVERSE["Large"]))
    check_alerts(big)
    if mode == MODES[0]:
        retail(big); st.divider(); market_tables()
    elif mode == MODES[1]: day_trader(big)
    elif mode == MODES[2]: institutional(big)
    else: compliance(big)
    st.subheader("Corporate Action & Policy Radar"); news_feed(8, only_tags=True)
    if st.session_state.get("orders"):
        with st.expander("Order log"): st.dataframe(pd.DataFrame(st.session_state["orders"]), hide_index=True)
    if st.session_state.get("scalper"): time.sleep(5); st.rerun()

main()