def corrigir_arquivo(arquivo_entrada, arquivo_saida):
    """Corrige problemas de formatação no arquivo de entrada."""
    with open(arquivo_entrada, 'r') as f_in, open(arquivo_saida, 'w') as f_out:
        for linha in f_in:
            # Remove espaços extras e corrige linhas coladas
            linha_corrigida = linha.replace(")(", ")\n(").strip()
            if linha_corrigida:  
                f_out.write(linha_corrigida + "\n")
    print(f"Arquivo corrigido salvo como {arquivo_saida}")


def carregar_jogos(arquivo):
    """Carrega os jogos do arquivo corrigido, tratando erros de formatação."""
    jogos = []
    with open(arquivo, 'r') as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                try:
                    # Remove parênteses e divide pelos números
                    jogo = tuple(map(int, linha.strip("()\n").split(",")))
                    jogos.append(jogo)
                except ValueError:
                    print(f"Erro ao processar linha: {linha}")
    return jogos


def validar_jogo(jogo):
    """Aplica regras para validar os jogos."""
    # Regra 1: Máximo de 7 pares e 8 ímpares (ou vice-versa)
    pares = sum(1 for num in jogo if num % 2 == 0)
    impares = len(jogo) - pares
    if pares > 8 or impares > 8:
        return False

    # Regra 2: Não permitir sequências de mais de 8 números consecutivos
    contador_sequencia = 1
    for i in range(len(jogo) - 1):
        if jogo[i] + 1 == jogo[i + 1]:
            contador_sequencia += 1
            if contador_sequencia > 8:
                return False
        else:
            contador_sequencia = 1

    # Regra 3: Limitar a soma dos números a um intervalo razoável (ex: 180 a 220)
    soma_jogo = sum(jogo)
    if soma_jogo < 180 or soma_jogo > 220:
        return False

    # Regra 4: Evitar repetições excessivas do mesmo dígito (ex: mais de 4 números com final 5)
    contagem_finais = {i: 0 for i in range(10)}
    for num in jogo:
        contagem_finais[num % 10] += 1
    if any(v > 4 for v in contagem_finais.values()):
        return False

    return True


def reduzir_jogos(jogos):
    """Reduz os jogos com base nas regras de validação."""
    jogos_validos = [jogo for jogo in jogos if validar_jogo(jogo)]
    print(f"Jogos reduzidos de {len(jogos)} para {len(jogos_validos)}")
    return jogos_validos


def salvar_jogos(jogos, arquivo_saida):
    """Salva os jogos reduzidos em um arquivo."""
    with open(arquivo_saida, 'w') as f:
        for jogo in jogos:
            f.write(f"{jogo}\n")
    print(f"Jogos válidos salvos em {arquivo_saida}")


# Arquivos
arquivo_entrada = "combinacoes_eliminadas.txt"
arquivo_corrigido = "combinacoes_corrigidas.txt"
arquivo_saida = "jogos_filtrados.txt"

# Corrigir o arquivo original
corrigir_arquivo(arquivo_entrada, arquivo_corrigido)

# Carregar os jogos corrigidos
jogos = carregar_jogos(arquivo_corrigido)

# Aplicar regras de filtragem e reduzir jogos
jogos_reduzidos = reduzir_jogos(jogos)

# Salvar jogos filtrados
salvar_jogos(jogos_reduzidos, arquivo_saida)
