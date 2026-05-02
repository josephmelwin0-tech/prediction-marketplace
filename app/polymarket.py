def fetch_polymarket_markets(limit=13):
    markets = [
        {
            "title": "Will Claude 3.5 Sonnet be released by Anthropic in 2024?",
            "category": "AI",
            "resolution_date": "2024-12-31",
            "resolution_source": "anthropic.com/news",
            "created_by": "platform-seed"
        },
        {
            "title": "Will Bitcoin exceed $50,000 in 2024?",
            "category": "Crypto",
            "resolution_date": "2024-12-31",
            "resolution_source": "coinmarketcap.com",
            "created_by": "platform-seed"
        },
        {
            "title": "Will OpenAI release GPT-4o in 2024?",
            "category": "AI",
            "resolution_date": "2024-12-31",
            "resolution_source": "openai.com/blog",
            "created_by": "platform-seed"
        },
        {
            "title": "Will the US Federal Reserve cut interest rates before July 2026?",
            "category": "Economics",
            "resolution_date": "2026-07-01",
            "resolution_source": "federalreserve.gov",
            "created_by": "platform-seed"
        },
        {
            "title": "Will OpenAI release GPT-6 before September 2026?",
            "category": "AI",
            "resolution_date": "2026-09-01",
            "resolution_source": "openai.com/blog",
            "created_by": "platform-seed"
        },
        {
            "title": "Will Bitcoin reach $150,000 before December 2026?",
            "category": "Crypto",
            "resolution_date": "2026-12-01",
            "resolution_source": "coinmarketcap.com",
            "created_by": "platform-seed"
        },
        {
            "title": "Will Anthropic release Claude 5 before August 2026?",
            "category": "AI",
            "resolution_date": "2026-08-01",
            "resolution_source": "anthropic.com/news",
            "created_by": "platform-seed"
        },
        {
            "title": "Will India's GDP growth exceed 7% in 2026?",
            "category": "Economics",
            "resolution_date": "2026-12-31",
            "resolution_source": "mospi.gov.in",
            "created_by": "platform-seed"
        },
        {
            "title": "Will Solana's SOL token exceed $300 before October 2026?",
            "category": "Crypto",
            "resolution_date": "2026-10-01",
            "resolution_source": "coinmarketcap.com",
            "created_by": "platform-seed"
        },
        {
            "title": "Will OpenClaw reach 500,000 GitHub stars before 2027?",
            "category": "AI",
            "resolution_date": "2026-12-31",
            "resolution_source": "github.com/openclaw/openclaw",
            "created_by": "platform-seed"
        },
        {
            "title": "Will any AI model pass the Turing Test officially before 2027?",
            "category": "AI",
            "resolution_date": "2026-12-31",
            "resolution_source": "nature.com",
            "created_by": "platform-seed"
        },
        {
            "title": "Will Elon Musk's xAI surpass OpenAI in valuation before 2027?",
            "category": "Business",
            "resolution_date": "2026-12-31",
            "resolution_source": "bloomberg.com",
            "created_by": "platform-seed"
        },
        {
            "title": "Will a major AI regulation bill pass in the EU before September 2026?",
            "category": "Policy",
            "resolution_date": "2026-09-01",
            "resolution_source": "europarl.europa.eu",
            "created_by": "platform-seed"
        }
    ]
    return markets[:limit]