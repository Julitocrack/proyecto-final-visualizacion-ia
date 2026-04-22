Parte 1. Obtención y preparación de los datos

Fuente exacta: Football-Data.co.uk (Archivos históricos de la English Premier League).

URL: https://www.football-data.co.uk/englandm.php

Fecha de descarga: Miercoles 22 de abril del 2026

Formato original: Archivos planos CSV (formato E0.csv).

Condiciones de uso / Licencia: Datos de libre acceso provistos por Football-Data.co.uk para fines de investigación y modelado cuantitativo.

Documentación de limpieza y transformación: El procesamiento automatizado en Python (Pandas) consistió en la ingesta y concatenación de los archivos de las temporadas recientes. Se aplicó un filtrado para conservar exclusivamente variables ofensivas clave (HST: Tiros a puerta local, AST: Tiros a puerta visitante, HC: Córners local, AC: Córners visitante), el resultado al descanso (HTHG, HTAG) y las cuotas de cierre de Bet365 (B365H, B365A, B365D). Posteriormente, se generó un subconjunto de datos aislando los escenarios tácticos de interés: partidos donde el equipo perfilado como favorito por las cuotas de apuestas se encontraba en desventaja en el marcador al término del primer tiempo.

Reproducibilidad: El script limpieza_premier.py incluido en este repositorio contiene el código fuente completo. Cualquier usuario puede ejecutarlo localmente junto con los CSVs originales para replicar el dataset final.