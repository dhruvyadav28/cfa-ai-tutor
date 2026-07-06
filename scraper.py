# scraper.py
TOPICS = [
    "Ethics",
    "Quant",
    "Economics",
    "FSA",
    "Corporate Issuers",
    "Equity",
    "Fixed Income",
    "Derivatives",
    "Alternatives",
    "Portfolio Management"
]

def scrape_all():
    """Creates placeholder .txt files for each topic so the app can start."""
    import os
    os.makedirs("./data", exist_ok=True)
    for topic in TOPICS:
        with open(f"./data/{topic}.txt", "w", encoding="utf-8") as f:
            f.write(f"CFA Level 1 – {topic} placeholder content.\n"
                    "Please replace with actual study notes or run a real scraper later.")
    print("Placeholder scraping done. Replace with real scraper for actual content.")