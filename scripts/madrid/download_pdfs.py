import asyncio
import aiohttp
import json
import os
import aiofiles
import pdfplumber
import io

async def download_and_check(session, doc_info, sem):
    doc_id = doc_info['id']
    url = doc_info['url']
    filename = f"DS-{doc_id}.pdf"
    dest_path = os.path.join("data/madrid/raw/pdf", filename)
    
    if os.path.exists(dest_path):
        return True
        
    async with sem:
        try:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Quick heuristic check before saving: look for text
                    # We can use pdfplumber on the bytes
                    has_votes = False
                    try:
                        with pdfplumber.open(io.BytesIO(content)) as pdf:
                            text = ""
                            for page in pdf.pages[:20]: # Check first 20 pages
                                text += (page.extract_text() or "")
                            if "resultado de la votación" in text.lower() or "votos emitidos" in text.lower():
                                has_votes = True
                    except:
                        pass
                        
                    if has_votes:
                        async with aiofiles.open(dest_path, 'wb') as f:
                            await f.write(content)
                        print(f"Saved Plenary Session {filename} (Votes found!)")
                        return True
                    else:
                        print(f"Skipped {filename} (No votes found)")
                        return False
        except Exception as e:
            print(f"Error downloading {filename}: {e}")
            return False

async def main():
    index_file = "data/madrid/sessions_index.json"
    if not os.path.exists(index_file):
        print(f"Error: {index_file} not found")
        return
        
    with open(index_file, "r") as f:
        sessions = json.load(f)
        
    os.makedirs("data/madrid/raw/pdf", exist_ok=True)
    
    sem = asyncio.Semaphore(15) # Concurrent downloads
    
    # We will use aiohttp ClientSession
    connector = aiohttp.TCPConnector(limit=15)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [download_and_check(session, doc, sem) for doc in sessions]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
