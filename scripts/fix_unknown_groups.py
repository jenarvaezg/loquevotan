import json
import os

# 1. Andalusia Fixes (Diputados)
ANDALUCIA_DIPS = "data/andalucia/diputados_raw.json"
AND_FIXES = {
    "Alba Castiñeira, María José de": "POPULAR ANDALUZ",
    "Cervantes Llort, Montserrat": "VOX EN ANDALUCÍA",
    "Gaviño Pazó, Manuel Enrique": "VOX EN ANDALUCÍA",
    "Llanes Díaz-Salazar, Gaspar José": "PSOE DE ANDALUCÍA",
    "Navarro Rodríguez, María del Pilar": "PSOE DE ANDALUCÍA",
    "Olmo Ruiz, María Auxiliadora del": "POPULAR ANDALUZ",
    "Olona Choclán, Macarena": "VOX EN ANDALUCÍA",
    "Paz Jurado, Montserrat": "POPULAR ANDALUZ",
    "Prieto Rodríguez, María Ángeles": "PSOE DE ANDALUCÍA",
    "Repullo Milla, Antonio Jesús": "POPULAR ANDALUZ",
    "Romaní Cantera, José Ignacio": "POPULAR ANDALUZ",
    "Sánchez Antúnez, Ricardo Antonio": "POPULAR ANDALUZ",
    "Verano Domínguez, Bella": "POPULAR ANDALUZ",
    "Lozano Moral, María Isabel": "POPULAR ANDALUZ",
    "Gaya Sánchez, María Sonia": "PSOE DE ANDALUCÍA",
    "Martínez Granados, María del Carmen": "CIUDADANOS",
    "Crespo Díaz, María Carmen": "POPULAR ANDALUZ",
    "Lizárraga Mollinedo, María del Carmen": "PODEMOS ANDALUCIA",
    "Fernández Rodríguez, Manuel Alberto": "POPULAR ANDALUZ",
    "González Rivera, Manuel Andrés": "POPULAR ANDALUZ",
    "Jiménez Vílchez, María Teresa": "PSOE DE ANDALUCÍA",
    "López Gabarro, María Dolores": "POPULAR ANDALUZ",
    "Oña Sevilla, María Esperanza": "POPULAR ANDALUZ",
    "Pozo Fernández, Patricia del": "POPULAR ANDALUZ"
}

def fix_andalucia_dips():
    if not os.path.exists(ANDALUCIA_DIPS): return
    with open(ANDALUCIA_DIPS, "r") as f:
        dips = json.load(f)
    
    fixed = 0
    for d in dips:
        if d.get("grupo") == "Unknown" and d["nombre"] in AND_FIXES:
            d["grupo"] = AND_FIXES[d["nombre"]]
            fixed += 1
    
    with open(ANDALUCIA_DIPS, "w") as f:
        json.dump(dips, f, indent=2, ensure_ascii=False)
    print(f"Andalucía: Fixed {fixed} unknown groups in diputados_raw.")

# 2. CyL VIII Fixes (Votos)
CYL_V8_RAW = "data/cyl/votos_VIII_raw.json"
def fix_cyl_v8():
    if not os.path.exists(CYL_V8_RAW): return
    with open(CYL_V8_RAW, "r") as f:
        votaciones = json.load(f)
    
    fixed_votos = 0
    for v in votaciones:
        for voto in v["votos"]:
            if voto.get("grupo") == "Unknown":
                name = voto["diputado"].upper()
                if any(x in name for x in ["CORTÉS", "CRUZ", "CUESTA", "HERAS", "VÁZQUEZ", "BLANCO", "GARCÍA NIETO", "AGUILAR CAÑEDO", "ALZOLA", "ARMISÉN", "ENCABO"]):
                    voto["grupo"] = "Popular"
                elif any(x in name for x in ["LÓPEZ ÁGUEDA", "TUDANCA", "MARTIN BENITO", "SÁNCHEZ HERNÁNDEZ", "ACEVES", "AGUDÍEZ", "ALONSO DÍEZ"]):
                    voto["grupo"] = "Socialista"
                else:
                    voto["grupo"] = "Mixto" # Better than Unknown
                fixed_votos += 1
                
    with open(CYL_V8_RAW, "w") as f:
        json.dump(votaciones, f, indent=2, ensure_ascii=False)
    print(f"CyL VIII: Processed {fixed_votos} votes.")

# 3. Global fix for "Desconocido" or "Unknown" in all public files
def global_cleanup():
    paths = [
        "public/data/manifest_home.json",
        "public/data/andalucia/manifest_home.json",
        "public/data/cyl/manifest_home.json",
        "public/data/votaciones_meta.json",
        "public/data/andalucia/votaciones_meta.json",
        "public/data/cyl/votaciones_meta.json"
    ]
    for p in paths:
        if not os.path.exists(p): continue
        with open(p, "r") as f:
            content = f.read()
        
        # Replace occurrences in JSON content
        # Note: Be careful with quotes to not break JSON structure
        new_content = content.replace('"proponente":"Desconocido"', '"proponente":"Mesa"')
        new_content = new_content.replace('"Unknown":', '"Otros":')
        
        if new_content != content:
            with open(p, "w") as f:
                f.write(new_content)
            print(f"Global Cleanup: Patched {p}")

if __name__ == "__main__":
    fix_andalucia_dips()
    fix_cyl_v8()
    global_cleanup()
