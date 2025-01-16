
import os
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from datetime import datetime, timezone, timedelta
from werkzeug.datastructures import ImmutableMultiDict
from hashlib import sha256
from time import time
from collections import defaultdict
import random
import string
from fuzzywuzzy import fuzz

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Chave secreta para a sessão

def conectar_bd():
        conn = sqlite3.connect('biblioteca.db')
        conn.row_factory = sqlite3.Row
        return conn

def verificar_criar_tabelas():
    conn = conectar_bd()
    conn.execute('''CREATE TABLE IF NOT EXISTS livros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT NOT NULL UNIQUE,
                    titulo TEXT NOT NULL,
                    autor TEXT NOT NULL,
                    exemplares_disponiveis INTEGER NOT NULL,
                    emprestado BOOLEAN NOT NULL DEFAULT 0
                )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS emprestimos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        livro_id INTEGER NOT NULL,
                        aluno TEXT NOT NULL,
                        horario_emprestimo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(livro_id) REFERENCES livros(id)
                )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS transacoes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tipo TEXT NOT NULL,
                        descricao TEXT NOT NULL,
                        horario TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()


verificar_criar_tabelas()


def gerar_codigo_unico():
    while True:
        codigo = str(random.randint(1, 99999))
        conn = conectar_bd()
        cursor = conn.execute('SELECT id FROM livros WHERE codigo = ?', (codigo,))
        livro = cursor.fetchone()
        conn.close()
        if not livro:
            return codigo

@app.route('/criar_usuario', methods=['GET', 'POST'])
def criar_usuario():
    if 'username' not in session or not session.get('is_admin'):
        flash("Você não tem permissão para acessar esta página.", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = request.form.get('is_admin', '0')  # Retorna '0' se 'is_admin' não estiver presente


        if not username or not password:
            flash('Nome de usuário e senha são obrigatórios.', 'error')
            return render_template('criar_usuario.html')

        try:
            conn = conectar_bd()
            conn.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                         (username, password, is_admin))
            conn.commit()
            conn.close()
            flash('Usuário criado com sucesso.', 'success')
            return redirect(url_for('index'))
        except sqlite3.Error as e:
            flash(f'Erro ao criar usuário: {e}', 'error')
            return render_template('criar_usuario.html')

    return render_template('criar_usuario.html')

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verificar as credenciais no banco de dados
        conn = conectar_bd()
        cursor = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Armazenar o usuário na sessão
            session['username'] = username
            session['is_admin'] = user['is_admin']
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos. Tente novamente.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

# Rota da página inicial
@app.route('/')
def index():
    if 'username' in session:
        # Verificar se o usuário é administrador
        is_admin = session.get('is_admin', False)

        conn = conectar_bd()
        cursor = conn.execute('SELECT * FROM livros ORDER BY titulo, autor')
        livros = cursor.fetchall()
        conn.close()

        return render_template('index.html', livros=livros, is_admin=is_admin)
    else:
        return redirect(url_for('login'))
    
def registrar_transacao(tipo, descricao):
    print("Registrando transação...")
    try:
        horario = datetime.now(timezone.utc).astimezone().isoformat()
        with conectar_bd() as conn:
            conn.execute('INSERT INTO transacoes (tipo, descricao, horario) VALUES (?, ?, ?)', (tipo, descricao, horario))
            conn.commit()
        print("Transação registrada com sucesso.")
    except sqlite3.Error as e:
        print(f"Erro ao registrar transação: {e}")

def formatar_data_hora(data_hora_str):
    try:
        # Tenta converter a data/hora do formato '03/07/2024 14:50' para objeto datetime
        data_hora = datetime.strptime(data_hora_str, '%d/%m/%Y %H:%M')
        fuso_horario = timezone(timedelta(hours=-3))
        data_hora_formatada = data_hora.replace(tzinfo=timezone.utc).astimezone(fuso_horario)
        return data_hora_formatada.strftime('%d/%m/%Y - %H:%M')
    except ValueError:
        try:
            # Tenta converter a data/hora no formato ISO 8601
            data_hora = datetime.fromisoformat(data_hora_str.replace('Z', '+00:00'))
            fuso_horario = timezone(timedelta(hours=-3))
            data_hora_formatada = data_hora.astimezone(fuso_horario)
            return data_hora_formatada.strftime('%d/%m/%Y - %H:%M')
        except ValueError:
            return "Formato de data/hora inválido"



@app.route('/historico', methods=['GET'])
def historico():
    # Verifica se o usuário está logado e se é administrador
    if 'username' not in session:
        flash("Você precisa fazer login para acessar o histórico.", "error")
        return redirect(url_for('login'))

    if not session.get('is_admin', False):
        flash("Você não tem permissão para acessar esta página.", "error")
        return redirect(url_for('index'))
    
    try:
        with conectar_bd() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT tipo, descricao, horario FROM transacoes')
            transacoes = [{
                'tipo': tipo,
                'descricao': descricao,
                'horario': formatar_data_hora(horario)
            } for tipo, descricao, horario in cursor.fetchall()]

            transacoes_agrupadas = {}
            for transacao in transacoes:
                chave = (transacao['tipo'], transacao['descricao'], transacao['horario'])
                if chave not in transacoes_agrupadas:
                    transacoes_agrupadas[chave] = 0
                transacoes_agrupadas[chave] += 1

            transacoes_formatadas = []
            for (tipo, descricao, horario), quantidade in transacoes_agrupadas.items():
                descricao_formatada = descricao if quantidade == 1 else f'{descricao} Quantidade: {quantidade}'
                transacoes_formatadas.append({
                    'tipo': tipo,
                    'descricao': descricao_formatada,
                    'horario': horario
                })

            # Invertendo a ordem das transações formatadas
            transacoes_formatadas.reverse()

            return render_template('historico.html', transacoes=transacoes_formatadas)
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")
        flash("Erro ao acessar o banco de dados.", "error")
        return redirect(url_for('index'))

@app.route('/adicionar_livro', methods=['POST'])
def adicionar_livro():
    try:
        # Coleta os inputs do HTML
        titulo = request.form.get("titulo")
        autor = request.form.get("autor")
        canal = request.form.get("canal")
        exemplares = int(request.form.get("exemplares", 0))

        if not titulo or not autor or not canal:
            flash('Título, autor e canal são obrigatórios.', 'error')
            return redirect(url_for('index'))

        if exemplares <= 0:
            flash('A quantidade de exemplares deve ser maior que zero.', 'error')
            return redirect(url_for('index'))

        conn = conectar_bd()
        cursor = conn.cursor()

        try:
            # Verifica se o livro já existe
            cursor.execute(
                'SELECT id, titulo, autor, exemplares_disponiveis, codigo, canal FROM livros WHERE titulo = ? AND autor = ?',
                (titulo, autor)
            )
            livro_existente = cursor.fetchone()

            if livro_existente:
                novo_total_exemplares = livro_existente[3] + exemplares
                cursor.execute(
                    'UPDATE livros SET exemplares_disponiveis = ?, canal = ? WHERE id = ?',
                    (novo_total_exemplares, canal, livro_existente[0])
                )
                codigo = livro_existente[4]  # Código do livro existente
                flash('Quantidade de exemplares atualizada com sucesso.', 'success')
            else:
                # Insere um novo livro
                codigo = gerar_codigo_unico()
                cursor.execute(
                    'INSERT INTO livros (codigo, titulo, autor, exemplares_disponiveis, emprestado, canal) VALUES (?, ?, ?, ?, ?, ?)',
                    (codigo, titulo, autor, exemplares, False, canal)
                )
                flash('Livro adicionado com sucesso.', 'success')

            conn.commit()
            registrar_transacao(
                'Adição' if not livro_existente else 'Atualização',
                f'Livro {"adicionado" if not livro_existente else "atualizado"} - Código: {codigo}, Título: {titulo}, Autor: {autor}, Plateleira: {canal}, Exemplares: {exemplares}'
            )

        except Exception as e:
            conn.rollback()
            flash(f'Erro ao processar a transação: {str(e)}', 'error')

        finally:
            conn.close()

    except Exception as e:
        flash(f'Erro ao processar a requisição: {str(e)}', 'error')

    return redirect(url_for('index'))

# Rota para emprestar um livro

@app.route('/emprestar_livro', methods=['POST'])
def emprestar_livro():
    print("Endpoint /emprestar_livro chamado")
    data = request.form
    pesquisa = data["pesquisa"]
    quantidade = int(data["quantidade"])
    aluno = data["aluno"]

    try:
        with conectar_bd() as conn:
            # Verificar se o aluno está cadastrado
            cursor = conn.execute('SELECT * FROM users WHERE username = ?', (aluno,))
            usuario = cursor.fetchone()
            if not usuario:
                flash("Aluno não cadastrado.", "error")
                return redirect(url_for('index'))

            conn.execute("PRAGMA foreign_keys = ON")  # Ativar suporte a chaves estrangeiras

            cursor = conn.execute('SELECT * FROM livros WHERE codigo = ? OR titulo = ? OR autor = ?', (pesquisa, pesquisa, pesquisa))
            livros_encontrados = cursor.fetchall()

            if not livros_encontrados:
                flash("Nenhum livro encontrado.", "error")
                return redirect(url_for('index'))

            horario_emprestimo = datetime.now(timezone.utc).astimezone().isoformat()

            for livro in livros_encontrados:
                exemplares_disponiveis = livro["exemplares_disponiveis"]
                if exemplares_disponiveis < quantidade:
                    flash("Exemplares insuficientes.", "error")
                    return redirect(url_for('index'))

                exemplares_restantes = exemplares_disponiveis - quantidade
                conn.execute('UPDATE livros SET exemplares_disponiveis = ? WHERE id = ?', (exemplares_restantes, livro["id"]))

                cursor = conn.execute('SELECT COUNT(*) FROM emprestimos WHERE livro_id = ? AND aluno = ?', (livro["id"], aluno))
                emprestimo_existente = cursor.fetchone()[0]

                if emprestimo_existente > 0:
                    return redirect(url_for('index'))

                for _ in range(quantidade):
                    conn.execute('INSERT INTO emprestimos (livro_id, aluno, horario_emprestimo) VALUES (?, ?, ?)', (livro["id"], aluno, horario_emprestimo))

                descricao = f'Livro emprestado - {livro["titulo"]}, Aluno: {aluno}'
                registrar_transacao('Empréstimo', descricao)

            conn.commit()

        flash("Livro emprestado com sucesso.", "success")
        return redirect(url_for('index'))
    except sqlite3.Error as e:
        print(f"Erro ao emprestar livro: {e}")
        flash("Livro emprestado.", "success")
        return redirect(url_for('index'))


# Rota para devolver um livro
recent_requests = defaultdict(lambda: (0, None))  # livro_id: (timestamp, hash)

    
@app.route('/devolver_livro', methods=['POST'])
def devolver_livro():
    pesquisa = request.form.get("pesquisa")
    aluno = request.form.get("aluno")
    quantidade = int(request.form.get("quantidade", 0))

    if not pesquisa or not aluno or quantidade <= 0:
        flash("Dados inválidos para o formulário.", "error")
        print("Dados inválidos para o formulário.")
        return redirect(url_for('index'))

    try:
        conn = conectar_bd()

        # Verificar se o aluno está cadastrado
        cursor = conn.execute('SELECT * FROM users WHERE username = ?', (aluno,))
        usuario = cursor.fetchone()
        if not usuario:
            flash("Aluno não cadastrado.", "error")
            print("Aluno não cadastrado.")
            return redirect(url_for('index'))

        # Verificar se o livro está cadastrado
        cursor = conn.execute('SELECT * FROM livros WHERE codigo = ? OR titulo = ?', (pesquisa, pesquisa))
        livro = cursor.fetchone()

        if not livro:
            flash("Livro não encontrado.", "error")
            print("Livro não encontrado.")
            return redirect(url_for('index'))

        hash_request = sha256(f"{livro['id']}-{aluno}-{quantidade}".encode()).hexdigest()
        current_time = time()

        last_time, last_hash = recent_requests.get(livro['id'], (None, None))
        if last_time and last_hash == hash_request and (current_time - last_time) < 10:
            flash("Você já processou a devolução recentemente para este livro.", "warning")
            print("Você já processou a devolução recentemente para este livro.")
            return redirect(url_for('index'))

        recent_requests[livro['id']] = (current_time, hash_request)

        cursor = conn.execute('SELECT * FROM emprestimos WHERE livro_id = ? AND aluno = ? LIMIT ?', (livro["id"], aluno, quantidade))
        emprestimos = cursor.fetchall()

        if len(emprestimos) < quantidade:
            flash("Quantidade de exemplares emprestados insuficiente.", "error")
            print("Quantidade de exemplares emprestados insuficiente.")
            return redirect(url_for('index'))

        exemplares_disponiveis = livro["exemplares_disponiveis"] + quantidade
        conn.execute('UPDATE livros SET exemplares_disponiveis = ? WHERE id = ?', (exemplares_disponiveis, livro["id"]))

        for emprestimo in emprestimos:
            conn.execute('DELETE FROM emprestimos WHERE id = ?', (emprestimo["id"],))

        conn.commit()

        descricao = f'Livro devolvido - {livro["titulo"]}, Aluno: {aluno}, Quantidade: {quantidade}'
        registrar_transacao('Devolução', descricao)

        flash("Livros devolvidos com sucesso.", "success")
        print("Livros devolvidos com sucesso.")
        return redirect(url_for('index'))
    except sqlite3.Error as e:
        print(f"Erro ao devolver livro: {e}")
        flash("Erro ao devolver livro.", "error")
        return redirect(url_for('index'))


@app.route('/meus_emprestimos', methods=['GET', 'POST'])
def meus_emprestimos():
    if 'username' not in session:
        flash("Você precisa fazer login para ver seus empréstimos.", "error")
        return redirect(url_for('login'))

    aluno = session['username']
    is_admin = session.get('is_admin', False)

    if request.method == 'POST' and is_admin:
        aluno = request.form.get('aluno')

    try:
        with conectar_bd() as conn:
            # Verificar se o aluno existe
            cursor = conn.execute('SELECT COUNT(*) FROM users WHERE username = ?', (aluno,))
            aluno_existe = cursor.fetchone()[0]

            if aluno_existe == 0:
                flash(f"Não há nenhum aluno cadastrado com o nome '{aluno}'.", "warning")

            # Buscar empréstimos do aluno
            cursor = conn.execute('''
                SELECT e.id, l.titulo, l.autor, e.horario_emprestimo 
                FROM emprestimos e 
                JOIN livros l ON e.livro_id = l.id 
                WHERE e.aluno = ?
            ''', (aluno,))
            emprestimos = cursor.fetchall()

            return render_template('meus_emprestimos.html', emprestimos=emprestimos, aluno=aluno, is_admin=is_admin)
    except sqlite3.Error as e:
        print(f"Erro ao buscar empréstimos: {e}")
        flash("Erro ao buscar empréstimos.", "error")
        return redirect(url_for('index'))

# Rota para obter os livros emprestados
@app.route('/livros_emprestados_json')
def livros_emprestados_json():
    print("Endpoint /emprestado chamado")
    conn = conectar_bd()
    cursor = conn.execute('SELECT livros.titulo, livros.autor, emprestimos.aluno, emprestimos.horario_emprestimo, COUNT(*) as quantidade FROM emprestimos INNER JOIN livros ON emprestimos.livro_id = livros.id GROUP BY livro_id, aluno, horario_emprestimo ORDER BY emprestimos.horario_emprestimo')
    emprestimos = cursor.fetchall()
    conn.close()

    # Formatar os resultados como lista de dicionários
    livros_emprestados = []
    for emprestimo in emprestimos:
        livro_emprestado = {
            'titulo': emprestimo['titulo'],
            'autor': emprestimo['autor'],
            'aluno': emprestimo['aluno'],
            'horario_emprestimo': emprestimo['horario_emprestimo'],
            'quantidade': emprestimo['quantidade']
        }
        livros_emprestados.append(livro_emprestado)

    return jsonify(livros_emprestados)

# Rota para buscar livros por título ou autor
@app.route('/buscar_livros', methods=['GET'])
def buscar_livros():
    print("Endpoint /buscar chamado")
    termo_pesquisa = request.args.get('q', '').lower().strip()

    conn = conectar_bd()
    cursor = conn.execute('''
        SELECT livros.id, livros.codigo, livros.titulo, livros.autor, livros.exemplares_disponiveis, livros.canal,
        (SELECT COUNT(emprestimos.id) FROM emprestimos WHERE emprestimos.livro_id = livros.id) as quantidade_emprestados,
        (SELECT aluno FROM emprestimos WHERE emprestimos.livro_id = livros.id ORDER BY horario_emprestimo DESC LIMIT 1) as aluno,
        (SELECT horario_emprestimo FROM emprestimos WHERE emprestimos.livro_id = livros.id ORDER BY horario_emprestimo DESC LIMIT 1) as horario_emprestimo
        FROM livros
    ''')
    livros = cursor.fetchall()
    conn.close()

    resultado_livros = []
    for livro in livros:
        titulo = livro['titulo'].lower().strip()
        autor = livro['autor'].lower().strip()
        if fuzz.partial_ratio(termo_pesquisa, titulo) > 80 or fuzz.partial_ratio(termo_pesquisa, autor) > 80 or termo_pesquisa in livro['codigo'].lower():
            if livro['exemplares_disponiveis'] > 0:
                resultado_livro = {
                    'id': livro['id'],
                    'codigo': livro['codigo'],
                    'titulo': livro['titulo'],
                    'autor': livro['autor'],
                    'canal':livro['canal'],
                    'exemplares_disponiveis': livro['exemplares_disponiveis'],
                    'emprestado': False
                }
                resultado_livros.append(resultado_livro)
            else:
                resultado_livro = {
                    'id': livro['id'],
                    'codigo': livro['codigo'],
                    'titulo': livro['titulo'],
                    'autor': livro['autor'],
                    'exemplares_disponiveis': livro['exemplares_disponiveis'],
                    'canal':livro['canal'],
                    'emprestado': True,
                    'aluno': livro['aluno'],
                    'horario_emprestimo': livro['horario_emprestimo']
                }
                resultado_livros.append(resultado_livro)

    return jsonify(resultado_livros)


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('is_admin', None)
    flash("Você saiu com sucesso.", "success")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, port=80)