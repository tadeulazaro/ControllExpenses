from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.secret_key = os.urandom(24)
 # Altere para uma chave secreta real

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Adicione essa linha

# Resto do código


# Modelo de Usuário
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Modelos de Despesa e Categoria
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    type = db.Column(db.String(10), nullable=False, default='saida')  # entrada ou saída
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='expenses')

User.expenses = db.relationship('Expense', back_populates='user')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

# Rotas de Login e Cadastro
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Verifica se o usuário existe
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user'] = user.id  # Armazena o ID do usuário na sessão
            return redirect(url_for('index'))  # Redireciona para a página inicial
        else:
            return 'Login falhou. Verifique suas credenciais.', 400

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Verifica se o usuário já existe
        if User.query.filter_by(username=username).first():
            return 'Usuário já existe.', 400
        
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('login'))  # Redireciona para a página de login após cadastro

    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)  # Remove o usuário da sessão
    return redirect(url_for('inicio'))  # Redireciona para a página inicial

# Rota de Página Inicial
@app.route('/inicio')
def inicio():
    return render_template('inicio.html')

# Rota principal
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))  # Redireciona para o login se não estiver logado

    # Recupera as despesas do usuário logado
    user_id = session['user']
    expenses = Expense.query.filter_by(user_id=user_id).all()
    categories = Category.query.all()

    # Calculando valores e labels para o gráfico
    category_totals = {}
    for expense in expenses:
        if expense.category not in category_totals:
            category_totals[expense.category] = 0
        category_totals[expense.category] += expense.value

    labels = list(category_totals.keys())
    values = list(category_totals.values())

    # Calculando os totais de entrada e saída
    total_entrada = sum(e.value for e in expenses if e.type == 'entrada')
    total_saida = sum(e.value for e in expenses if e.type == 'saida')
    saldo = total_entrada - total_saida

    # Renderiza o template com os dados necessários
    return render_template(
        'index.html',
        expenses=expenses,
        categories=categories,  
        total_entrada=total_entrada,
        total_saida=total_saida,
        saldo=saldo,
        values=values,
        labels=labels,
    )

# Rota para adicionar despesas
@app.route('/add', methods=['POST'])
def add_expense():
    try:
        if 'user' not in session:
            return redirect(url_for('login'))

        description = request.form.get('description')
        category = request.form.get('category')
        value = request.form.get('value')
        date = request.form.get('date')
        type = request.form.get('type')

        if not all([description, category, value, date, type]):
            return "Todos os campos são obrigatórios.", 400
        
        # Verifica se o valor da despesa é positivo
        value = float(value)
        if value <= 0:
            return "O valor da despesa deve ser positivo.", 400
        
        # Conversões
        date = datetime.strptime(date, '%Y-%m-%d')

        if type not in ['entrada', 'saida']:
            return "Tipo inválido.", 400

        # Recupera o usuário logado
        user_id = session['user']

        new_expense = Expense(description=description, category=category, value=value, date=date, type=type, user_id=user_id)
        db.session.add(new_expense)
        db.session.commit()

        return redirect(url_for('index'))
    except ValueError:
        return "Valor ou data inválidos.", 400
    except Exception as e:
        return f"Erro ao adicionar despesa: {e}", 500

# Rota para editar despesas
@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    
    if request.method == 'POST':
        # Atualizar os dados com as novas informações
        expense.description = request.form['description']
        expense.category = request.form['category']
        expense.value = float(request.form['value'])
        expense.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        expense.type = request.form['type']
        
        # Salvar as alterações no banco de dados
        db.session.commit()
        return redirect(url_for('index'))
    
    categories = Category.query.all()
    return render_template('edit_expense.html', expense=expense, categories=categories)

# Rota para excluir despesas
@app.route('/delete/<int:expense_id>', methods=['GET', 'POST'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    
    # Excluir a despesa
    db.session.delete(expense)
    db.session.commit()
    
    return redirect(url_for('index'))

# Rota para gráficos de categoria
@app.route('/category_chart')
def category_chart():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Obter as despesas agrupadas por categoria
    user_id = session['user']
    categories = db.session.query(Expense.category, db.func.sum(Expense.value).label('total')) \
        .filter_by(user_id=user_id) \
        .group_by(Expense.category).all()

    # Criar as listas de rótulos e valores para o gráfico
    labels = [category[0] for category in categories]
    values = [category[1] for category in categories]

    # Passando as listas para o template
    return render_template('category_chart.html', labels=labels, values=values)

# Rota para o resumo das despesas
@app.route('/summary')
def summary():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']
    expenses = Expense.query.filter_by(user_id=user_id).all()
    total_entrada = sum(e.value for e in expenses if e.type == 'entrada')
    total_saida = sum(e.value for e in expenses if e.type == 'saida')
    saldo = total_entrada - total_saida

    # Cálculo por categoria
    category_expenses = {}
    for expense in expenses:
        if expense.category not in category_expenses:
            category_expenses[expense.category] = 0
        category_expenses[expense.category] += expense.value

    # Preparando os dados para o gráfico
    labels = list(category_expenses.keys())
    values = list(category_expenses.values())

    return render_template(
        'summary.html',
        total_entrada=total_entrada,
        total_saida=total_saida,
        saldo=saldo,
        labels=labels,
        values=values
    )

# Rota para o relatório de despesas
@app.route('/report', methods=['GET'])
def report():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Recupera parâmetros de filtros
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')
    type_filter = request.args.get('type')

    user_id = session['user']
    query = Expense.query.filter_by(user_id=user_id)

    # Filtra por data
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(Expense.date >= start_date)
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(Expense.date <= end_date)

    # Filtra por categoria
    if category:
        query = query.filter(Expense.category == category)

    # Filtra por tipo
    if type_filter:
        query = query.filter(Expense.type == type_filter)

    expenses = query.all()
    return render_template('report.html', expenses=expenses)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Criação das tabelas se não existirem
    app.run(debug=True)
