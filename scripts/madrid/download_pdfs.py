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
    # Use legis_id in filename if available to avoid collisions
    legis_id = doc_info.get('legis_id', 'XIII')
    filename = f"DS-{legis_id}-{doc_id}.pdf"
    dest_path = os.path.join("data/madrid/raw/pdf", filename)
    
    if os.path.exists(dest_path):
        return True
        
    async with sem:
        for attempt in range(3): # Try 3 times
            try:
                async with session.get(url, timeout=60) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        has_votes = False
                        try:
                            with pdfplumber.open(io.BytesIO(content)) as pdf:
                                text = ""
                                # Check first 30 pages and last 10 (votes often at the end)
                                pages_to_check = pdf.pages[:30]
                                if len(pdf.pages) > 40:
                                    pages_to_check += pdf.pages[-10:]
                                
                                for page in pages_to_check:
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
                            # We create a small empty marker file to avoid re-checking non-voting PDFs
                            async with aiofiles.open(dest_path + ".novotes", 'w') as f:
                                await f.write("")
                            print(f"Skipped {filename} (No votes found)")
                            return False
                    elif response.status == 404:
                        return False
            except Exception as e:
                if attempt == 2:
                    print(f"Error downloading {filename} after 3 attempts: {e}")
                else:
                    await asyncio.sleep(2 * (attempt + 1)) # Backoff
        return False

async def main():
    index_file = "data/madrid/sessions_index.json"
    if not os.path.exists(index_file):
        print(f"Error: {index_file} not found")
        return
        
    with open(index_file, "r") as f:
        sessions = json.load(f)
        
    os.makedirs("data/madrid/raw/pdf", exist_ok=True)
    
    # Filter sessions that were already marked as no-votes
    sessions = [s for s in sessions if not os.path.exists(os.path.join("data/madrid/raw/pdf", f"DS-{s.get('legis_id', 'XIII')}-{s['id']}.pdf.novotes"))]
    
    sem = asyncio.Semaphore(5) # Lower concurrency to avoid being blocked
    
    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [download_and_check(session, doc, sem) for doc in sessions]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
