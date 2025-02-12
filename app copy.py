
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash


import re,secrets,smtplib,os,sqlite3






load_dotenv()  # Carrega as variáveis do arquivo .env

email_user = os.getenv("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secreto'

# Armazenar códigos temporários
codes = {}

db = SQLAlchemy(app)

# Modelos (sem alteração)
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    type = db.Column(db.String(10), nullable=False, default='saida')
    status = db.Column(db.String(20), default='NOK')
    paid = db.Column(db.Boolean, default=False)  

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)



class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    nome_completo = db.Column(db.String(200), nullable=False)
    cpf = db.Column(db.String(11), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)



# Rotas
from datetime import datetime, timedelta
from flask import render_template

@app.route('/despesas')
def index():
    expenses = Expense.query.all()
    categories = Category.query.all()

    category_totals = {}
    for expense in expenses:
        if expense.category not in category_totals:
            category_totals[expense.category] = 0
        category_totals[expense.category] += expense.value

    labels = list(category_totals.keys())
    values = list(category_totals.values())

    total_entrada = sum(e.value for e in expenses if e.type == 'entrada')
    total_saida = sum(e.value for e in expenses if e.type == 'saida')
    saldo = total_entrada - total_saida

    # Cálculo de total a vencer e vencidas, usando o atributo correto 'date'
    hoje = datetime.today().date()
    prazo_limite = hoje + timedelta(days=7)

    total_a_vencer = sum(
        e.value for e in expenses
        if hoje <= e.date <= prazo_limite and not e.paid
    )

    total_vencidas = sum(
        e.value for e in expenses
        if e.date < hoje and not e.paid
    )

    return render_template(
        'index.html',
        expenses=expenses,
        categories=categories,
        total_entrada=total_entrada,
        total_saida=total_saida,
        saldo=saldo,
        values=values,
        labels=labels,
        total_a_vencer=total_a_vencer,
        total_vencidas=total_vencidas,
    )


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


def update_expense_status(expense_id):
    try:
        expense = Expense.query.get(expense_id)

        if expense:
            expense.status = 'PAGO'
            expense.paid = True
            
            db.session.flush()  # Força a atualização do objeto na sessão
            db.session.commit()
            print(f"Status da despesa com ID {expense_id} foi atualizado para PAGO.")
            return True
        else:
            print(f"Despesa com ID {expense_id} não encontrada.")
            return False
    
    except Exception as e:
        db.session.rollback()
        print(f"Ocorreu um erro ao atualizar o status: {str(e)}")
        return False


@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    expense_id = data.get('id')
    new_status = data.get('status')

    # Lógica para atualizar no banco de dados
    expense = Expense.query.get(expense_id)
    if expense:
        expense.status = new_status
        expense.paid = True if new_status == 'ok' else False
        db.session.commit()
        return jsonify({'message': 'Status atualizado com sucesso'}), 200
    else:
        return jsonify({'error': 'Despesa não encontrada'}), 404





@app.route('/add', methods=['POST'])
def add_expense():
    try:
        description = request.form.get('description')
        category = request.form.get('category')
        value = request.form.get('value')
        date = request.form.get('date')
        type = request.form.get('type')

        if not all([description, category, value, date, type]):
            return "Todos os campos são obrigatórios.", 400

        value = float(value)
        if value <= 0:
            return "O valor da despesa deve ser positivo.", 400

        date = datetime.strptime(date, '%Y-%m-%d')

        if type not in ['entrada', 'saida']:
            return "Tipo inválido.", 400

        new_expense = Expense(description=description, category=category, value=value, date=date, type=type)
        db.session.add(new_expense)
        db.session.commit()

        return redirect(url_for('index'))
    except ValueError:
        return "Valor ou data inválidos.", 400
    except Exception as e:
        return f"Erro ao adicionar despesa: {e}", 500

@app.route('/add_category', methods=['POST'])
def add_category():
    try:
        name = request.form.get('category_name')
        if not name:
            return "Nome da categoria é obrigatório.", 400

        if Category.query.filter_by(name=name).first():
            return "Categoria já existe.", 400

        new_category = Category(name=name)
        db.session.add(new_category)
        db.session.commit()

        return redirect(url_for('index'))
    except Exception as e:
        return f"Erro ao adicionar categoria: {e}", 500

@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    
    if request.method == 'POST':
        expense.description = request.form['description']
        expense.category = request.form['category']
        expense.value = float(request.form['value'])
        expense.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        expense.type = request.form['type']
        
        db.session.commit()
        return redirect(url_for('index'))
    
    categories = Category.query.all()
    return render_template('edit_expense.html', expense=expense, categories=categories)

