import sqlite3

def conectar_bd():
    return sqlite3.connect('banco.db', check_same_thread=False)

def obter_poltronas_com_dados():
    with conectar_bd() as con:
        cur = con.cursor()
        
        # Consulta para obter as poltronas, passageiros e destinos
        cur.execute('''
            SELECT r.poltrona, u.nome AS passageiro, v.destino
            FROM reservas r
            JOIN usuarios u ON r.usuario_id = u.id
            JOIN viagens v ON r.viagem_id = v.id
        ''')
        
        resultado = cur.fetchall()
        
        poltronas = []
        for row in resultado:
            poltronas.append({
                "numero": row[0],
                "passageiro": row[1],
                "destino": row[2]
            })
        
        return poltronas


