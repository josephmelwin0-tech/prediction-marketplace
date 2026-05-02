import requests
import json
import time
import random
import uuid
from groq import Groq
import os
from dotenv import load_dotenv
load_dotenv()


# --- CONFIG ---
API_BASE = "https://prediction-marketplace.onrender.com"
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # Replace with your key


# --- Two agent personalities ---
AGENTS = [
    {
        "name": "BullishBot-9000",
        "wallet": "wallet_bullish_9000",
        "personality": "You are an optimistic, data-driven AI agent. You tend to bet YES on markets involving AI progress, tech adoption, and innovation. You are confident and cite specific trends and data points in your reasoning.",
        "bias": "YES"
    },
    {
        "name": "SkepticalSam",
        "wallet": "wallet_skeptical_sam",
        "personality": "You are a cautious, contrarian AI agent. You tend to bet NO on markets, preferring to bet against hype and mainstream narratives. You cite historical failures, market inefficiencies, and regulatory risks in your reasoning.",
        "bias": "NO"
    }
]

client = Groq(api_key=GROQ_API_KEY)


def register_agent(agent):
    """Register an agent, skip if already exists."""
    try:
        res = requests.post(f"{API_BASE}/register", json={
            "name": agent["name"],
            "wallet_address": agent["wallet"]
        })
        if res.status_code == 200:
            data = res.json()
            print(f"✅ Registered {agent['name']} — ID: {data['agent_id']}")
            return data["agent_id"]
        elif res.status_code == 400:
            # Already registered, fetch existing ID
            agents = requests.get(f"{API_BASE}/agents").json()
            for a in agents:
                if a["name"] == agent["name"]:
                    print(f"♻️  {agent['name']} already registered — ID: {a['id']}")
                    return a["id"]
    except Exception as e:
        print(f"❌ Registration error for {agent['name']}: {e}")
    return None


def get_markets():
    """Fetch all open markets."""
    try:
        res = requests.get(f"{API_BASE}/markets")
        markets = res.json()
        print(f"📊 Found {len(markets)} open markets")
        return markets
    except Exception as e:
        print(f"❌ Error fetching markets: {e}")
        return []


def get_web_context(market_title):
    """Use Firecrawl to search for real web context for the market."""
    FIRECRAWL_API_KEY = "fc-4d8f59e5c87945d8abde0a516b726bd6"  # paste your key here
    try:
        res = requests.post(
            "https://api.firecrawl.dev/v1/search",
            headers={
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "query": market_title,
                "limit": 3,
                "scrapeOptions": {"formats": ["markdown"]}
            }
        )
        results = res.json().get("data", [])
        context = "\n".join([
            f"- {r.get('title', '')}: {r.get('description', '')}"
            for r in results if r.get('title')
        ])
        return f"\n\nReal-world context from web search:\n{context}" if context else ""
    except Exception as e:
        print(f"⚠️  Firecrawl search failed: {e}")
        return ""


def generate_reasoning(agent, market, web_context=""):
    """Use Groq/Llama to generate betting reasoning."""
    prompt = f"""You are {agent['name']}, an AI prediction market agent.

{agent['personality']}

You are analyzing this prediction market:
Title: {market['title']}
Category: {market['category']}
Resolution Date: {market['resolution_date']}
Current YES Pool: {market['yes_pool']} $PRED
Current NO Pool: {market['no_pool']} $PRED
{web_context}

Based on your personality and analysis, decide whether to bet YES or NO.
Your natural bias is {agent['bias']} but you can override it if the evidence is strong.

Respond in this exact JSON format:
{{
  "position": "YES" or "NO",
  "amount": a number between 5 and 20,
  "reasoning": "2-3 sentences explaining your reasoning with specific arguments"
}}

Only respond with the JSON, nothing else."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        raw = response.choices[0].message.content.strip()
        # Clean up in case model adds backticks
        raw = raw.replace("```json", "").replace("```", "").strip()
        decision = json.loads(raw)
        return decision
    except Exception as e:
        print(f"❌ Groq error: {e}")
        # Fallback decision
        return {
            "position": agent["bias"],
            "amount": 10.0,
            "reasoning": f"Based on market trends and my analysis of {market['title']}, I am placing this bet with moderate confidence."
        }


def place_bet(agent_id, market, decision):
    """Place a bet on the market."""
    try:
        res = requests.post(f"{API_BASE}/markets/{market['id']}/bet", json={
            "agent_id": agent_id,
            "position": decision["position"],
            "amount": float(decision["amount"]),
            "reasoning": decision["reasoning"]
        })
        if res.status_code == 200:
            data = res.json()
            print(f"  💰 Bet placed: {decision['position']} {decision['amount']} $PRED")
            print(f"  💭 Reasoning: {decision['reasoning']}")
            print(f"  💳 Remaining credits: {data['remaining_credits']}")
            return True
        else:
            print(f"  ❌ Bet failed: {res.json()}")
            return False
    except Exception as e:
        print(f"  ❌ Bet error: {e}")
        return False


def run_agent_loop(rounds=3, delay=15):
    """Main loop — agents register then bet on markets."""
    print("🚀 Starting Agent Prediction Market Bot")
    print("=" * 50)

    # Register all agents
    agent_ids = {}
    for agent in AGENTS:
        agent_id = register_agent(agent)
        if agent_id:
            agent_ids[agent["name"]] = agent_id

    if not agent_ids:
        print("❌ No agents registered. Exiting.")
        return

    print(f"\n✅ {len(agent_ids)} agents ready\n")

    for round_num in range(1, rounds + 1):
        print(f"\n{'='*50}")
        print(f"🔄 ROUND {round_num}/{rounds}")
        print(f"{'='*50}")

        markets = get_markets()
        if not markets:
            print("No open markets found.")
            time.sleep(delay)
            continue

        for agent in AGENTS:
            agent_id = agent_ids.get(agent["name"])
            if not agent_id:
                continue

            # Pick a random market
            market = random.choice(markets)
            print(f"\n🤖 {agent['name']} analyzing: {market['title']}")

            # Get web context (if Exa configured)
            web_context = get_web_context(market["title"])
            if web_context:
                print(f"  🌐 Got web context from Exa")

            # Generate reasoning
            decision = generate_reasoning(agent, market, web_context)
            print(f"  🧠 Decision: {decision['position']} {decision['amount']} $PRED")

            # Place the bet
            place_bet(agent_id, market, decision)

            # Small delay between agents
            time.sleep(3)

        print(f"\n⏳ Waiting {delay} seconds before next round...")
        time.sleep(delay)

    print("\n✅ All rounds complete. Check your dashboard!")
    print(f"🌐 {API_BASE.replace('prediction-marketplace.onrender.com', 'rococo-moxie-49ce59.netlify.app')}")


if __name__ == "__main__":
    run_agent_loop(rounds=3, delay=15)