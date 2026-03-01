import json
import os

# Data from Wikipedia web_fetch
WIKI_TEXT = """
María Acín Carrera | Más Madrid
Rocío Albert López | PP
Esteban Álvarez León | PSOE-M
José Ignacio Arias Moreno | Vox
José María Arribas del Barrio | PP
Jonatan Alberto Arroyo Perea | PP
Álvaro Ballarín Valcárcel | PP
Jazmín Beirak Ulanosky | Más Madrid
Manuela Bergerot Uncal | Más Madrid
Marta Bernardo Llorente | PSOE-M
María del Mar Blanco Garrido | PP
Sara Bonmati García | PSOE-M
Beatriz Borrás Vergel | Más Madrid
Miriam Bravo Sánchez | PP
Tomás Burgos Beteta | PP
Isabel Sofía Cadórniga Varela | PSOE-M
Mariano Calabuig Martínez | Vox
María Eugenia Carballedo Berlanga | PP
Marta Carmona Ossorio | Más Madrid
María de los Llanos Castellanos Garijo | PSOE-M
Laura Castilla Rodríguez | PP
Ignacio Catalá Martínez | PP
Jesús Celada Pérez | PSOE-M
José Carmelo Cepeda García de León | PSOE-M
Ana Collado Jiménez | PP
Pedro María Corral Corral | PP
Mirina Cortés Ortega | PP
Diego Cruz Torrijos | PSOE-M
Ana María Cuartero Lorenzo | Vox
Ramón Cubián Martínez | PP
Jorge Arturo Cutillas Cordón | Vox
Ana Dávila-Ponce de León Municio | PP
Paula Raquel de las Heras Tundidor | PP
Jaime de los Santos González | PP
Carla Delgado Gómez | Más Madrid
Emilio Delgado Orgaz | Más Madrid
Isabel Natividad Díaz Ayuso | PP
Carlos Díaz-Pache Gosende | PP
María del Mar Espinar Mesa-Moles | PSOE-M
Gustavo Alaín Eustache Soteldo | PP
Alma Lucía Ezcurra Almansa | PP
Fernando Fernández Lara | PSOE-M
Javier Fernández-Lasquetty | PP
Diego Figuera Álvarez | Más Madrid
José Antonio Fúster Lamelas | Vox
Francisco Galeote Perea | PP
Jorge García Díaz | PP
Mónica García Gómez | Más Madrid
Rafael García González | PP
Miguel Ángel García Martín | PP
Oliva Cristina García Robredo | PP
José Luis García Sánchez | PSOE-M
Pablo Gómez Perpinyà | Más Madrid
Cristina González Álvarez | PSOE-M
Jimena González Gómez | Más Madrid
Carlos González Maestre | PP
María Belén González Moreno | Vox
Javier Guardiola Arévalo | PSOE-M
Laura Gutiérrez Barreno | PP
Santiago Eduardo Gutiérrez Benito | Más Madrid
Íñigo Henríquez de Luna Losada | Vox
María Yolanda Ibarrola de la Fuente | PP
María Tatiana Jiménez Liébana | PSOE-M
Mónica Lavín Moreno-Torres | PP
Juan Lobato Gandarias-Sánchez | PSOE-M
Miguel López-Valverde Argüeso | PP
Leticia Lorenzo Brito | PSOE-M
Marta Lozano Sabroso | Más Madrid
Marta Marbán de Frutos | PP
Raúl Martín Galán | PP
Guillermo Martín Jiménez | PSOE-M
Paloma Martín Martín | PP
Hugo Martínez Abarca | Más Madrid
Rafael Martínez Pérez | PSOE-M
Carlos Daniel Martínez Rodríguez | PP
María Carmen Mena Romero | PSOE-M
José Virgilio Menéndez Medrano | PP
Ana Belén Millán Arroyo | PP
Rocío Monasterio San Martín | Vox
Silvia Monterrubio Hernando | PSOE-M
Lorena Morales Porro | PSOE-M
Jesús Moreno García | PP
Carlos Moreno Vinués | PSOE-M
Jorge Moruno Danzi | Más Madrid
Pedro Muñoz Abrines | PP
Juan José Murillo Moreno | PP
Carlos Novillo Piris | PP
José Enrique Núñez Guijarro | PP
Rafael Núñez Huesca | PP
Miguel Olite Lumbreras | PP
Alberto Oliver Gómez de la Vega | Más Madrid
José María Ortiz Claver | PP
Enrique Matías Ossorio Crespo | PP
Javier Padilla Bernáldez | Más Madrid
Pablo José Padilla Estrada | Más Madrid
Diana Carol Paredes Choquehuanca | Más Madrid
David Jonathan Parry Lafont | PP
Carlota Pasarón González | PP
María Pastor Valdés | Más Madrid
Juana Beatriz Pérez Abraham | PP
Isabel Pérez Moñino-Aranda | Vox
Alodia Pérez Muñoz | Más Madrid
Susana Pérez Quislant | PP
Esther Platero San Román | PP
Daniel Portero de la Torre | PP
Pablo Posse Praderas | PP
Eduardo Raboso García-Baquero | PP
Patricia Isaura Reyes Rivera | PP
Santiago José Rivero Cruz | PSOE-M
Jorge Rodrigo Domínguez | PP
Daniel Rodríguez Asensio | PP
Esther Rodríguez Moreno | Más Madrid
Daniel Rubio Caballero | PSOE-M
José Luis Ruiz Bartolomé | Vox
Enrique Ruiz Escudero | PP
Miguel Ángel Rumayor Fernández | PP
Sandra Samboal Ugena | PP
Antonio Sánchez Domínguez | Más Madrid
Alejandro Sánchez Pérez | Más Madrid
Emilia Sánchez Prieto | PSOE-M
José Antonio Sánchez Serrano | PP
Alicia Sánchez-Camacho Pérez | PP
Paz Serra Portilla | Más Madrid
Alfonso Carlos Serrano Sánchez-Capuchino | PP
Héctor Tejero Franco | Más Madrid
Alberto Tomé González | PP
Alicia Torija López | Más Madrid
Ignacio Vázquez Casavilla | PP
Isabel Vega de la Vara | PP
Ana María Velasco Vidal-Abarca | Vox
Elisa Adela Vigil González | PP
Manuela Villa Acosta | PSOE-M
Agustín Vinagre Alcázar | PSOE-M
Nikolay Yordanov Atanasov | PP
María Mercedes Zarzalejo Carbajo | PP
"""

def generate_diputados():
    lines = WIKI_TEXT.strip().split('\n')
    diputados = []
    
    for line in lines:
        if '|' not in line: continue
        parts = line.split('|')
        name = parts[0].strip()
        party = parts[1].strip()
        
        # Simple ID generation based on name
        import hashlib
        clean_name = name.replace(' ', '').replace(',', '').replace('.', '')
        name_hash = hashlib.md5(name.encode()).hexdigest()[:4].upper()
        d_id = "MAD-13-" + clean_name[:15].upper() + "-" + name_hash
        
        diputados.append({
            "id": d_id,
            "nombre": name,
            "grupo": party,
            "nlegis": "13",
            "foto": None
        })
        
    os.makedirs("data/madrid", exist_ok=True)
    with open("data/madrid/diputados_raw.json", "w") as f:
        json.dump(diputados, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(diputados)} deputies for Madrid")

if __name__ == "__main__":
    generate_diputados()
