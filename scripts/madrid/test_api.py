import requests
import json
import re
import time

def solve_sucuri():
    url = "https://www.asambleamadrid.es/actividad-parlamentaria/votaciones"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # This is a shot in the dark, but let's see if we can get anything
    # Sucuri usually needs a cookie set by JS.
    # Without a JS engine, it's hard.
    
    # Let's try to see if they have an API for their search
    # Sometimes it's on a different port or path
    
    search_url = "https://www.asambleamadrid.es/web/guest/actividad-parlamentaria/votaciones?p_p_id=votaciones_WAR_votacionesportlet&p_p_lifecycle=2"
    print(f"Trying search URL: {search_url}")
    try:
        r = requests.get(search_url, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Body snippet: {r.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    solve_sucuri()
