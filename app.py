from bson.objectid import ObjectId
from bson.errors import InvalidId
from bson import ObjectId

from datetime import datetime, timedelta
from dotenv import load_dotenv

from email.mime.text import MIMEText

from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
from flask_pymongo import PyMongo
from flask_login import login_required, current_user, LoginManager, UserMixin
from flask_mail import Mail, Message

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from werkzeug.security import generate_password_hash, check_password_hash

import os
import re, smtplib

import requests

# Carregar as variáveis do arquivo .env
load_dotenv()

# Carregar as configurações do .env
SECRET_KEY = os.getenv("SECRET_KEY")
email_user = os.getenv("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD")

# Configuração do Flask
app = Flask(__name__)
app.config['DEBUG'] = True  # Ativa o modo de depuração
app.config['MONGO_URI'] = os.getenv("MONGO_URI")  # Conexão com o MongoDB via string de conexão
app.secret_key = SECRET_KEY  # Configurar o segredo usando a variável do .env

# Instância do PyMongo (conexão com o MongoDB)
mongo = PyMongo(app)
db = mongo.db  # Isso já dá acesso ao banco de dados através do PyMongo

# Configuração do Flask-Mail com variáveis de ambiente
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Carregar de .env
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Carregar de .env
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')  # E-mail de envio padrão

# Definindo o tempo de expiração da sessão:
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

# Instância do Flask-Mail
mail = Mail(app)

# Criando um serializador para gerar tokens seguros
s = URLSafeTimedSerializer(app.secret_key)

# Criação do LoginManager
login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'


# Modelos adaptados para o MongoDB
def get_expense_collection():
    return mongo.db.despesas  # Retorna a coleção 'despesas' no MongoDB

def get_category_collection():
    return mongo.db.categories  # Retorna a coleção 'categories'

def get_usuarios_collection():
    return mongo.db.usuarios  # Retorna a coleção 'usuarios'


@app.before_request
def make_session_permanent():
    session.permanent = True




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


# Função de validação de senha
def validar_senha(password):
    """ Valida se a senha tem pelo menos 6 caracteres, uma letra maiúscula e um caractere especial """
    if not re.match(r'^(?=.*[A-Z])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{6,}$', password):
        return False
    return True





class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.name = user_data["name"]  # ou outro campo que represente o nome

@login_manager.user_loader
def load_user(user_id):
    user_data = get_user_collection().find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None


@app.route('/teste_user')
def teste_user():
    if current_user.is_authenticated:
        return f"Usuário logado: {current_user.name}"
    return "Nenhum usuário logado"


#______________________________________________________________________________#
################################# DESPESAS  ######################################
#______________________________________________________________________________#

@app.route('/despesas', methods=['GET', 'POST'])
def index():
    usuario_id = session.get('usuario_id')
    if usuario_id:  # Verificando se o usuario_id está na sessão
        usuario = mongo.db.usuarios.find_one({'_id': ObjectId(usuario_id)})
        if usuario:
            nome_completo = usuario.get('nome_completo', 'Usuário')
        else:
            nome_completo = None
            return redirect(url_for('login'))  # Se o usuário não for encontrado, redireciona para o login
    else:
        nome_completo = None
        return redirect(url_for('login'))  # Se o usuário não estiver na sessão, redireciona para o login

    # Convertendo usuario_id para ObjectId
    usuario_id = ObjectId(usuario_id)

    # Consultando as despesas do usuário
    expenses = list(mongo.db.despesas.find({'usuario_id': usuario_id}))

    # Consultando as categorias do usuário
    categories = list(mongo.db.categories.find({'usuario_id': usuario_id}))

    # Inserindo o nome da categoria nas despesas
    for expense in expenses:
        category = mongo.db.categories.find_one({"_id": expense.get('category')})
        expense['category_name'] = category["name"] if category else "Categoria não encontrada"

    # Calculando os totais por categoria
    category_totals = {}
    for expense in expenses:
        category_id = str(expense.get('category', ''))  # Evita erro se 'category' não existir
        if category_id:  # Garante que há uma categoria válida
            category_totals[category_id] = category_totals.get(category_id, 0) + expense['value']

    # Preenchendo as labels e valores com base nos totais das categorias
    labels = []
    values = []

    # Construindo as labels e valores
    for category in categories:
        category_id_str = str(category['_id'])
        if category_id_str in category_totals:
            labels.append(category['name'])
            values.append(category_totals[category_id_str])

    # Calculando os totais de entrada, saída e saldo
    total_entrada = sum(e['value'] for e in expenses if e.get('type') == 'entrada')
    total_saida = sum(e['value'] for e in expenses if e.get('type') == 'saida')
    saldo = total_entrada - total_saida

    # Calculando os totais de despesas a vencer e vencidas
    hoje = datetime.today().date()
    prazo_limite = hoje + timedelta(days=7)

    total_a_vencer = sum(
        e['value'] for e in expenses
        if 'date' in e and isinstance(e['date'], datetime) and hoje <= e['date'].date() <= prazo_limite and not e.get('paid', False)
    )

    total_vencidas = sum(
        e['value'] for e in expenses
        if 'date' in e and isinstance(e['date'], datetime) and e['date'].date() < hoje and not e.get('paid', False)
    )

    # Renderizando o template com todos os dados calculados
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
        nome_completo=nome_completo
    )




