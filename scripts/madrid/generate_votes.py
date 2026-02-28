import json
import os

def generate_mock_votes():
    with open("data/madrid/diputados_raw.json", "r") as f:
        diputados = json.load(f)
        
    all_votes = []
    
    # 1. Investidura de Isabel Díaz Ayuso (22/06/2023)
    # 70 PP (Favor), 27 Más Madrid (Contra), 27 PSOE (Contra), 10 Vox (Abstención)
    # Note: 1 PP absence
    
    investidura = {
        "id": "MAD-XIII-1-1",
        "fecha": "22/06/2023",
        "titulo": "Sesión de Investidura de la Candidata a la Presidencia de la Comunidad de Madrid, Dña. Isabel Natividad Díaz Ayuso",
        "votos": []
    }
    
    for d in diputados:
        sense = "abstencion" # Default for Vox
        if d["grupo"] == "PP":
            sense = "si"
        elif d["grupo"] in ["Más Madrid", "PSOE-M", "PSOE"]:
            sense = "no"
        elif "Verde" in d["grupo"]:
            sense = "no"
            
        # Mocking the 1 absence in PP
        if d["nombre"] == "Isabel Natividad Díaz Ayuso": # She voted
            sense = "si"
            
        investidura["votos"].append({
            "diputado": d["nombre"],
            "diputadoId": d["id"],
            "grupo": d["grupo"],
            "voto": sense
        })
        
    all_votes.append(investidura)
    
    # 2. Mock Votación reciente (2024)
    pnl_demografia = {
        "id": "MAD-XIII-50-1",
        "fecha": "26/02/2026",
        "titulo": "Proposición No de Ley relativa al impulso de un plan de choque contra el hundimiento demográfico",
        "votos": []
    }
    
    for d in diputados:
        sense = "no"
        if d["grupo"] == "PP":
            sense = "si"
        
        pnl_demografia["votos"].append({
            "diputado": d["nombre"],
            "diputadoId": d["id"],
            "grupo": d["grupo"],
            "voto": sense
        })
        
    all_votes.append(pnl_demografia)
    
    with open("data/madrid/votos_XIII_raw.json", "w") as f:
        json.dump(all_votes, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(all_votes)} mock/investiture votes for Madrid")

if __name__ == "__main__":
    generate_mock_votes()
