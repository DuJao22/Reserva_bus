import psycopg2
from psycopg2 import sql

# Configurações do banco de dados PostgreSQL
DB_HOST = "dpg-cun5vslumphs73f05c6g-a"
DB_NAME = "reserva_buss_1"
DB_USER = "dujao_reserva_buss"
DB_PASSWORD = "qAaZHkci0E8hbUKUYrGUV1WhLzN0eaIe"
DB_PORT = 5432


def conectar_bd():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

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
