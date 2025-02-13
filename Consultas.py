import sqlite3
import os

# Criar diretório 'data' no diretório de trabalho atual
os.makedirs("data", exist_ok=True)

def conectar_bd():
    return sqlite3.connect('banco.db', check_same_thread=False)

def obter_poltronas_com_dados():
    with conectar_bd() as con:
        cur = con.cursor()
        
        # Consulta para obter todas as reservas
        cur.execute('''
            SELECT id, usuario_id, viagem_id, poltrona, nome, embarque, desembarque, status
            FROM reservas
        ''')
        
        resultado = cur.fetchall()
        
        reservas = []
        for row in resultado:
            reservas.append({
                "id": row[0],
                "usuario_id": row[1],
                "viagem_id": row[2],
                "numero": row[3],
                "nome": row[4],
                "embarque": row[5],
                "desembarque": row[6],
                "status": row[7]
            })
        
        return reservas
