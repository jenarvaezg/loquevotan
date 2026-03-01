import json
import os
import hashlib

# Data from previous Wikipedia fetch
WIKI_TEXT_X = """
Olga Abasolo Pozas | Podemos
Sonsoles Trinidad Aboín Aboín | PP
María Acín Carreras | Podemos
María Paloma Adrados Gautier | PP
Ignacio Jesús Aguado Crespo | Ciudadanos
María Josefa Aguado del Olmo | PP
María Victoria Ángeles Alonso Márquez | Ciudadanos
Daniel Álvarez Cabo | Ciudadanos
María Nadia Álvarez Padilla | PP
María Cristina Álvarez Sánchez | PP
María Isabel Andaluz Andaluz | PSOE
Miguel Ardanuy Pizarro | Podemos
María Isabel Ardid Jiménez | PSOE
José María Arribas del Barrio | PP
Álvaro César Ballarín Valcárcel | PP
Ana Belén Barbero Martín | PP
Jazmín Beirak Ulanosky | Podemos
Jacobo Ramón Beltrán Pedreira | PP
María Inés Berrio Fernández-Caballero | PP
José Manuel Berzal Andrade | PP
Eva María Borox Montoro | Ciudadanos
Pilar Busó Borús | PP
José Cabrera Orellana | PP
Raúl Camargo Fernández | Podemos
Ana Camins Martínez | PP
Marco Candela Pokorna | Podemos
Mónica Carazo Gómez | PSOE
María Eugenia Carballedo Berlanga | PP
María Lucía Inmaculada Casares Díaz | PSOE
José Carmelo Cepeda García de León | PSOE
María Cristina Cifuentes Cuencas | PP
Diego Cruz Torrijos | PSOE
Carla Delgado Gómez | PSOE
Emilio Delgado Orgaz | Podemos
María de las Mercedes Delgado Robles Sanguino | PP
Isabel Natividad Díaz Ayuso | PP
Laura Díaz Román | Podemos
José Ignacio Echeverría Echániz | PP
Marta María Escudero Díaz-Tejeiro | PP
Ramón Espinar Merino | Podemos
María Espinosa de la Llave | Podemos
Jesús Fermosel Díaz | PP
Lucía Fernández Fernández | PP
José Luis Fernández-Quejo del Pozo | PP
Eduardo Fernández Rubiño | Podemos
José Manuel Franco Pardo | PSOE
José Manuel Freire Campo | PSOE
Ángel Gabilondo Pujol | PSOE
Beatriz Galiana Blanco | Podemos
Mercedes Gallizo Llamas | PSOE
Ana García D'Atri | PSOE
Mónica García Gómez | Podemos
María Begoña García Martín | PP
María José García-Patrón Alcázar | PP
Pedro Pablo García-Rojo Garrido | PSOE
José Luis García Sánchez | PSOE
Ignacio García de Vinuesa Gardoqui | PP
Ángel Garrido García | PP
Beatriz Gimeno Reinoso | Podemos
Rafael Gomez Montoya | PSOE
Juan Antonio Gómez-Angulo Rodríguez | PP
José Ángel Gómez-Chamorro Torres | PSOE
Isabel Gema González González | PP
Mónica Silvana González González | PSOE
Bartolomé González Jiménez | PP
Miguel Ángel González Merino | PSOE
Dolores González Pastor | Ciudadanos
Jaime González Taboada | PP
Antonio Pablo González Terol | PP
Elena González-Moñux Vázquez | PP
Rosalía Gonzalo López | PP
Eduardo Benito Gutiérrez | Podemos
Raquel Huerta Bravo | Podemos
María Teresa de la Iglesia Vicente | Ciudadanos
Carlos Izquierdo Torres | PP
Rafael José Vélez | PSOE
Federico Jiménez de Parga Maseda | PP
Francisco Lara Casanova | Ciudadanos
María Isaura Leal Fernández | PSOE
María Pilar Liébana Montijano | PP
María Pilar Llop Cuenca | PSOE
Juan Lobato Gandarias | PSOE
Isidro López Fernández | Podemos
José Manuel López Rodrigo | Podemos
María Carmen López Ruiz | PSOE
Diego Lozano Pérez | PP
Teresa de Jesús Luis Rico | PP
Eva María Manguán Valderrama | PSOE
Marta Marbán de Frutos | Ciudadanos
Tomás Marcos Arias | Ciudadanos
Ana Isabel Mariño Ortega | PP
María Reyes Maroto Illera | PSOE
María Paz Martín Lozano | PSOE
Hugo Martínez Abarca | Podemos
Carmen Martínez Ten | PSOE
María Julia Martínez Torales | PSOE
Jesús Ricardo Megías Morales | Ciudadanos
María Carmen Mena Romero | PSOE
Anca Teodora Moldovan Feier | PP
Álvaro Moraga Valiente | PP
Jacinto Morano González | Podemos
Juan José Moreno Navarro | PSOE
María Encarnación Moya Nieto | PSOE
Pedro Muñoz Abrines | PP
Josefa Navarro Lanchas | PSOE
Modesto Nolla Estrada | PSOE
José Enrique Núñez Guijarro | PP
Pedro Núñez-Morgades García de Leaniz | Ciudadanos
Roberto Núñez Sánchez | Ciudadanos
Eduardo Oficialdegui Alonso de Celada | PP
Alberto Oliver Gómez de la Vega | Podemos
Luis del Olmo Flórez | PP
María Gádor Ongil Cores | PP
Miguel Ongil López | Podemos
Daniel Ortiz Espejo | PP
Enrique Matías Ossorio Crespo | PP
Pablo Padilla Estrada | Podemos
Josefa Pardo Ortiz | PSOE
Ricardo Vicente Peña Mari | PSOE
Luis Peral Guerra | PP
Ana Isabel Pérez Baos | PP
David Pérez García | PP
María Regina Plañiol de Lacalle | PP
José Quintana Viar | PSOE
Manuel Francisco Quintanar Díez | PP
Eduardo Raboso García-Vaquero | PP
Ángel Ramos Sánchez | PP
María Isabel Redondo Alcaide | PP
Alberto Reyero Zubiri | Ciudadanos
Enrique Rico García-Hierro | PSOE
Ana Rodríguez Durán | Ciudadanos
Nicolás Rodríguez García | PSOE
Belén Rodríguez Palomino | PP
Pedro Manuel Rollán Ojeda | PP
Juan Ramón Rubio Ruiz | Ciudadanos
Esther Ruiz Fernández | Ciudadanos
Miguel Ángel Ruiz López | PP
Lorena Ruiz-Huerta García de Viedma | Podemos
Cecilia Salazar-Alonso Revuelta | Podemos
Pilar Sánchez Acera | PSOE
Alejandro Sánchez Fernández | PP
Alejandro Sánchez Pérez | Podemos
Carmen San José Pérez | Podemos
Diego Sanjuanbenito Bonal | PP
Pedro Santín Fernández | PSOE
Francisco de Borja Sarasola Jáudenes | PP
Juan Segovia Noriega | PSOE
Clara Serra Sánchez | Podemos
Isabel Serra Sánchez | Podemos
José Tomás Serrano Guio | PP
Alfonso Carlos Serrano Sánchez-Capuchino | PP
Elena Sevillano de las Heras | Podemos
Juan Soler-Espiauba Gallo | PP
Susana Solís Pérez | Ciudadanos
Lucila Toledo Moreno | PP
Eva Tormo Mairena | PP
José Tortosa de la Iglesia | PP
Juan Trinidad Martos | Ciudadanos
Juan Van-Halen Acedo | PP
Enrique Veloso Lozano | Ciudadanos
Daniel Vicente Viondi | PSOE
Agustín Vinagre Alcázar | PSOE
César Zafra Fernández | Ciudadanos
"""

