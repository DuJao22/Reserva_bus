import sqlite3
import os

# Caminho do banco de dados
DB_PATH = "/var/data/banco.db"

# Cria a pasta /var/data caso não exista
os.makedirs("/var/data", exist_ok=True)

def conectar_bd():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

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
