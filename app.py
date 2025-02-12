from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import sqlitecloud
from Consultas import obter_poltronas_com_dados
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.secret_key = 'chave_secreta'


def conectar_bd():
    try:
        return sqlitecloud.connect("sqlitecloud://cd6aglqkhz.g2.sqlite.cloud:8860/banco.db?apikey=HMJnjaYXpCk6wFb3aaY9SGb4zw5eYEsCHInAbFyVYhc")
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None
        
# Criar tabelas no banco de dados
def criar_tabelas():
    con = conectar_bd()
    if con:
        try:
            cur = con.cursor()
            
            # Criar tabelas
            cur.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                nome TEXT,
                                email TEXT UNIQUE,
                                senha TEXT,
                                tipo TEXT DEFAULT 'user',
                                idade INTEGER,
                                cidade TEXT)''')

            cur.execute('''CREATE TABLE IF NOT EXISTS viagens (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                origem TEXT,
                                destino TEXT,
                                data TEXT,
                                horario TEXT,
                                onibus TEXT)''')

            cur.execute('''CREATE TABLE IF NOT EXISTS pontos_parada (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                viagem_id INTEGER,
                                parada TEXT,
                                valor REAL,
                                FOREIGN KEY(viagem_id) REFERENCES viagens(id))''')

            cur.execute('''CREATE TABLE IF NOT EXISTS reservas (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                usuario_id INTEGER,
                                viagem_id INTEGER,
                                poltrona INTEGER,
                                nome TEXT,
                                embarque TEXT,
                                desembarque TEXT,
                                status TEXT,
                                FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
                                FOREIGN KEY(viagem_id) REFERENCES viagens(id))''')

            cur.execute('''CREATE TABLE IF NOT EXISTS reservas_pontos (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                reserva_id INTEGER,
                                embarque_id INTEGER,
                                desembarque_id INTEGER,
                                FOREIGN KEY(reserva_id) REFERENCES reservas(id),
                                FOREIGN KEY(embarque_id) REFERENCES pontos_parada(id),
                                FOREIGN KEY(desembarque_id) REFERENCES pontos_parada(id))''')

            con.commit()

            # Verificar se o usuário administrador já existe antes de inseri-lo
            cur.execute("SELECT id FROM usuarios WHERE email = ?", ("admin_buser",))
            admin_existe = cur.fetchone()

            if not admin_existe:
                cur.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                            ("Admin Buser", "admin_buser", generate_password_hash("ADM_BUSS"), "admin"))
                con.commit()

        except sqlitecloud.exceptions.SQLiteCloudIntegrityError as e:
            print(f"Erro de integridade ao criar tabelas: {e}")
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")
        finally:
            con.close()

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
        cur.execute("SELECT * FROM usuarios WHERE email=? AND senha=?", (email, senha))
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
            return "Login falhou"
    return render_template('login.html')

# Verificar poltronas disponíveis para uma viagem
@app.route('/verificar_poltronas/<viagem_id>', methods=['GET'])
def verificar_poltronas(viagem_id):
    con = conectar_bd()
    cur = con.cursor()
    cur.execute("SELECT poltrona, status FROM reservas WHERE viagem_id = ?", (viagem_id,))
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
        cur.execute("INSERT INTO usuarios (nome, email, senha, cidade) VALUES (?, ?, ?, ?)", (nome, email, senha, cidade))
        con.commit()
        con.close()
        return redirect(url_for('login'))
    except sqlite3.IntegrityError:
        con.close()
        return "Erro: Usuário já existe"

# Rota do painel de administrador
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'usuario_id' in session and session['tipo'] == 'admin':
        usuario_id = session['usuario_id']
        
        # Conectar ao banco e buscar o nome do administrador
        con = conectar_bd()
        cur = con.cursor()
        cur.execute("SELECT nome FROM usuarios WHERE id = ?", (usuario_id,))
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
            if not destino or not horario or not onibus or not data:
                return "Erro: Todos os campos são obrigatórios", 400
            
            # Conecta ao banco de dados
            con = conectar_bd()
            cur = con.cursor()
            
            # Insere a viagem no banco de dados
            cur.execute("INSERT INTO viagens (destino, horario, onibus, data) VALUES (?, ?, ?, ?)", 
                        (destino, horario, onibus, data))
            con.commit()

            # Pega o ID da viagem inserida
            viagem_id = cur.lastrowid

            # Insere as paradas associadas a essa viagem
            for parada in paradas:
                if parada:  # Verifica se a parada não está vazia
                    cur.execute("INSERT INTO pontos_parada (viagem_id, parada) VALUES (?, ?)", 
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

        # Buscar todos os pontos de parada para as viagens
        pontos_parada = {}
        for viagem in viagens:
            viagem_id = viagem[0]
            cur.execute("SELECT parada FROM pontos_parada WHERE viagem_id = ?", (viagem_id,))
            pontos = [row[0] for row in cur.fetchall()]
            pontos_parada[viagem_id] = pontos
        
        con.close()

        return render_template('admin.html', 
                               viagens=viagens, 
                               poltronas_ocupadas=poltronas_ocupadas, 
                               reservas_pendentes=reservas_pendentes,
                               pontos_parada=pontos_parada, 
                               nome_usuario=nome_usuario)

# Rota do painel do usuário
@app.route('/user')
def user():
    if 'usuario_id' in session:
        usuario_id = session['usuario_id']
        con = conectar_bd()
        cur = con.cursor()

        # Buscar nome do usuário
        cur.execute("SELECT nome FROM usuarios WHERE id = ?", (usuario_id,))
        usuario = cur.fetchone()
        nome_usuario = usuario[0] if usuario else "Usuário"
        
        # Buscar viagens disponíveis
        cur.execute("SELECT * FROM viagens")
        viagens = cur.fetchall()

        # Buscar reservas do usuário
        cur.execute("SELECT r.*, viagens.origem, viagens.destino, viagens.data FROM reservas r JOIN viagens ON r.viagem_id = viagens.id WHERE r.usuario_id = ?", (usuario_id,))
        reservas = cur.fetchall()    

        # Criar um dicionário para armazenar pontos de embarque e desembarque por viagem
        pontos_viagens = {}

        for viagem in viagens:
            viagem_id = viagem[0]

            # Buscar pontos de embarque e desembarque ordenados
            cur.execute("SELECT parada FROM pontos_parada WHERE viagem_id = ? ORDER BY id", (viagem_id,))
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

        return render_template('user.html', reservas=reservas, viagens=viagens, nome_usuario=nome_usuario, 
                               pontos_viagens=pontos_viagens, poltronas_ocupadas=poltronas_ocupadas, 
                               pontos_embarque_desembarque=pontos_embarque_desembarque)
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
        cur.execute("SELECT * FROM reservas WHERE viagem_id = ? AND poltrona = ?", (viagem_id, poltrona))
        reserva_existente = cur.fetchone()
        if reserva_existente:
            flash("Erro: Poltrona já reservada", "error")
            return redirect(url_for('user'))  # Redireciona para a página do usuário com a mensagem de erro

        # Verificar se a viagem existe
        cur.execute("SELECT id FROM viagens WHERE id = ?", (viagem_id,))
        if not cur.fetchone():
            flash("Erro: Viagem não encontrada", "error")
            return redirect(url_for('user'))

        # Verificar se o ponto de embarque existe
        cur.execute("SELECT id FROM pontos_parada WHERE id = ?", (embarque,))
        if not cur.fetchone():
            flash("Erro: Ponto de embarque não encontrado", "error")
            return redirect(url_for('user'))

        # Verificar se o ponto de desembarque existe
        cur.execute("SELECT id FROM pontos_parada WHERE id = ?", (desembarque,))
        if not cur.fetchone():
            flash("Erro: Ponto de desembarque não encontrado", "error")
            return redirect(url_for('user'))

        # Inserir a reserva na tabela de reservas com o status 'Pendente'
        cur.execute("INSERT INTO reservas (usuario_id, viagem_id, poltrona, nome, embarque, desembarque, status) VALUES (?, ?, ?, ?, ?, ?, 'Pendente')", 
                    (usuario_id, viagem_id, poltrona, nome, embarque, desembarque))
        reserva_id = cur.lastrowid  # ID da reserva recém criada

        # Inserir os pontos de embarque e desembarque na tabela 'reservas_pontos'
        cur.execute("INSERT INTO reservas_pontos (reserva_id, embarque_id, desembarque_id) VALUES (?, ?, ?)", 
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
        cur.execute("UPDATE reservas SET status='Confirmado' WHERE id=?", (reserva_id,))
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
        cur.execute("INSERT INTO pontos_parada (viagem_id, parada, valor) VALUES (?, ?, ?)", 
                    (viagem_id, parada, valor))
        con.commit()
        con.close()

        return redirect(url_for('admin'))
    return redirect(url_for('login'))



@app.route('/pontos_parada/<viagem_id>', methods=['GET'])
def pontos_parada(viagem_id):
    con = conectar_bd()
    cur = con.cursor()
    cur.execute("SELECT id, parada, valor FROM pontos_parada WHERE viagem_id = ?", (viagem_id,))
    pontos = cur.fetchall()
    con.close()

    return {'pontos': [{'id': p[0], 'parada': p[1], 'valor': p[2]} for p in pontos]}




#######################################################
# Executar o app
if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")