WIKI_TEXT_XI = """
María Acín Carrera | Más Madrid
María Paloma Adrados Gautier | PP
Ignacio Aguado Crespo | Ciudadanos
Rocío Albert López | PP
Carolina Alonso Alonso | Podemos
Victoria Alonso Márquez | Ciudadanos
María Nadia Álvarez Padilla | PP
José Ignacio Arias Moreno | Vox
Miguel Luis Arranz Sánchez | PSOE-M
José María Arribas del Barrio | PP
Isabel Aymerich D'Olhaberriague | PSOE-M
Eva Bailén Fernández | Ciudadanos
María Carmen Barahona Prol | PSOE-M
Jazmín Beirak Ulanosky | Más Madrid
Jaime María de Berenguer de Santiago | Vox
Marta Bernardo Llorente | PSOE-M
Borja Luis Cabezón Royo | PSOE-M
Sergio Brabezo Carballo | Ciudadanos
Mariano Calabuig Martínez | Vox
Ana Camins Martínez | PP
Francisco Javier Cañadas Martín | Podemos
María Eugenia Carballedo Berlanga | PP
María Yobana Carril Antelo | Vox
María Carmen Castell Díaz | PP
María Llanos Castellanos Garijo | PSOE-M
Purificación Causapié Lopesino | PSOE-M
José Carmelo Cepeda García de León | PSOE-M
Sonia Conejero Palero | PSOE-M
Diego Cruz Torrijos | PSOE-M
Ana María Cuartero Lorenzo | Vox
Jorge Arturo Cutillas Cordón | Vox
Carla Delgado Gómez | PSOE-M
Emilio Delgado Orgaz | Más Madrid
Isabel Natividad Díaz Ayuso | PP
Carlos Díaz-Pache Gosende | PP
Miguel Díaz Martín | Ciudadanos
Matilde Isabel Díaz Ojeda | PSOE-M
Macarena Elvira Rubio | PSOE-M
David Erguido Cano | PP
Íñigo Errejón Galván | Más Madrid
María Yolanda Estrada Madrid | PP
Fernando Fernández Lara | PSOE-M
Emy Fernández-Luna Abellán | Ciudadanos
Eduardo Fernández Rubiño | Más Madrid
Diego Figuera Álvarez | Más Madrid
José Manuel Freire Campo | PSOE-M
Ángel Gabilondo Pujol | PSOE-M
Ana Isabel García García | Ciudadanos
Mónica García Gómez | Más Madrid
José Luis García Sánchez | PSOE-M
Ángel Garrido García | Ciudadanos
Beatriz Gimeno Reinoso | Podemos
Alicia Gómez Benítez | Más Madrid
José Ángel Gómez Chamorro Torres | PSOE-M
Araceli Gómez García | Ciudadanos
Rafael Gómez Montoya | PSOE-M
Pablo Gómez Perpiñá | Más Madrid
Cristina González Álvarez | PSOE-M
Javier Guardiola Arévalo | PSOE-M
Santiago Eduardo Gutiérrez Benito | Más Madrid
Pablo Gutiérrez de Cabiedes Hidalgo de Caviedes | Vox
Roberto Hernández Blázquez | Ciudadanos
Juan Miguel Hernández de León | PSOE-M
Íñigo Henríquez de Luna Losada | Vox
Raquel Huerta Bravo | Más Madrid
María Yolanda Ibarrola de la Fuente | PP
Carlos Izquierdo Torres | PP
Hana Jalloul Muro | PSOE-M
Gádor Pilar Joya Verde | Vox
Pilar Liébana Soto | Ciudadanos
Vanessa Lillo Gómez | IU-Madrid
Pilar Llop Cuenca | PSOE-M
María Carmen López Ruiz | PSOE-M
Javier Luengo Vicente | Ciudadanos
Marta Marbán de Frutos | Ciudadanos
Tomás Marcos Arias | Ciudadanos
Hugo Martínez Abarca | Más Madrid
Ricardo Megías Morales | Ciudadanos
María Carmen Mena Romero | PSOE-M
María Luisa Mercado Merino | PSOE-M
Rocío Monasterio San Martín | Vox
Álvaro Moraga Valiente | PP
Lorena Morales Porro | PSOE-M
Jacinto Morano González | Podemos
Juan José Moreno Navarro | PSOE-M
Jorge Moruno Danzi | Más Madrid
María Encarnación Moya Nieto | PSOE-M
Pedro Muñoz Abrines | PP
María Dolores Navarro Ruiz | PP
Almudena Negro Konrad | PP
Modesto Nolla Estrada | PSOE-M
José Enrique Núñez Guijarro | PP
Roberto Núñez Sánchez | Ciudadanos
Regina Otaola Muguerza | PP
Enrique Matías Ossorio Crespo | PP
Luis Pacheco Torres | Ciudadanos
Tamara Pardo Blázquez | Ciudadanos
María Pastor Valdés | Más Madrid
Javier Pérez Gallardo | Vox
David Pérez García | PP
Alodia Pérez Muñoz | Más Madrid
Daniel Portero de la Torre | PP
Eduardo Raboso García-Baquero | PP
Clara Ramas San Miguel | Más Madrid
Alberto Reyero Zubiri | Ciudadanos
Enrique Rico García Hierro | PSOE-M
Pedro Manuel Rollán Ojeda | PP
Jorge Rodrigo Domínguez | PP
Ana Rodríguez Durán | Ciudadanos
Nicolás Rodríguez García | PSOE-M
José Manuel Rodríguez Uribes | PSOE-M
Alicia Verónica Rubio Calle | Vox
Juan Rubio Ruiz | Ciudadanos
Esther Ruiz Fernández | Ciudadanos
Pilar Sánchez Acera | PSOE-M
Alicia Sánchez-Camacho Pérez | PP
Soledad Sánchez Maroto | IU-Madrid
Tania Sánchez Melero | Más Madrid
Alejandro Sánchez Pérez | Más Madrid
José Antonio Sánchez Serrano | PP
Diego Sanjuanbenito Bonal | PP
Carlota Santiago Camacho | Ciudadanos
Jaime Miguel de los Santos González | PP
Clara Serra Sánchez | Más Madrid
Isabel Serra Sánchez | Podemos
Alfonso Carlos Serrano Sánchez-Capuchino | PP
Héctor Tejero Franco | Más Madrid
Francisco Tomás-Valiente Lanuza | PSOE-M
Juan Trinidad Martos | Ciudadanos
Enrique Veloso Lozano | Ciudadanos
Agustín Vinagre Alcázar | PSOE-M
César Zafra Hernández | Ciudadanos
"""

