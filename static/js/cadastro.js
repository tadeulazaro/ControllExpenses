document.querySelector('form').addEventListener('submit', function(event) {
    const password = document.querySelector('input[name="senha"]').value;
    const regex = /^(?=.*[A-Z])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{6,}$/;

    // Se a senha não corresponder ao regex, bloqueia o envio e mostra a mensagem de erro
    if (!regex.test(password)) {
        event.preventDefault();  // Impede o envio do formulário
        alert("A senha deve ter pelo menos 6 caracteres, uma letra maiúscula e um caractere especial.");
    }
});
