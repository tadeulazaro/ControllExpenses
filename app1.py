import os
from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

# Conexão com MongoDB (utilizando a URI local)
MONGO_URI = os.getenv('MONGO_URI')  # Variável de ambiente do MongoDB
client = MongoClient(MONGO_URI)
db = client.get_database()  # Conectando ao banco de dados especificado em MONGO_URI

# Criando a aplicação Flask
app = Flask(__name__)

@app.route("/teste")
def teste():
    # Buscar todas as despesas
    despesas = db.despesas.find()  # Retorna um cursor
    resposta = []

    for despesa in despesas:
        category_id = despesa.get("category_id")
        # Buscar categoria se existir
        categoria = db.categories.find_one({"_id": category_id}) if category_id else None
        descricao = despesa.get("description", "Sem descrição")
        nome_categoria = categoria["name"] if categoria else "Não encontrada"
        resposta.append(f"Despesa: {descricao} - Categoria: {nome_categoria}")

    # Retornar a lista de despesas ou mensagem caso não haja
    return "<br>".join(resposta) if resposta else "Nenhuma despesa encontrada."

# Iniciar o servidor Flask
if __name__ == "__main__":
    app.run(debug=True)