#______________________________________________________________________________#
###################### ADD DESPESAS######################################
#______________________________________________________________________________#
@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    try:
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return redirect(url_for('login'))

        # Garantindo que usuario_id seja um ObjectId válido
        try:
            usuario_id = ObjectId(usuario_id)
            print(f"usuario_id convertido: {usuario_id}")
        except Exception as e:
            return f"Erro ao converter usuario_id: {e}", 400


        if request.method == 'GET':
            categories = list(mongo.db.categories.find({"usuario_id": usuario_id}))
            print(f"Categorias carregadas: {categories}")  # <-- Adicione este print
            return render_template('add_expense.html', categories=categories)


        if request.method == 'POST':
            description = request.form.get('description')
            category = request.form.get('category')
            value = request.form.get('value')
            date = request.form.get('date')
            type = request.form.get('type')
            installments = request.form.get('installments', 1)  # Pegando o número de parcelas

            if not all([description, category, value, date, type]):
                return "Todos os campos são obrigatórios.", 400

            # Verificando se a categoria pertence ao usuário
            print(f"Verificando categoria: {category} para o usuário {usuario_id}")
            try:
                category_exists = mongo.db.categories.find_one(
                    {"_id": ObjectId(category), "usuario_id": usuario_id}
                )
                print(f"Categoria encontrada: {category_exists}")
            except Exception as e:
                return f"Erro ao verificar categoria: {e}", 500

            if not category_exists:
                return "Categoria inválida ou não associada a você.", 400

            # Validando o valor
            try:
                value = float(value)
                print(f"Valor convertido: {value}")
            except ValueError:
                return "O valor da despesa deve ser numérico.", 400

            if value <= 0:
                return "O valor da despesa deve ser positivo.", 400

            # Convertendo a data
            try:
                date = datetime.strptime(date, '%Y-%m-%d')
                print(f"Data convertida: {date}")
            except ValueError:
                return "Data inválida. Formato esperado: YYYY-MM-DD.", 400

            # Validando o tipo de despesa
            if type not in ['entrada', 'saida']:
                return "Tipo inválido.", 400

            # Obtendo o nome da categoria
            category_name = category_exists.get("name", "Categoria não encontrada")

            # Lógica para parcelamento
            installments = int(installments)  # Garantindo que o número de parcelas seja um inteiro
            installment_dates = []
            for i in range(installments):
                next_date = date + timedelta(weeks=4 * i)  # Adiciona 4 semanas para cada parcela
                installment_dates.append(next_date)

            # Inserindo as parcelas no banco de dados
            for i, installment_date in enumerate(installment_dates):
                # Criando a nova despesa para cada parcela
                new_expense = {
                    "description": description,
                    "category": ObjectId(category),
                    "category_name": category_name,  # Armazenando o nome da categoria
                    "value": value,
                    "date": installment_date,
                    "type": type,
                    "status": "NOK",
                    "paid": False,
                    "usuario_id": usuario_id,
                    "installment_number": i + 1,  # Adiciona o número da parcela
                    "total_installments": installments  # Armazena o número total de parcelas
                }

                # Verificando o conteúdo de new_expense antes de inserir
                print(f"Inserindo despesa (parcela {i+1}): {new_expense}")

                # Inserindo no MongoDB
                try:
                    result = mongo.db.despesas.insert_one(new_expense)
                    if result.inserted_id:
                        print(f"Despesa inserida com sucesso, ID: {result.inserted_id}")
                    else:
                        print("Erro ao inserir despesa.")
                except Exception as e:
                    return f"Erro ao inserir despesa: {e}", 500

            return redirect(url_for('index'))
        
    except ValueError:
        return "Valor ou data inválidos.", 400
    except Exception as e:
        return f"Erro ao adicionar despesa: {e}", 500