WIKI_TEXT_XII = """
María Acín Carrera | Más Madrid
María Paloma Adrados Gautier | PP
Carolina Alonso Alonso | Podemos
Loreto Arenillas Gómez | Más Madrid
José Ignacio Arias Moreno | Vox
José María Arribas del Barrio | PP
Gonzalo Babé Romero | Vox
Álvaro Ballarín Valcárcel | PP
María Carmen Barahona Prol | PSOE-M
Jazmín Beirak Ulanosky | Más Madrid
Manuela Bergerot Uncal | Más Madrid
Marta Bernardo Llorente | PSOE-M
María del Mar Blanco Garrido | PP
Sergio Brabezo Carballo | PP
Miriam Bravo Sánchez | PP
Tomás Burgos Beteta | PP
Mariano Calabuig Martínez | Vox
Ana Camins Martínez | PP
María Eugenia Carballedo Berlanga | PP
María Carmen Castell Díaz | PP
Ignacio Catalá Martínez | PP
Jesús Celada Pérez | PSOE-M
José Carmelo Cepeda García de León | PSOE-M
Orlando Chacón Tabares | PP
Ana Collado Jiménez | PP
Sonia Conejero Palero | PSOE-M
Pedro María Corral Corral | PP
Mirina Cortés Ortega | PP
Diego Cruz Torrijos | PSOE-M
Ana María Cuartero Lorenzo | Vox
Jorge Arturo Cutillas Cordón | Vox
Ana Dávila-Ponce de León Municio | PP
Jaime María de Berenguer de Santiago | Vox
Jaime de los Santos González | PP
Emilio Delgado Orgaz | Más Madrid
Isabel Natividad Díaz Ayuso | PP
Matilde Isabel Díaz Ojeda | PSOE-M
Alberto Escribano García | PP
María Yolanda Estrada Madrid | PP
Lucía Soledad Fernández Alonso | PP
Fernando Fernández Lara | PSOE-M
Eduardo Fernández Rubiño | Más Madrid
Javier Fernández-Lasquetty | PP
Diego Figuera Álvarez | Más Madrid
Francisco Galeote Perea | PP
Mónica García Gómez | Más Madrid
José Luis García Sánchez | PSOE-M
Paloma García Villa | Podemos
Beatriz Gimeno Reinoso | Podemos
Pablo Gómez Perpiñá | Más Madrid
Cristina González Álvarez | PSOE-M
Carlos González Maestre | PP
Carlos González Pereira | PP
Carla Isabel Greciano Barrado | PP
Javier Guardiola Arévalo | PSOE-M
Santiago Eduardo Gutiérrez Benito | Más Madrid
Pablo Gutiérrez de Cabiedes Hidalgo de Caviedes | Vox
Íñigo Henríquez de Luna Losada | Vox
Lorena Heras Sedano | PP
Raquel Huerta Bravo | Más Madrid
Carlos Izquierdo Torres | PP
Alejandra Jacinto Uranga | Podemos
Hana Jalloul Muro | PSOE-M
Gádor Pilar Joya Verde | Vox
Vanessa Lillo Gómez | IU-Madrid
Juan Lobato Gandarias | PSOE-M
Enrique López López | PP
María del Carmen López Ruiz | PSOE-M
Marta Marbán de Frutos | PP
Paloma Martín Martín | PP
Hugo Martínez Abarca | Más Madrid
Serigne Mbaye Diouf | Podemos
María Carmen Mena Romero | PSOE-M
José Virgilio Menéndez Medrano | PP
Rocío Monasterio San Martín | Vox
Silvia Monterrubio Hernando | PSOE-M
Álvaro Moraga Valiente | PP
Lorena Morales Porro | PSOE-M
Jacinto Morano González | Podemos
Agustín Moreno García | Podemos
Jorge Moruno Danzi | Más Madrid
Pedro Muñoz Abrines | PP
Almudena Negro Konrad | PP
María del Mar Nicolás Robledano | PP
Janette Novo Castillo | PP
Noelia Núñez González | PP
José Enrique Núñez Guijarro | PP
Alberto Oliver Gómez de la Vega | Más Madrid
Enrique Matías Ossorio Crespo | PP
Javier Padilla Bernáldez | Más Madrid
Gonzalo Pastor Barahona | PSOE-M
María Pastor Valdés | Más Madrid
Juan Antonio Peña Ochoa | PP
Juana Beatriz Pérez Abraham | PP
Javier Pérez Gallardo | Vox
David Pérez García | PP
Alodia Pérez Muñoz | Más Madrid
Ignacio José Pezuela Cabañes | PP
Judit Piquet Flores | PP
Esther Platero San Román | PP
Daniel Portero de la Torre | PP
Miriam Rabaneda Gudiel | PP
Eduardo Raboso García-Baquero | PP
Ángel Ramos Sánchez | PP
Miguel Ángel Recuenco Checa | PP
María Isabel Redondo Alcaide | PP
Enrique Rico García Hierro | PSOE-M
Santiago José Rivero Cruz | PSOE-M
Encarnación Rivero Flor | PP
Jorge Rodrigo Domínguez | PP
Esther Rodríguez Moreno | Más Madrid
Alicia Verónica Rubio Calle | Vox
José Luis Ruiz Bartolomé | Vox
Enrique Ruiz Escudero | PP
Pilar Sánchez Acera | PSOE-M
Antonio Sánchez Domínguez | Más Madrid
Soledad Sánchez Maroto | IU-Madrid
Tania Sánchez Melero | Más Madrid
Alejandro Sánchez Pérez | Más Madrid
Alicia Sánchez-Camacho Pérez | PP
Diego Sanjuanbenito Bonal | PP
Jesús Santos Gimeno | Podemos
Carlos Segura Gutiérrez | PP
Alejandra Serrano Fernández | PP
Alfonso Carlos Serrano Sánchez-Capuchino | PP
Enrique Serrano Sánchez-Tembleque | PP
Juan Soler-Espiauba Gallo | PP
Begoña Estefanía Suárez Menéndez | PSOE-M
Héctor Tejero Franco | Más Madrid
Paloma Tejero Toledo | PP
Alicia Torija López | Más Madrid
Elisa Adela Vigil González | PP
Manuela Villa Acosta | PSOE-M
Agustín Vinagre Alcázar | PSOE-M
José Manuel Zarzoso Revenga | PP
Teresa de Jesús Zurita Ramón | Más Madrid
"""

