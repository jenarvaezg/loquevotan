import asyncio
import aiohttp
import json
import os
import argparse

LEGISLATURAS = {
    "XIII": 800,
    "XII": 500,
    "XI": 400,
    "X": 1000
}

async def check_url(session, leg, idx):
    url = f"https://www.asambleamadrid.es/static/doc/publicaciones/{leg}-DS-{idx}.pdf"
    try:
        async with session.head(url, timeout=10) as response:
            if response.status == 200:
                return {"id": f"{leg}-{idx}", "url": url, "legis_id": leg, "text": f"DS {idx}"}
    except:
        pass
    return None

def parse_legislaturas(value):
    if not value:
        return dict(LEGISLATURAS)
    requested = [v.strip().upper() for v in str(value).split(",") if v.strip()]
    filtered = {leg: max_idx for leg, max_idx in LEGISLATURAS.items() if leg in requested}
    missing = [leg for leg in requested if leg not in LEGISLATURAS]
    if missing:
        raise ValueError(f"Legislaturas desconocidas: {', '.join(missing)}")
    return filtered


async def main():
    parser = argparse.ArgumentParser(description="Scrapea índices de diarios de sesiones de Madrid.")
    parser.add_argument(
        "--legislaturas",
        help="Lista de legislaturas separadas por coma (ej: XIII,XII). Por defecto: XIII,XII,XI,X.",
    )
    args = parser.parse_args()

    legislaturas = parse_legislaturas(args.legislaturas)
    os.makedirs("data/madrid", exist_ok=True)
    sessions = []
    
    # We use a semaphore to limit concurrency
    sem = asyncio.Semaphore(50)
    
    async def bounded_check(session, leg, idx):
        async with sem:
            return await check_url(session, leg, idx)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for leg, max_idx in legislaturas.items():
            for idx in range(1, max_idx + 1):
                tasks.append(bounded_check(session, leg, idx))
                
        results = await asyncio.gather(*tasks)
        for r in results:
            if r:
                sessions.append(r)
                
    with open("data/madrid/sessions_index.json", "w") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)
        
    print(f"Found {len(sessions)} valid session diaries.")

if __name__ == "__main__":
    asyncio.run(main())
