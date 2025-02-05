from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from Consultas import obter_poltronas_com_dados

app = Flask(__name__)
app.secret_key = 'chave_secreta'

# Função para conectar ao banco de dados
def conectar_bd():
    return sqlite3.connect('banco.db', check_same_thread=False)

# Criar tabelas no banco de dados
def criar_tabelas():
    with conectar_bd() as con:
        cur = con.cursor()
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
                        status TEXT,
                        nome TEXT,
                        FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
                        FOREIGN KEY(viagem_id) REFERENCES viagens(id))''')
        con.commit()

        # Criar usuário administrador padrão se não existir
        try:
            cur.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)", 
                        ("Admin Buser", "Admin_buser", "ADM_BUSS", "admin"))
            con.commit()
        except sqlite3.IntegrityError:
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

            if not destino or not horario or not onibus:
                return "Erro: Todos os campos são obrigatórios", 400
            
            con = conectar_bd()
            cur = con.cursor()
            cur.execute("INSERT INTO viagens (destino, horario, onibus,data) VALUES (?, ?, ?,?)", 
                        (destino, horario, onibus,data))
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
        cur.execute("SELECT r.id, u.nome, v.origem, v.destino, r.poltrona FROM reservas r "
                    "JOIN usuarios u ON r.usuario_id = u.id "
                    "JOIN viagens v ON r.viagem_id = v.id "
                    "WHERE r.status = 'Pendente'")
        reservas_pendentes = cur.fetchall()

        con.close()

        reserva = obter_poltronas_com_dados()
        print(reservas_pendentes)
        
        return render_template('admin.html', 
                               viagens=viagens, 
                               poltronas_ocupadas=poltronas_ocupadas, 
                               reservas_pendentes=reservas_pendentes, 
                               nome_usuario=nome_usuario,
                               reserva = reserva )
    
    return redirect(url_for('login'))


# Rota do painel do usuário
@app.route('/user')
def user():
    if 'usuario_id' in session:
        usuario_id = session['usuario_id']
        
        # Conectar ao banco e buscar o nome do usuário
        con = conectar_bd()
        cur = con.cursor()
        cur.execute("SELECT nome FROM usuarios WHERE id = ?", (usuario_id,))
        usuario = cur.fetchone()
        con.close()
        
        nome_usuario = usuario[0] if usuario else "Usuário"

        # Buscar viagens disponíveis
        con = conectar_bd()
        cur = con.cursor()
        cur.execute("SELECT * FROM viagens")
        viagens = cur.fetchall()

        # Buscar reservas do usuário
        cur.execute("SELECT r.id, viagens.origem, viagens.destino, viagens.data, r.poltrona FROM reservas r JOIN viagens ON r.viagem_id = viagens.id WHERE r.usuario_id = ?", (usuario_id,))
        reservas = cur.fetchall()
        
        # Buscar poltronas ocupadas para cada viagem
        poltronas_ocupadas = {}
        for viagem in viagens:
            cur.execute("SELECT poltrona FROM reservas WHERE viagem_id = ? AND status = 'Confirmado'", (viagem[0],))
            ocupadas = cur.fetchall()
            poltronas_ocupadas[viagem[0]] = [row[0] for row in ocupadas]

        con.close()
        print(viagens)
        return render_template('user.html', viagens=viagens, reservas=reservas, poltronas_ocupadas=poltronas_ocupadas, nome_usuario=nome_usuario)
    
    return redirect(url_for('login'))

# Rota para realizar uma reserva
@app.route('/reservar', methods=['POST'])
def reservar():
    if 'usuario_id' in session:
        usuario_id = session['usuario_id']
        viagem_id = request.form['viagem_id']
        poltrona = request.form['poltrona']
        nome = request.form['nome']
        
        # Verificar se a poltrona está disponível
        con = conectar_bd()
        cur = con.cursor()
        cur.execute("SELECT * FROM reservas WHERE viagem_id = ? AND poltrona = ?", (viagem_id, poltrona))
        reserva_existente = cur.fetchone()
        con.close()
        
        if reserva_existente:
            return "Erro: Poltrona já reservada"
        
        # Se disponível, criar a reserva
        con = conectar_bd()
        cur = con.cursor()
        cur.execute("INSERT INTO reservas (usuario_id, viagem_id, poltrona,nome ,status) VALUES (?, ?, ?,?, 'Pendente')", (usuario_id, viagem_id, poltrona,nome))
        con.commit()
        con.close()
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

# Executar o app
if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")