#______________________________________________________________________________#
###################### ADD CATEGORIA ######################################
#______________________________________________________________________________#
@app.route('/add_category', methods=['POST'])
def add_category():
    try:
        name = request.form.get('category_name')
        if not name:
            return "Nome da categoria é obrigatório.", 400

        usuario_id = session.get('usuario_id')  # Obtém o ID do usuário logado
        if not usuario_id:
            return redirect(url_for('login'))  # Se não houver usuário logado, redireciona para o login

        usuario_object_id = ObjectId(usuario_id)  # Convertendo para ObjectId

        # Verificando se a categoria já existe para o usuário
        if get_category_collection().find_one({"name": name, "usuario_id": usuario_object_id}):
            return "Categoria já existe para este usuário.", 400

        # Inserindo a categoria associada ao usuário
        new_category = {
            "name": name,
            "usuario_id": usuario_object_id  # Agora armazenando como ObjectId
        }

        get_category_collection().insert_one(new_category)
        return redirect(url_for('index'))
    except Exception as e:
        return f"Erro ao adicionar categoria: {e}", 500



#______________________________________________________________________________#
###################### DELETAR DESPESAS######################################
#______________________________________________________________________________#

@app.route('/delete/<expense_id>', methods=['GET'])
def delete_expense(expense_id):
    try:
        expense_id_obj = ObjectId(expense_id)
        get_expense_collection().delete_one({"_id": expense_id_obj})
        return redirect(url_for('index'))
    except InvalidId:
        return "ID inválido", 400
    except Exception as e:
        return f"Erro ao excluir a despesa: {e}", 500



#______________________________________________________________________________#
######################TELA EDITAR DESPESAS######################################
#______________________________________________________________________________#


