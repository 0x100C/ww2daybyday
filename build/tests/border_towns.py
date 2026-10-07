"""Town side-of-border assertions for 1 September 1939.

Each entry: (town, lat, lon, expected unit code). The political raster is
checked at each town; any mismatch fails the build. Towns are chosen on
both sides of every hand-digitised border.
"""
TOWNS_1939 = [
    # German-Polish border 1922-1939
    ("Wejherowo", 54.60, 18.24, "POL"), ("Lebork", 54.54, 17.75, "GER"), ("Leba", 54.76, 17.56, "GER"),
    ("Puck", 54.72, 18.41, "POL"), ("Hel", 54.61, 18.80, "POL"), ("Gdynia", 54.52, 18.53, "POL"),
    ("Kartuzy", 54.33, 18.20, "POL"), ("Bytow", 54.17, 17.49, "GER"), ("Koscierzyna", 54.12, 17.98, "POL"),
    ("Chojnice", 53.70, 17.56, "POL"), ("Czluchow", 53.66, 17.36, "GER"), ("Zlotow", 53.36, 17.04, "GER"),
    ("Sepolno", 53.45, 17.53, "POL"), ("Wiecbork", 53.35, 17.50, "POL"), ("Pila", 53.15, 16.74, "GER"),
    ("Naklo", 53.14, 17.60, "POL"), ("Bydgoszcz", 53.12, 18.01, "POL"), ("Czarnkow", 52.90, 16.56, "POL"),
    ("Trzcianka", 53.04, 16.46, "GER"), ("Wielen", 52.89, 16.15, "POL"), ("Krzyz", 52.88, 16.01, "GER"),
    ("Miedzyrzecz", 52.44, 15.58, "GER"), ("Miedzychod", 52.60, 15.89, "POL"), ("Zbaszyn", 52.25, 15.92, "POL"),
    ("Babimost", 52.16, 15.83, "GER"), ("Wolsztyn", 52.12, 16.12, "POL"), ("Wschowa", 51.80, 16.32, "GER"),
    ("Leszno", 51.84, 16.57, "POL"), ("Gora", 51.67, 16.54, "GER"), ("Rawicz", 51.61, 16.86, "POL"),
    ("Milicz", 51.53, 17.27, "GER"), ("Krotoszyn", 51.70, 17.44, "POL"), ("Ostrzeszow", 51.43, 17.93, "POL"),
    ("Sycow", 51.31, 17.72, "GER"), ("Kepno", 51.28, 17.99, "POL"), ("Byczyna", 51.11, 18.18, "GER"),
    ("Wierusz.", 51.29, 18.15, "POL"), ("Olesno", 50.88, 18.42, "GER"), ("Lubliniec", 50.67, 18.68, "POL"),
    ("Dobrodzien", 50.73, 18.44, "GER"), ("Tarnowskie Gory", 50.44, 18.86, "POL"), ("Bytom", 50.35, 18.92, "GER"),
    ("Chorzow", 50.30, 18.95, "POL"), ("Zabrze", 50.32, 18.79, "GER"), ("Gliwice", 50.29, 18.67, "GER"),
    ("Katowice", 50.26, 19.02, "POL"), ("Rybnik", 50.10, 18.54, "POL"), ("Raciborz", 50.09, 18.22, "GER"),
    ("Opole", 50.67, 17.93, "GER"), ("Wroclaw", 51.11, 17.03, "GER"), ("Poznan", 52.41, 16.93, "POL"),
    # Danzig
    ("Danzig", 54.35, 18.65, "DAN"), ("Sopot", 54.44, 18.56, "DAN"), ("Tczew", 54.09, 18.78, "POL"),
    ("Nowy Dwor Gd.", 54.21, 19.12, "DAN"), ("Malbork", 54.04, 19.03, "GER"), ("Elblag", 54.16, 19.40, "GER"),
    # East Prussia
    ("Kwidzyn", 53.73, 18.93, "GER"), ("Grudziadz", 53.48, 18.75, "POL"), ("Gniew", 53.84, 18.82, "POL"),
    ("Brodnica", 53.26, 19.40, "POL"), ("Ilawa", 53.60, 19.57, "GER"), ("Dzialdowo", 53.24, 20.17, "POL"),
    ("Nidzica", 53.36, 20.42, "GER"), ("Mlawa", 53.11, 20.38, "POL"), ("Kolno", 53.41, 21.93, "POL"),
    ("Pisz", 53.63, 21.81, "GER"), ("Grajewo", 53.65, 22.45, "POL"), ("Elk", 53.83, 22.36, "GER"),
    ("Suwalki", 54.10, 22.93, "POL"), ("Goldap", 54.31, 22.31, "GER"), ("Konigsberg", 54.71, 20.51, "GER"),
    # Memel and Lithuania
    ("Memel", 55.71, 21.13, "GER"), ("Silute", 55.35, 21.48, "GER"), ("Kretinga", 55.89, 21.24, "LTU"),
    ("Kaunas", 54.90, 23.90, "LTU"), ("Vilnius", 54.69, 25.28, "POL"), ("Trakai", 54.64, 24.93, "POL"),
    ("Sirvintos", 55.04, 24.95, "LTU"), ("Alytus", 54.40, 24.05, "LTU"), ("Druskininkai", 54.02, 23.97, "POL"),
    ("Sejny", 54.11, 23.35, "POL"), ("Lazdijai", 54.23, 23.52, "LTU"), ("Svencionys", 55.13, 26.16, "POL"),
    ("Utena", 55.50, 25.60, "LTU"), ("Zarasai", 55.73, 26.25, "LTU"),
    # Riga line
    ("Grodno", 53.68, 23.83, "POL"), ("Brest", 52.10, 23.69, "POL"), ("Pinsk", 52.11, 26.10, "POL"),
    ("Lida", 53.89, 25.30, "POL"), ("Baranavichy", 53.13, 26.01, "POL"), ("Molodechno", 54.31, 26.85, "POL"),
    ("Nesvizh", 53.22, 26.68, "POL"), ("Stowbtsy", 53.48, 26.74, "POL"), ("Minsk", 53.90, 27.56, "SOV"),
    ("Slutsk", 53.03, 27.56, "SOV"), ("Polotsk", 55.49, 28.78, "SOV"), ("Glubokoye", 55.14, 27.69, "POL"),
    ("Braslaw", 55.64, 27.04, "POL"), ("Lutsk", 50.75, 25.33, "POL"), ("Rivne", 50.62, 26.25, "POL"),
    ("Sarny", 51.34, 26.60, "POL"), ("Zhytomyr", 50.25, 28.66, "SOV"), ("Lviv", 49.84, 24.03, "POL"),
    ("Ternopil", 49.55, 25.59, "POL"), ("Stanislawow", 48.92, 24.71, "POL"), ("Kamianets-Podilskyi", 48.68, 26.58, "SOV"),
    ("Proskurov", 49.42, 26.99, "SOV"), ("Shepetivka", 50.18, 27.06, "SOV"),
    # Romania / USSR / Hungary
    ("Chernivtsi", 48.29, 25.94, "ROU"), ("Chisinau", 47.01, 28.86, "ROU"), ("Bender", 46.83, 29.46, "ROU"),
    ("Tiraspol", 46.84, 29.63, "SOV"), ("Izmail", 45.35, 28.84, "ROU"), ("Bilhorod-Dn.", 46.19, 30.34, "ROU"),
    ("Odessa", 46.48, 30.73, "SOV"), ("Uzhhorod", 48.62, 22.29, "HUN"), ("Mukachevo", 48.44, 22.72, "HUN"),
    ("Khust", 48.17, 23.29, "HUN"), ("Kosice", 48.72, 21.26, "HUN"), ("Komarno", 47.76, 18.12, "HUN"),
    ("Nove Zamky", 47.99, 18.16, "HUN"), ("Lucenec", 48.33, 19.67, "HUN"), ("Rimavska Sobota", 48.38, 20.02, "HUN"),
    ("Levice", 48.22, 18.60, "HUN"), ("Rožňava", 48.66, 20.53, "HUN"), ("Nitra", 48.31, 18.09, "SVK"),
    ("Bratislava", 48.15, 17.11, "SVK"), ("Presov", 49.00, 21.24, "SVK"), ("Zvolen", 48.58, 19.13, "SVK"),
    ("Michalovce", 48.75, 21.92, "SVK"), ("Trnava", 48.38, 17.59, "SVK"), ("Dobrich", 43.57, 27.83, "ROU"),
    ("Silistra", 44.12, 27.26, "ROU"), ("Varna", 43.21, 27.91, "BGR"), ("Cluj", 46.77, 23.60, "ROU"),
    # Bohemia-Moravia
    ("Prague", 50.08, 14.42, "PRO"), ("Brno", 49.19, 16.61, "PRO"), ("Ostrava", 49.83, 18.29, "PRO"),
    ("Olomouc", 49.59, 17.25, "PRO"), ("Plzen", 49.75, 13.38, "PRO"), ("Ceske Budejovice", 48.97, 14.47, "PRO"),
    ("Liberec", 50.77, 15.06, "GER"), ("Karlovy Vary", 50.23, 12.87, "GER"), ("Cheb", 50.08, 12.37, "GER"),
    ("Usti", 50.66, 14.03, "GER"), ("Opava", 49.94, 17.90, "GER"), ("Znojmo", 48.86, 16.05, "GER"),
    ("Hlucin", 49.90, 18.19, "GER"), ("Trutnov", 50.56, 15.91, "GER"), ("Cesky Krumlov", 48.81, 14.32, "GER"),
    ("Karvina", 49.85, 18.54, "POL"), ("Cesky Tesin", 49.75, 18.63, "POL"), ("Bohumin", 49.90, 18.36, "POL"),
    ("Frydek", 49.68, 18.35, "PRO"), ("Vienna", 48.21, 16.37, "GER"),
    # Finland, Baltic, USSR
    ("Vyborg", 60.71, 28.75, "FIN"), ("Sortavala", 61.70, 30.69, "FIN"), ("Terijoki", 60.17, 29.70, "FIN"),
    ("Leningrad", 59.94, 30.31, "SOV"), ("Petsamo", 69.50, 31.20, "FIN"), ("Murmansk", 68.97, 33.08, "SOV"),
    ("Pechory", 57.81, 27.60, "EST"), ("Ivangorod", 59.37, 28.21, "EST"), ("Pytalovo", 57.07, 27.92, "LVA"),
    ("Pskov", 57.82, 28.33, "SOV"), ("Tallinn", 59.44, 24.75, "EST"), ("Riga", 56.95, 24.11, "LVA"),
    ("Salla (old)", 66.83, 28.67, "FIN"), ("Kandalaksha", 67.15, 32.41, "SOV"),
    ("Suojarvi", 62.08, 32.37, "FIN"), ("Vidlitsa", 61.17, 32.42, "SOV"), ("Salmi", 61.37, 31.86, "FIN"),
    ("Porosozero", 62.73, 32.70, "SOV"), ("Kexholm", 61.03, 30.12, "FIN"), ("Toksovo", 60.15, 30.52, "SOV"),
    ("Petrozavodsk", 61.79, 34.36, "SOV"), ("Olonets", 60.98, 32.97, "SOV"),
    # Italy and Yugoslavia
    ("Fiume", 45.33, 14.43, "ITA"), ("Susak", 45.32, 14.47, "YUG"), ("Pula", 44.87, 13.85, "ITA"),
    ("Postojna", 45.78, 14.21, "ITA"), ("Idrija", 46.00, 14.03, "ITA"), ("Gorizia", 45.94, 13.62, "ITA"),
    ("Ljubljana", 46.05, 14.51, "YUG"), ("Krk", 45.03, 14.58, "YUG"), ("Cres", 44.96, 14.41, "ITA"),
    ("Zara", 44.12, 15.23, "ITA"), ("Split", 43.51, 16.44, "YUG"), ("Trieste", 45.65, 13.77, "ITA"),
    ("Tirana", 41.33, 19.82, "ALB"), ("Rhodes", 36.43, 28.22, "DOD"), ("Kos", 36.89, 27.29, "DOD"),
    ("Samos", 37.75, 26.98, "GRC"), ("Chios", 38.37, 26.13, "GRC"),
    # Morocco, Levant
    ("Tetouan", 35.57, -5.37, "SMA"), ("Tangier", 35.76, -5.81, "TNG"), ("Fez", 34.03, -5.00, "MAR"),
    ("Antakya", 36.20, 36.16, "TUR"), ("Aleppo", 36.20, 37.16, "SYR"), ("Beirut", 33.89, 35.50, "LBN"),
    ("Jerusalem", 31.78, 35.22, "PAL"), ("Amman", 31.95, 35.93, "TRJ"), ("Tobruk", 32.08, 23.96, "LBY"),
    ("Sidi Barrani", 31.61, 25.93, "EGY"),
]
