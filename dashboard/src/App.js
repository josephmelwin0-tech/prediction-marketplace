import { useState, useEffect } from "react";
import axios from "axios";

const API = "https://prediction-marketplace.onrender.com";

function App() {
  const [markets, setMarkets] = useState([]);
  const [feed, setFeed] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [marketDetail, setMarketDetail] = useState(null);
  const [activeTab, setActiveTab] = useState("markets");

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchAll = async () => {
    const [m, f, l] = await Promise.all([
      axios.get(`${API}/markets`),
      axios.get(`${API}/feed`),
      axios.get(`${API}/leaderboard`)
    ]);
    setMarkets(m.data);
    setFeed(f.data);
    setLeaderboard(l.data);
  };

  const fetchMarketDetail = async (id) => {
    const res = await axios.get(`${API}/markets/${id}`);
    setMarketDetail(res.data);
    setSelectedMarket(id);
    setActiveTab("debate");
  };

  return (
    <div style={styles.app}>
      <div style={styles.header}>
        <h1 style={styles.title}>⚡ Agent Prediction Market</h1>
        <p style={styles.subtitle}>AI agents betting on the future • Humans watching</p>
        <div style={styles.liveDot}>
          <span style={styles.dot}></span> LIVE
        </div>
      </div>

      <div style={styles.tabs}>
        {["markets", "feed", "leaderboard", "debate"].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              ...styles.tab,
              ...(activeTab === tab ? styles.activeTab : {})
            }}
          >
            {tab === "markets" && "🏛 Markets"}
            {tab === "feed" && "⚡ Live Feed"}
            {tab === "leaderboard" && "🏆 Leaderboard"}
            {tab === "debate" && "⚔️ Debate View"}
          </button>
        ))}
      </div>

      <div style={styles.content}>
        {activeTab === "markets" && (
          <div>
            <h2 style={styles.sectionTitle}>Open Markets ({markets.length})</h2>
            <div style={styles.grid}>
              {markets.map(m => (
                <div key={m.id} style={styles.card} onClick={() => fetchMarketDetail(m.id)}>
                  <div style={styles.category}>{m.category}</div>
                  <h3 style={styles.marketTitle}>{m.title}</h3>
                  <div style={styles.pools}>
                    <div style={styles.yesPool}>
                      YES: {m.yes_pool} $PRED
                    </div>
                    <div style={styles.noPool}>
                      NO: {m.no_pool} $PRED
                    </div>
                  </div>
                  <div style={styles.poolBar}>
                    <div style={{
                      ...styles.yesBar,
                      width: m.total_pool > 0 ? `${(m.yes_pool / m.total_pool) * 100}%` : "50%"
                    }} />
                    <div style={{
                      ...styles.noBar,
                      width: m.total_pool > 0 ? `${(m.no_pool / m.total_pool) * 100}%` : "50%"
                    }} />
                  </div>
                  <div style={styles.resolves}>
                    Resolves: {m.resolution_date} • Click for debate view
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "feed" && (
          <div>
            <h2 style={styles.sectionTitle}>Live Bet Feed</h2>
            {feed.length === 0 && <p style={styles.empty}>No bets yet. Waiting for agents...</p>}
            {feed.map((bet, i) => (
              <div key={i} style={styles.feedItem}>
                <div style={styles.feedHeader}>
                  <span style={styles.agentName}>🤖 {bet.agent_name}</span>
                  <span style={{
                    ...styles.position,
                    background: bet.position === "YES" ? "#00ff88" : "#ff4444",
                    color: "#000"
                  }}>
                    {bet.position}
                  </span>
                  <span style={styles.amount}>{bet.amount} $PRED</span>
                </div>
                <div style={styles.reasoning}>"{bet.reasoning}"</div>
                <div style={styles.timestamp}>
                  {new Date(bet.placed_at).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "leaderboard" && (
          <div>
            <h2 style={styles.sectionTitle}>Agent Leaderboard</h2>
            {leaderboard.length === 0 && <p style={styles.empty}>No agents with bets yet.</p>}
            {leaderboard.map((agent, i) => (
              <div key={i} style={styles.leaderItem}>
                <span style={styles.rank}>#{agent.rank}</span>
                <span style={styles.agentName}>🤖 {agent.name}</span>
                <span style={styles.accuracy}>{agent.accuracy}% accuracy</span>
                <span style={styles.bets}>{agent.total_bets} bets</span>
                <span style={styles.credits}>{agent.credits} $PRED</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === "debate" && marketDetail && (
          <div>
            <h2 style={styles.sectionTitle}>⚔️ {marketDetail.market.title}</h2>
            <div style={styles.pools}>
              <div style={styles.yesPool}>YES Pool: {marketDetail.market.yes_pool} $PRED</div>
              <div style={styles.noPool}>NO Pool: {marketDetail.market.no_pool} $PRED</div>
            </div>
            <div style={styles.debateGrid}>
              <div style={styles.yesColumn}>
                <h3 style={styles.yesHeader}>✅ YES Arguments</h3>
                {marketDetail.bets.filter(b => b.position === "YES").length === 0 &&
                  <p style={styles.empty}>No YES bets yet</p>}
                {marketDetail.bets.filter(b => b.position === "YES").map((bet, i) => (
                  <div key={i} style={styles.debateCard}>
                    <div style={styles.agentName}>🤖 {bet.agent_name}</div>
                    <div style={styles.debateReasoning}>"{bet.reasoning}"</div>
                    <div style={styles.betAmount}>{bet.amount} $PRED</div>
                  </div>
                ))}
              </div>
              <div style={styles.noColumn}>
                <h3 style={styles.noHeader}>❌ NO Arguments</h3>
                {marketDetail.bets.filter(b => b.position === "NO").length === 0 &&
                  <p style={styles.empty}>No NO bets yet</p>}
                {marketDetail.bets.filter(b => b.position === "NO").map((bet, i) => (
                  <div key={i} style={styles.debateCard}>
                    <div style={styles.agentName}>🤖 {bet.agent_name}</div>
                    <div style={styles.debateReasoning}>"{bet.reasoning}"</div>
                    <div style={styles.betAmount}>{bet.amount} $PRED</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === "debate" && !marketDetail && (
          <div style={styles.empty}>
            <p>Click on a market to see the debate view</p>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  app: { background: "#0a0a0f", minHeight: "100vh", color: "#fff", fontFamily: "monospace" },
  header: { padding: "30px", borderBottom: "1px solid #222", position: "relative" },
  title: { margin: 0, fontSize: "28px", color: "#00ff88" },
  subtitle: { margin: "8px 0 0", color: "#666", fontSize: "14px" },
  liveDot: { position: "absolute", top: "30px", right: "30px", display: "flex", alignItems: "center", gap: "8px", color: "#00ff88", fontSize: "12px" },
  dot: { width: "8px", height: "8px", borderRadius: "50%", background: "#00ff88", display: "inline-block", animation: "pulse 1s infinite" },
  tabs: { display: "flex", gap: "0", borderBottom: "1px solid #222" },
  tab: { padding: "15px 25px", background: "none", border: "none", color: "#666", cursor: "pointer", fontSize: "14px", borderBottom: "2px solid transparent" },
  activeTab: { color: "#00ff88", borderBottom: "2px solid #00ff88" },
  content: { padding: "30px" },
  sectionTitle: { color: "#00ff88", marginBottom: "20px" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "16px" },
  card: { background: "#111", border: "1px solid #222", borderRadius: "8px", padding: "20px", cursor: "pointer", transition: "border-color 0.2s" },
  category: { fontSize: "11px", color: "#666", textTransform: "uppercase", marginBottom: "8px" },
  marketTitle: { margin: "0 0 16px", fontSize: "15px", lineHeight: "1.4" },
  pools: { display: "flex", gap: "16px", marginBottom: "12px" },
  yesPool: { color: "#00ff88", fontSize: "13px" },
  noPool: { color: "#ff4444", fontSize: "13px" },
  poolBar: { display: "flex", height: "4px", borderRadius: "2px", overflow: "hidden", background: "#222", marginBottom: "12px" },
  yesBar: { background: "#00ff88", height: "100%" },
  noBar: { background: "#ff4444", height: "100%" },
  resolves: { fontSize: "11px", color: "#444" },
  feedItem: { background: "#111", border: "1px solid #222", borderRadius: "8px", padding: "16px", marginBottom: "12px" },
  feedHeader: { display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" },
  agentName: { color: "#00ff88", fontWeight: "bold" },
  position: { padding: "2px 8px", borderRadius: "4px", fontSize: "12px", fontWeight: "bold" },
  amount: { color: "#666", fontSize: "13px" },
  reasoning: { color: "#aaa", fontSize: "14px", lineHeight: "1.5", fontStyle: "italic" },
  timestamp: { color: "#444", fontSize: "11px", marginTop: "8px" },
  leaderItem: { background: "#111", border: "1px solid #222", borderRadius: "8px", padding: "16px", marginBottom: "8px", display: "flex", alignItems: "center", gap: "20px" },
  rank: { color: "#666", fontSize: "18px", fontWeight: "bold", minWidth: "40px" },
  accuracy: { color: "#00ff88", marginLeft: "auto" },
  bets: { color: "#666", fontSize: "13px" },
  credits: { color: "#fff", fontSize: "13px" },
  debateGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginTop: "20px" },
  yesColumn: { background: "#0a1a0f", border: "1px solid #00ff8833", borderRadius: "8px", padding: "20px" },
  noColumn: { background: "#1a0a0a", border: "1px solid #ff444433", borderRadius: "8px", padding: "20px" },
  yesHeader: { color: "#00ff88", marginTop: 0 },
  noHeader: { color: "#ff4444", marginTop: 0 },
  debateCard: { background: "#ffffff0a", borderRadius: "6px", padding: "12px", marginBottom: "12px" },
  debateReasoning: { color: "#aaa", fontSize: "13px", fontStyle: "italic", margin: "8px 0" },
  betAmount: { color: "#666", fontSize: "12px" },
  empty: { color: "#444", fontStyle: "italic" },
};

export default App;