@app.route('/delete/<int:expense_id>', methods=['GET', 'POST'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    
    db.session.delete(expense)
    db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/category_chart')
def category_chart():
    categories = db.session.query(Expense.category, db.func.sum(Expense.value).label('total')) \
        .group_by(Expense.category).all()

    labels = [category[0] for category in categories]
    values = [category[1] for category in categories]

    return render_template('category_chart.html', labels=labels, values=values)

@app.route('/summary')
def summary():
    expenses = Expense.query.all()
    total_entrada = sum(e.value for e in expenses if e.type == 'entrada')
    total_saida = sum(e.value for e in expenses if e.type == 'saida')
    saldo = total_entrada - total_saida

    category_expenses = {}
    for expense in expenses:
        if expense.category not in category_expenses:
            category_expenses[expense.category] = 0
        category_expenses[expense.category] += expense.value

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

@app.route('/inicio')
def inicio():
    return render_template('inicio.html')

# Função de envio de email para validar e-mail
def send_email(recipient, code):
    smtp = smtplib.SMTP('smtp.office365.com', 587)
    smtp.starttls()
    smtp.login(email_user, email_password)
    msg = MIMEText(f"Seu código de validação é {code}.")
    msg['Subject'] = "Código de Validação"
    msg['From'] = email_user
    msg['To'] = recipient
    smtp.sendmail(email_user, recipient, msg.as_string())
    smtp.quit()


@app.route('/complete_registration', methods=['GET', 'POST'])
def complete_registration():
    return "Registro completo!"


@app.route('/report', methods=['GET'])
def report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')
    type_filter = request.args.get('type')

    query = Expense.query

    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(Expense.date >= start_date)
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(Expense.date <= end_date)
    if category:
        query = query.filter(Expense.category == category)
    if type_filter:
        query = query.filter(Expense.type == type_filter)

    expenses = query.all()

    return render_template('report.html', expenses=expenses)



#cadastro de usuarios#
# Função para validar a senha
def validar_senha(password):
    """ Valida se a senha tem pelo menos 6 caracteres, uma letra maiúscula e um caractere especial """
    if not re.match(r'^(?=.*[A-Z])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{6,}$', password):
        return False
    return True

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        email = request.form.get('email')
        nome_completo = request.form.get('nome_completo')
        cpf = request.form.get('cpf')
        senha = request.form.get('senha')

        # Verificar se todos os campos foram preenchidos
        if not all([email, nome_completo, cpf, senha]):
            flash("Todos os campos são obrigatórios.", "error")
            return redirect(url_for('cadastro'))

        # Verificar a senha antes de salvar
        if not validar_senha(senha):
            flash("A senha deve ter no mínimo 6 caracteres, uma letra maiúscula e um caractere especial.", "error")
            return redirect(url_for('cadastro'))

        # Criptografar a senha antes de salvar
        senha_hash = generate_password_hash(senha)

        # Adicionando o print para depuração
        print(f'Email: {email}, Nome: {nome_completo}, CPF: {cpf}, Senha Hash: {senha_hash}')
        
        try:
            conn = sqlite3.connect('expenses.db')
            cursor = conn.cursor()

            # Verificar se o CPF já existe
            cursor.execute('SELECT 1 FROM usuarios WHERE cpf = ?', (cpf,))
            if cursor.fetchone():
                flash("Erro: CPF já cadastrado.", "error")
                return redirect(url_for('cadastro'))

            # Verificar se o e-mail já existe
            cursor.execute('SELECT 1 FROM usuarios WHERE email = ?', (email,))
            if cursor.fetchone():
                flash("Erro: E-mail já cadastrado.", "error")
                return redirect(url_for('cadastro'))

            # Inserir novo usuário
            cursor.execute('INSERT INTO usuarios (email, nome_completo, cpf, senha) VALUES (?, ?, ?, ?)',
                           (email, nome_completo, cpf, senha_hash))

            conn.commit()
            flash("Cadastro realizado com sucesso!", "success")
            return redirect(url_for('login'))
        
        except sqlite3.Error as e:
            flash(f"Erro no banco de dados: {str(e)}", "error")
        
        finally:
            conn.close()

    return render_template('cadastro.html')



if __name__ == '__main__':
    with app.app_context():
        update_expense_status(1)  # Teste dentro do contexto Flask
    app.run(debug=True)





if __name__ == '__main__':
    app.run(debug=True)
