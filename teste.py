
import os
import re
import dns.resolver
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, flash

app = Flask(__name__)
app.secret_key = 'secreto'
EMAIL_USER = "tadeusf_sampo@hotmail.com"  # Seu e-mail
EMAIL_PASSWORD = "pmolyumsoyhlmvae"  # Senha de aplicativo gerada

# Função de validação do formato do e-mail com Regex
def validar_email(email):
    padrao_email = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    if re.match(padrao_email, email):
        return True
    return False

# Função de validação de domínio com DNS
def verificar_dominio(email):
    dominio = email.split('@')[1]
    try:
        dns.resolver.resolve(dominio, 'MX')
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return False

# Função para enviar e-mail


def send_email(recipient):
    try:
        smtp = smtplib.SMTP('smtp.office365.com', 587)
        smtp.ehlo()  # A "Hello" command to the server
        smtp.starttls()  # Start TLS encryption
        smtp.ehlo()  # Re-establish connection with encryption

        smtp.login(EMAIL_USER, EMAIL_PASSWORD)  # Use your email and app password
        
        msg = MIMEText("Este é um teste de envio de e-mail.")
        msg['Subject'] = "Teste de E-mail"
        msg['From'] = EMAIL_USER
        msg['To'] = recipient
        
        smtp.sendmail(EMAIL_USER, recipient, msg.as_string())
        smtp.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return False


# Rota principal
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash("Por favor, insira um e-mail.", "error")
            return render_template('index.html')
        
        # Validação do formato do e-mail
        if not validar_email(email):
            flash("O e-mail fornecido não tem um formato válido.", "error")
            return render_template('index.html')
        
        # Verificação do domínio
        if not verificar_dominio(email):
            flash("O domínio do e-mail não é válido.", "error")
            return render_template('index.html')
        
        # Envio do e-mail de teste
        if send_email(email):
            flash("E-mail de teste enviado com sucesso!", "success")
        else:
            flash("Erro ao enviar o e-mail. Tente novamente.", "error")
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
