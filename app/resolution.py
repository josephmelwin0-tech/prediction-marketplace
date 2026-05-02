import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

from groq import Groq
client = Groq(api_key=GROQ_API_KEY)


def search_resolution_evidence(market_title, resolution_source):
    """Use Firecrawl to search for evidence about market resolution."""
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
        evidence = "\n".join([
            f"- {r.get('title', '')}: {r.get('description', '')}"
            for r in results if r.get('title')
        ])
        return evidence if evidence else ""
    except Exception as e:
        print(f"⚠️ Firecrawl error: {e}")
        return ""


def determine_resolution(market_title, resolution_date, evidence):
    """Use Groq to determine if market resolved YES or NO."""
    prompt = f"""You are a prediction market resolution judge.

Market: {market_title}
Resolution Date: {resolution_date}

Evidence from web search:
{evidence}

Based on this evidence, has this prediction market resolved?
- If the event has clearly happened: answer YES
- If the event has clearly NOT happened: answer NO  
- If there is not enough evidence or it's still uncertain: answer UNRESOLVED

Respond in this exact JSON format only:
{{
  "resolution": "YES" or "NO" or "UNRESOLVED",
  "confidence": a number between 0 and 1,
  "reasoning": "1-2 sentences explaining your resolution decision"
}}

Only respond with JSON, nothing else."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group()

        result = json.loads(raw)
        return result
    except Exception as e:
        print(f"⚠️ Groq resolution error: {e}")
        return {"resolution": "UNRESOLVED", "confidence": 0, "reasoning": "Error determining resolution"}


def redistribute_credits(market, winning_position, db):
    """Redistribute credits to winning agents."""
    from .models import Bet, Agent

    bets = db.query(Bet).filter(Bet.market_id == market.id).all()
    winning_bets = [b for b in bets if b.position == winning_position]
    losing_bets = [b for b in bets if b.position != winning_position]

    if not winning_bets:
        print(f"  No winners for {winning_position} — refunding all bets")
        for bet in bets:
            agent = db.query(Agent).filter(Agent.id == bet.agent_id).first()
            if agent:
                agent.credits += bet.amount
        db.commit()
        return

    # Total losing pool goes to winners proportionally
    total_losing_pool = sum(b.amount for b in losing_bets)
    total_winning_pool = sum(b.amount for b in winning_bets)

    for bet in winning_bets:
        agent = db.query(Agent).filter(Agent.id == bet.agent_id).first()
        if agent:
            # Return original bet + proportional share of losing pool
            share = (bet.amount / total_winning_pool) * total_losing_pool
            winnings = bet.amount + share
            agent.credits += winnings
            agent.correct_bets += 1
            print(f"  💰 {agent.name} won {winnings:.2f} $PRED")

    db.commit()