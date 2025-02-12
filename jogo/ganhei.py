import random

def escolher_jogos(arquivo, quantidade=7):
    with open(arquivo, 'r') as f:
        jogos = [linha.strip() for linha in f.readlines()]
    
    if len(jogos) < quantidade:
        raise ValueError("O arquivo tem menos jogos do que a quantidade solicitada.")
    
    jogos_selecionados = random.sample(jogos, quantidade)
    
    return jogos_selecionados

# Uso
aquivo_jogos = "jogos_filtrados.txt"
jogos_sorteados = escolher_jogos(aquivo_jogos)

for jogo in jogos_sorteados:
    print(jogo)