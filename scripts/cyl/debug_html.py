import requests
from bs4 import BeautifulSoup
import re

def check_html():
    url = "https://www.ccyl.es/Organizacion/PlenoAlfabetico?Legislatura=11"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find tables
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        print(f"Table {i} first rows:")
        rows = table.find_all('tr')[:5]
        for row in rows:
            print(f"  {row.get_text()[:100].strip()}")
            
    # If no tables, print body part
    if not tables:
        print(response.text[:2000])

if __name__ == "__main__":
    check_html()
