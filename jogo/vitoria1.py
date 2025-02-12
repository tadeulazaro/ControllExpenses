import random

# Função para gerar um resultado aleatório de 15 números da Lotofácil
def gerar_resultado_lotofacil():
    return tuple(sorted(random.sample(range(1, 26), 15)))

# Gerar os últimos 30 resultados
ultimos_resultados = [gerar_resultado_lotofacil() for _ in range(30)]

# Salvar no arquivo 'ultimos_resultados.txt'
with open('ultimos_resultados.txt', 'w') as f:
    for resultado in ultimos_resultados:
        f.write(f"({', '.join(map(str, resultado))})\n")

print("Últimos 30 resultados gerados e salvos em 'ultimos_resultados.txt'.")


# Função para carregar os resultados da Lotofácil a partir do arquivo
def carregar_resultados(arquivo):
    """
    Carrega os últimos resultados da Lotofácil a partir de um arquivo.
    """
    with open(arquivo, 'r') as f:
        return [tuple(map(int, linha.strip().strip("()").split(", "))) for linha in f if linha.strip()]

# Função para carregar os jogos filtrados a partir de um arquivo
def carregar_jogos_filtrados(arquivo):
    """
    Carrega os jogos filtrados a partir de um arquivo.
    """
    with open(arquivo, 'r') as f:
        return [tuple(map(int, linha.strip().strip("()").split(", "))) for linha in f if linha.strip()]

# Função para contar o número de acertos entre um jogo e um resultado
def contar_acertos(jogo, resultado):
    """
    Conta o número de acertos entre um jogo e um resultado.
    """
    return len(set(jogo) & set(resultado))

# Função para verificar se o jogo já foi sorteado com 14 ou 15 acertos
def jogo_nao_foi_sorteado_com_pontos(resultados, jogo):
    """
    Verifica se o jogo já foi sorteado com 14 ou 15 pontos.
    """
    for resultado in resultados:
        acertos = contar_acertos(jogo, resultado)
        if acertos == 14 or acertos == 15:
            return False  # Se o jogo já foi sorteado com 14 ou 15 acertos, não inclui ele
    return True  # Se o jogo não foi sorteado com 14 ou 15 acertos, inclui ele

# Função para encontrar os jogos mais semelhantes aos últimos resultados
def encontrar_jogos_similares(resultados, jogos_filtrados):
    """
    Encontra os 10 jogos mais semelhantes aos últimos resultados da Lotofácil,
    considerando que o jogo não tenha saído com 14 ou 15 pontos em resultados passados.
    """
    jogos_similares = []
    
    for jogo in jogos_filtrados:
        if not jogo_nao_foi_sorteado_com_pontos(resultados, jogo):
            continue  # Ignora o jogo se já saiu com 14 ou 15 pontos em algum resultado
        
        similaridades = [contar_acertos(jogo, resultado) for resultado in resultados]
        max_acertos = max(similaridades)
        jogos_similares.append((jogo, max_acertos))
    
    # Ordena os jogos com base no número de acertos e seleciona os 10 mais semelhantes
    jogos_similares.sort(key=lambda x: x[1], reverse=True)
    return jogos_similares[:10]

# Carregar os arquivos de resultados e jogos filtrados
arquivo_resultados = 'ultimos_resultados.txt'
arquivo_jogos_filtrados = 'jogos_filtrados.txt'

resultados = carregar_resultados(arquivo_resultados)
jogos_filtrados = carregar_jogos_filtrados(arquivo_jogos_filtrados)

# Encontrar os jogos mais semelhantes
jogos_similares = encontrar_jogos_similares(resultados, jogos_filtrados)

# Salvar os 10 jogos mais semelhantes no arquivo 'jogos_para_ganhar.txt'
with open('jogos_para_ganhar.txt', 'w') as f:
    for jogo, acertos in jogos_similares:
        f.write(f"Jogo: {jogo}, Acertos: {acertos}\n")

print("Os 10 jogos mais semelhantes, sem 14 ou 15 acertos, foram salvos em 'jogos_para_ganhar.txt'.")
