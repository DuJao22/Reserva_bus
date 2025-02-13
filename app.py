from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2 import sql
import os
from Consultas import obter_poltronas_com_dados

app = Flask(__name__)
app.secret_key = 'chave_secreta'

# Configurações do banco de dados PostgreSQL
DB_HOST = "dpg-cukn8dqn91rc73at9ca0-a.oregon-postgres.render.com"
DB_NAME = "reserva_buss"
DB_USER = "reserva_buss_user"
DB_PASSWORD = "lPGSnYEbsyHqohl2PPVb559392YuoNhM"
DB_PORT = 5432

# Função para conectar ao banco de dados
def conectar_bd():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

# Criar tabelas no banco de dados
def criar_tabelas():
    with conectar_bd() as con:
        cur = con.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                            id SERIAL PRIMARY KEY,
                            nome TEXT,
                            email TEXT UNIQUE,
                            senha TEXT,
                            tipo TEXT DEFAULT 'user',
                            idade INTEGER,
                            cidade TEXT)''')

        # Criar a tabela 'viagens'
        cur.execute('''CREATE TABLE IF NOT EXISTS viagens (
                            id SERIAL PRIMARY KEY,
                            origem TEXT,
                            destino TEXT,
                            data TEXT,
                            horario TEXT,
                            onibus TEXT)''')

        # Criar a tabela 'pontos_parada'
        cur.execute('''CREATE TABLE IF NOT EXISTS pontos_parada (
                            id SERIAL PRIMARY KEY,
                            viagem_id INTEGER,
                            parada TEXT,
                            valor REAL,
                            FOREIGN KEY(viagem_id) REFERENCES viagens(id))''')

        # Criar a tabela 'reservas'
        cur.execute('''CREATE TABLE IF NOT EXISTS reservas (
                            id SERIAL PRIMARY KEY,
                            usuario_id INTEGER,
                            viagem_id INTEGER,
                            poltrona INTEGER,
                            nome TEXT,
                            embarque TEXT,
                            desembarque TEXT,
                            status TEXT,
                            FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
                            FOREIGN KEY(viagem_id) REFERENCES viagens(id))''')

        # Criar a tabela 'reservas_pontos' com embarque e desembarque referenciando 'pontos_parada'
        cur.execute('''CREATE TABLE IF NOT EXISTS reservas_pontos (
                            id SERIAL PRIMARY KEY,
                            reserva_id INTEGER,
                            embarque_id INTEGER,
                            desembarque_id INTEGER,
                            FOREIGN KEY(reserva_id) REFERENCES reservas(id),
                            FOREIGN KEY(embarque_id) REFERENCES pontos_parada(id),
                            FOREIGN KEY(desembarque_id) REFERENCES pontos_parada(id))''')

        # Commit para salvar as mudanças
        con.commit()

        # Criar usuário administrador padrão se não existir
        try:
            cur.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (%s, %s, %s, %s)", 
                        ("Admin Buser", "Admin_buser", "ADM_BUSS", "admin"))
            con.commit()
        except psycopg2.errors.UniqueViolation:
            pass  # Se o admin já existir, não faz nada

criar_tabelas()

# Rota inicial
@app.route('/')
def index():
    return render_template('index.html')

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        con = conectar_bd()
        cur = con.cursor()
        cur.execute("SELECT * FROM usuarios WHERE email=%s AND senha=%s", (email, senha))
        usuario = cur.fetchone()
        con.close()
        
        if usuario:
            session['usuario_id'] = usuario[0]
            session['tipo'] = usuario[4]
            if usuario[4] == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('user'))
        else:
            flash('Login falhou', 'error')
    return render_template('login.html')

# Verificar poltronas disponíveis para uma viagem
@app.route('/verificar_poltronas/<viagem_id>', methods=['GET'])
def verificar_poltronas(viagem_id):
    con = conectar_bd()
    cur = con.cursor()
    cur.execute("SELECT poltrona, status FROM reservas WHERE viagem_id = %s", (viagem_id,))
    reservas = cur.fetchall()
    poltronas_ocupadas = [reserva[0] for reserva in reservas if reserva[1] == 'Confirmado']
    con.close()
    return {'poltronas_ocupadas': poltronas_ocupadas}

# Criar um novo usuário
@app.route('/criar_usuario', methods=['POST'])
def criar_usuario():
    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']
    cidade = request.form['cidade']
    
    con = conectar_bd()
    cur = con.cursor()
    
    try:
        cur.execute("INSERT INTO usuarios (nome, email, senha, cidade) VALUES (%s, %s, %s, %s)", (nome, email, senha, cidade))
        con.commit()
        con.close()
        return redirect(url_for('login'))
    except psycopg2.errors.UniqueViolation:
        con.close()
        flash("Erro: Usuário já existe", "error")
        return redirect(url_for('criar_usuario'))

# Rota do painel de administrador
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'usuario_id' in session and session['tipo'] == 'admin':
        usuario_id = session['usuario_id']
        
        # Conectar ao banco e buscar o nome do administrador
        con = conectar_bd()
        cur = con.cursor()
        cur.execute("SELECT nome FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cur.fetchone()
        con.close()
        
        nome_usuario = usuario[0] if usuario else "Administrador"

        if request.method == 'POST':
            destino = request.form.get('destino', None)
            horario = request.form.get('horario', None)
            onibus = request.form.get('onibus', None)
            data = request.form.get('data', None)
            
            # Pega a lista de paradas
            paradas = request.form.getlist('paradas[]')

            # Verifica se os campos obrigatórios estão preenchidos
            if not (destino and horario and onibus and data):
                flash("Erro: Todos os campos são obrigatórios", "error")
                return redirect(url_for('admin'))
            
            # Conecta ao banco de dados
            con = conectar_bd()
            cur = con.cursor()
            
            # Insere a viagem no banco de dados
            cur.execute("INSERT INTO viagens (destino, horario, onibus, data) VALUES (%s, %s, %s, %s)", 
                        (destino, horario, onibus, data))
            con.commit()

            # Pega o ID da viagem inserida
            viagem_id = cur.fetchone()[0]

            # Insere as paradas associadas a essa viagem
            for parada in paradas:
                if parada:  # Verifica se a parada não está vazia
                    cur.execute("INSERT INTO pontos_parada (viagem_id, parada) VALUES (%s, %s)", 
                                (viagem_id, parada))
            
            con.commit()
            con.close()
            
            return redirect(url_for('admin'))
        
        # Buscar viagens e poltronas ocupadas
        con = conectar_bd()
        cur = con.cursor()
        cur.execute("SELECT * FROM viagens")
        viagens = cur.fetchall()

        poltronas_ocupadas = []
        cur.execute("SELECT poltrona FROM reservas WHERE status = 'Confirmado'")
        reservas = cur.fetchall()

        for reserva in reservas:
            poltronas_ocupadas.append(reserva[0])

        # Buscar reservas pendentes e incluir nome do usuário
        cur.execute('''SELECT r.*, u.nome, v.origem, v.destino 
               FROM reservas r
               JOIN usuarios u ON r.usuario_id = u.id
               JOIN viagens v ON r.viagem_id = v.id
               WHERE r.status = 'Pendente' ''')
        reservas_pendentes = cur.fetchall()

        con.close()

        reserva = obter_poltronas_com_dados()
        print(reservas_pendentes)
        
        return render_template('admin.html', 
                               viagens=viagens, 
                               poltronas_ocupadas=poltronas_ocupadas, 
                               reservas_pendentes=reservas_pendentes, 
                               nome_usuario=nome_usuario,
                               reserva=reserva)
    
    return redirect(url_for('login'))

# Rota do painel do usuário
@app.route('/user')
def user():
    if 'usuario_id' in session:
        usuario_id = session['usuario_id']
        con = conectar_bd()
        cur = con.cursor()

        # Buscar nome do usuário
        cur.execute("SELECT nome FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cur.fetchone()
        nome_usuario = usuario[0] if usuario else "Usuário"
        
        # Buscar viagens disponíveis
        con = conectar_bd()
        cur = con.cursor()
        cur.execute("SELECT * FROM viagens")
        viagens = cur.fetchall()

        # Buscar reservas do usuário
        cur.execute("SELECT r.*, viagens.origem, viagens.destino, viagens.data FROM reservas r JOIN viagens ON r.viagem_id = viagens.id WHERE r.usuario_id = %s", (usuario_id,))

        reservas = cur.fetchall()    
        
        # Criar um dicionário para armazenar pontos de embarque e desembarque por viagem
        pontos_viagens = {}

        for viagem in viagens:
            viagem_id = viagem[0]

            # Buscar pontos de embarque e desembarque ordenados
            cur.execute("SELECT parada FROM pontos_parada WHERE viagem_id = %s ORDER BY id", (viagem_id,))
            pontos = [row[0] for row in cur.fetchall()]

            pontos_viagens[viagem_id] = pontos  # Salva os pontos disponíveis na viagem

        # Criar dicionário de poltronas ocupadas por viagem
        poltronas_ocupadas = {}
        cur.execute("SELECT viagem_id, poltrona FROM reservas")
        todas_reservas = cur.fetchall()

        for viagem_id, poltrona in todas_reservas:
            if viagem_id not in poltronas_ocupadas:
                poltronas_ocupadas[viagem_id] = []
            poltronas_ocupadas[viagem_id].append(poltrona)

        # Lógica para filtrar os pontos de embarque e desembarque
        pontos_embarque_desembarque = {}
        for viagem_id, pontos in pontos_viagens.items():
            pontos_embarque_desembarque[viagem_id] = {}
            for i, ponto in enumerate(pontos):
                # Considerando o ponto de embarque
                embarque = ponto
                # Pegando os pontos restantes após o embarque
                pontos_restantes = pontos[i + 1:]
                pontos_embarque_desembarque[viagem_id][embarque] = pontos_restantes

        con.close()
        print(reservas)
        return render_template('user.html', viagens=viagens, reservas=reservas, 
                               nome_usuario=nome_usuario, poltronas_ocupadas=poltronas_ocupadas,
                               pontos_viagens=pontos_viagens, pontos_embarque_desembarque=pontos_embarque_desembarque)  # Passando a lógica de embarque/desembarque

    return redirect(url_for('login'))

@app.route('/reservar', methods=['POST'])
def reservar():
    if 'usuario_id' in session:
        usuario_id = session['usuario_id']
        viagem_id = request.form['viagem_id']
        poltrona = request.form['poltrona']
        nome = request.form['nome']
        embarque = request.form['embarque']  # O embarque é o ID do ponto de parada
        desembarque = request.form['desembarque']  # O desembarque é o ID do ponto de parada

        # Conectar ao banco de dados
        con = conectar_bd()
        cur = con.cursor()

        # Verificar se a poltrona já está reservada
        cur.execute("SELECT * FROM reservas WHERE viagem_id = %s AND poltrona = %s", (viagem_id, poltrona))
        reserva_existente = cur.fetchone()
        if reserva_existente:
            flash("Erro: Poltrona já reservada", "error")
            return redirect(url_for('user'))  # Redireciona para a página do usuário com a mensagem de erro

        # Inserir a reserva na tabela de reservas com o status 'Pendente'
        cur.execute("INSERT INTO reservas (usuario_id, viagem_id, poltrona, nome, embarque, desembarque, status) VALUES (%s, %s, %s, %s, %s, %s, 'Pendente')", 
                    (usuario_id, viagem_id, poltrona, nome, embarque, desembarque))
        reserva_id = cur.fetchone()[0]  # ID da reserva recém criada

        # Inserir os pontos de embarque e desembarque na tabela 'reservas_pontos'
        cur.execute("INSERT INTO reservas_pontos (reserva_id, embarque_id, desembarque_id) VALUES (%s, %s, %s)", 
                    (reserva_id, embarque, desembarque))

        # Commit das mudanças e fechamento da conexão
        con.commit()
        con.close()

        # Redirecionar para a página do usuário
        return redirect(url_for('user'))
    return redirect(url_for('login'))

# Confirmar reserva (somente administrador)
@app.route('/confirmar_reserva', methods=['POST'])
def confirmar_reserva():
    if 'usuario_id' in session and session['tipo'] == 'admin':
        reserva_id = request.form['reserva_id']
        con = conectar_bd()
        cur = con.cursor()
        cur.execute("UPDATE reservas SET status='Confirmado' WHERE id=%s", (reserva_id,))
        con.commit()
        con.close()
        return redirect(url_for('admin'))
    return redirect(url_for('login'))

# Rota de logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

#######################################################

@app.route('/adicionar_ponto_parada', methods=['POST'])
def adicionar_ponto_parada():
    if 'usuario_id' in session and session['tipo'] == 'admin':
        viagem_id = request.form['viagem_id']
        parada = request.form['parada']
        valor = request.form['valor']

        con = conectar_bd()
        cur = con.cursor()
        cur.execute("INSERT INTO pontos_parada (viagem_id, parada, valor) VALUES (%s, %s, %s)", 
                    (viagem_id, parada, valor))
        con.commit()
        con.close()

        return redirect(url_for('admin'))
    return redirect(url_for('login'))

@app.route('/pontos_parada/<viagem_id>', methods=['GET'])
def pontos_parada(viagem_id):
    con = conectar_bd()
    cur = con.cursor()
    cur.execute("SELECT id, parada, valor FROM pontos_parada WHERE viagem_id = %s", (viagem_id,))
    pontos = cur.fetchall()
    con.close()

    return {'pontos': [{'id': p[0], 'parada': p[1], 'valor': p[2]} for p in pontos]}

#######################################################
# Executar o app
if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")