@app.route('/edit/<expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    if 'usuario_id' not in session:  # Verifica se o usuário não está logado
        flash("Você precisa estar logado para acessar essa página.", "error")
        return redirect(url_for('login'))
    
    try:
        print(f"Tentando buscar a despesa com ID: {expense_id}")  # Debug

        try:
            expense_obj_id = ObjectId(expense_id)  # Converte o ID com validação
        except InvalidId:
            return "ID inválido", 400

        expense = get_expense_collection().find_one({"_id": expense_obj_id})
        print(f"Despesa encontrada: {expense}")  # Debug

        if not expense:
            return "Despesa não encontrada", 404

    except Exception as e:
        print(f"Erro ao buscar despesa: {e}")
        return "Erro ao carregar a página", 500

    if request.method == 'POST':
        description = request.form.get('description')
        category = request.form.get('category')
        expense_type = request.form.get('type')
        value = request.form.get('value')
        date = request.form.get('date')

        if not description or not category or not expense_type or not value or not date:
            return "Todos os campos são obrigatórios", 400

        try:
            value = float(value)
            date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return "Formato de valor ou data inválido", 400

        updated_expense = {
            "description": description,
            "category": category,
            "value": value,
            "date": date,
            "type": expense_type,
            "status": expense.get("status", "NOK"),
            "paid": expense.get("paid", False)
        }

        get_expense_collection().update_one({"_id": expense_obj_id}, {"$set": updated_expense})
        return redirect(url_for('index'))

    # Busca as categorias do usuário logado
    try:
        categories = list(get_category_collection().find({"usuario_id": ObjectId(session['usuario_id'])}, {"name": 1}))
    except Exception as e:
        print(f"Erro ao buscar categorias: {e}")
        categories = []

    return render_template('edit_expense.html', expense=expense, categories=categories)






#______________________________________________________________________________#
###################### UPDATE DESPESAS######################################
#______________________________________________________________________________#

@app.route('/update_paid_status/<expense_id>', methods=['POST'])
def update_paid_status(expense_id):
    try:
        if not ObjectId.is_valid(expense_id):
            return jsonify({"success": False, "error": "ID inválido"}), 400
        
        data = request.json
        new_paid_status = data.get('paid', False)
        
        result = get_expense_collection().update_one(
            {"_id": ObjectId(expense_id)},
            {"$set": {"paid": new_paid_status}}
        )
        
        if result.modified_count == 0:
            return jsonify({"success": False, "error": "Nenhum documento foi atualizado"}), 404
        
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500




#______________________________________________________________________________#
###################### SUMMARY DE ENTRADA SAIDA VENCIMENTO ETC  ######################################
#______________________________________________________________________________#
@app.route('/summary')
def summary():
    expenses = get_expense_collection().find()
    total_entrada = sum(e['value'] for e in expenses if e['type'] == 'entrada')
    total_saida = sum(e['value'] for e in expenses if e['type'] == 'saida')
    saldo = total_entrada - total_saida

    category_expenses = {}
    for expense in expenses:
        if expense['category'] not in category_expenses:
            category_expenses[expense['category']] = 0
        category_expenses[expense['category']] += expense['value']

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


#______________________________________________________________________________#
###################### CADASTRO USUARIO ######################################
#______________________________________________________________________________#

def validar_cpf_formatado(cpf):
    # Remover qualquer coisa que não seja número
    cpf = ''.join(filter(str.isdigit, cpf))

    # Verificar se o CPF tem 11 dígitos
    if len(cpf) != 11:
        return False

    # Verificar se todos os números são iguais (casos como 111.111.111.11 são inválidos)
    if cpf == cpf[0] * len(cpf):
        return False

    # Calcular o primeiro dígito verificador
    soma_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto_1 = (soma_1 * 10) % 11
    digito_1 = resto_1 if resto_1 < 10 else 0

    # Calcular o segundo dígito verificador
    soma_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto_2 = (soma_2 * 10) % 11
    digito_2 = resto_2 if resto_2 < 10 else 0

    # Verificar se os dígitos calculados são iguais aos fornecidos
    return cpf[-2:] == f"{digito_1}{digito_2}"

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        email = request.form['email']
        nome_completo = request.form['nome_completo']
        cpf = request.form['cpf']
        senha = request.form['senha']
        
        # Verificar se todos os campos estão preenchidos
        if not email or not nome_completo or not cpf or not senha:
            flash('Todos os campos são obrigatórios!', 'danger')
            return redirect(url_for('cadastro'))

        # Validar o formato do CPF
        if not validar_cpf_formatado(cpf):
            flash('CPF inválido! ', 'danger')
            return redirect(url_for('cadastro'))

        # Verificar se o CPF já existe no banco
        if mongo.db.usuarios.find_one({'cpf': cpf}):
            flash('CPF já cadastrado.', 'danger')
            return redirect(url_for('cadastro'))
        
        # Verificar se o email já existe no banco
        if mongo.db.usuarios.find_one({'email': email}):
            flash('Email já cadastrado.', 'danger')
            return redirect(url_for('cadastro'))

        # Criptografar a senha
        senha_hash = generate_password_hash(senha)
        
        # Criar um novo usuário
        usuario = {
            'email': email,
            'nome_completo': nome_completo,
            'cpf': cpf,
            'senha': senha_hash
        }
        
        # Inserir o usuário no banco de dados
        mongo.db.usuarios.insert_one(usuario)
        
        flash('Cadastro realizado com sucesso!', 'success')
        return redirect(url_for('login'))  # Redirecionar para a página de login

    return render_template('cadastro.html')






#______________________________________________________________________________#
######################  AUTENTICACAO USUARIO ######################################
#______________________________________________________________________________#


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            
            user = mongo.db.usuarios.find_one({'email': email})
            if not user:
                flash("Usuário ou senha inválidos, tente novamente.", "error")
                return redirect(url_for('login'))
            
            hashed_password = user.get('senha', None)
            if hashed_password is None:
                flash("Erro interno, tente novamente.", "error")
                return redirect(url_for('login'))
            
            if check_password_hash(hashed_password, password):
                session['usuario_id'] = str(user['_id'])
                flash("Login realizado com sucesso!", "success")
                return redirect(url_for('index'))
            else:
                flash("Usuário ou senha inválidos, tente novamente.", "error")
                return redirect(url_for('login'))
        
        except Exception as e:
            print(f"Erro no login: {e}")
            flash("Erro interno no servidor, tente novamente.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')





#______________________________________________________________________________#
###################### FRDLOGAR USUARIO######################################
#______________________________________________________________________________#


@app.route('/logout')
def logout():
    session.pop('usuario_id', None)  # Remove o ID do usuário da sessão
    flash("Você foi desconectado com sucesso!", "success")
    return redirect(url_for('login'))

def send_email(recipient, code):
    try:
        smtp = smtplib.SMTP('smtp.office365.com', 587)
        smtp.starttls()
        smtp.login(email_user, email_password)
        msg = MIMEText(f"Seu código de validação é {code}.")
        msg['Subject'] = "Código de Validação"
        msg['From'] = email_user
        msg['To'] = recipient
        smtp.sendmail(email_user, recipient, msg.as_string())
        smtp.quit()
        print(f"Email enviado com sucesso para {recipient}")
    except Exception as e:
        print(f"Erro ao enviar o e-mail: {e}")


#______________________________________________________________________________#
######################T RECUPERAR SENHA ######################################
#______________________________________________________________________________#

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form['email']

        # Verifica se o e-mail existe no banco
        usuario = mongo.db.usuarios.find_one({"email": email})
        if not usuario:
            flash('E-mail não encontrado.', 'error')
            return redirect(url_for('login'))  # Mantém o usuário na página do login

        # Gera um token seguro
        token = serializer.dumps(str(usuario["_id"]), salt='reset-senha')

        # Cria um link seguro para redefinição de senha
        link = url_for('redefinir_senha', token=token, _external=True)

        # Envia o e-mail
        msg = Message('Redefinição de Senha', sender='seu_email@gmail.com', recipients=[email])
        msg.body = f'Clique no link para redefinir sua senha (válido por 5 minutos):\n\n{link}'

        try:
            mail.send(msg)
            flash('E-mail de recuperação enviado!', 'success')
        except Exception as e:
            print(f'Erro ao enviar e-mail: {e}')
            flash('Erro ao enviar e-mail. Tente novamente mais tarde.', 'error')

        return redirect(url_for('login'))  # Mantém o usuário na tela de login

    # Se for GET, apenas renderiza a página
    return render_template('recuperar_senha.html')




@app.route('/senha_alterada')
def senha_alterada():
    return render_template('senha_alterada_sucesso.html')





    #______________________________________________________________________________#
######################  ESQUECI SENHA ######################################
#______________________________________________________________________________#
import re
@app.route('/redefinir_senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    try:
        # Carrega o ID do usuário do token e verifica se ele é válido
        user_id = serializer.loads(token, salt='reset-senha', max_age=300)  # Token expira em 5 min
        usuario = mongo.db.usuarios.find_one({"_id": ObjectId(user_id)})

        if not usuario:
            flash("Usuário não encontrado.", "danger")
            return redirect(url_for('recuperar_senha'))

        # 🔴 Comentando a verificação da flag senha_alterada
        # if usuario.get('senha_alterada', False):
        #     flash("Este link já foi usado ou a senha já foi alterada. Solicite um novo link.", "danger")
        #     return render_template('erro_link_expirado.html')  # Criar essa página informando erro

    except SignatureExpired:
        flash("O link expirou. Solicite um novo.", "danger")
        return render_template('erro_link_expirado.html')

    except BadSignature:
        flash("O link é inválido.", "danger")
        return render_template('erro_link_expirado.html')

    # Se chegou até aqui, mostrar a tela de redefinição de senha normalmente
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')

        # Expressão regular para validar a senha
        password_regex = r"^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$"
        if not re.match(password_regex, nova_senha):
            flash("A senha deve ter pelo menos 8 caracteres, incluindo letras maiúsculas, números e caracteres especiais.", "danger")
            return render_template('redefinir_senha.html', token=token)

        if nova_senha != confirmar_senha:
            flash("As senhas não coincidem.", "danger")
            return render_template('redefinir_senha.html', token=token)

        # Atualiza a senha (sem a flag senha_alterada)
        senha_hash = generate_password_hash(nova_senha)
        resultado = mongo.db.usuarios.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"senha": senha_hash}}  # 🔴 Removendo "senha_alterada": True
        )

        if resultado.modified_count == 1:
            flash("Senha redefinida com sucesso!", "success")
            return redirect(url_for('login'))
        else:
            flash("Erro ao atualizar a senha. Tente novamente.", "danger")

    return render_template('redefinir_senha.html', token=token)


@app.route('/signup')
def signup():
    # Aqui você pode adicionar o código para renderizar o formulário de cadastro
    return render_template('signup.html')





if __name__ == '__main__':
    app.run(debug=True)
