import asyncio
import aiohttp
import json
import os

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

async def main():
    os.makedirs("data/madrid", exist_ok=True)
    sessions = []
    
    # We use a semaphore to limit concurrency
    sem = asyncio.Semaphore(50)
    
    async def bounded_check(session, leg, idx):
        async with sem:
            return await check_url(session, leg, idx)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for leg, max_idx in LEGISLATURAS.items():
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