def generate_diputados():
    all_diputados = []
    
    legs_data = [
        ("10", WIKI_TEXT_X),
        ("11", WIKI_TEXT_XI),
        ("12", WIKI_TEXT_XII),
        ("13", None) # Will merge with current XIII
    ]
    
    # Load current XIII to merge
    current_xiii = []
    if os.path.exists("data/madrid/diputados_raw.json"):
        with open("data/madrid/diputados_raw.json", "r") as f:
            current_xiii = json.load(f)
            
    for nleg, text in legs_data:
        if text:
            lines = text.strip().split('\n')
            for line in lines:
                if '|' not in line: continue
                parts = line.split('|')
                name = parts[0].strip()
                party = parts[1].strip()
                
                clean_name = name.replace(' ', '').replace(',', '').replace('.', '')
                name_hash = hashlib.md5(name.encode()).hexdigest()[:4].upper()
                d_id = f"MAD-{nleg}-" + clean_name[:15].upper() + "-" + name_hash
                
                all_diputados.append({
                    "id": d_id,
                    "nombre": name,
                    "grupo": party,
                    "nlegis": nleg,
                    "foto": None,
                    "provincia": "Madrid"
                })
        else:
            # Handle XIII from the existing file but update IDs to be consistent
            for d in current_xiii:
                name = d["nombre"]
                clean_name = name.replace(' ', '').replace(',', '').replace('.', '')
                name_hash = hashlib.md5(name.encode()).hexdigest()[:4].upper()
                d_id = f"MAD-13-" + clean_name[:15].upper() + "-" + name_hash
                d["id"] = d_id
                all_diputados.append(d)
                
    with open("data/madrid/diputados_raw.json", "w") as f:
        json.dump(all_diputados, f, indent=2, ensure_ascii=False)
    print(f"Total historical Madrid deputies: {len(all_diputados)}")

if __name__ == "__main__":
    generate_diputados()
