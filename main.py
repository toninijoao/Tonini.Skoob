import os
import sqlite3
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
BANCO = "livros.db"


def criar_banco ():
    conn = sqlite3.connect(BANCO)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS livros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE,
            resumo TEXT,
            personagens TEXT,
            autor TEXT,
            paginas INTEGER
        )
    """)

    conn.commit()
    conn.close()


def gerar_infos_livros(livro):
    prompt = f"""
    Você é um crítico literário experiente que escreve resenhas envolventes.

    Responda SOMENTE com JSON válido. 

    Livro: {livro}

    Formato Obrigatório:
    {{
        "resumo": "texto cp, \\n para quebra de linha",
        "personagens": ["nome1", "nome2"...],
        "autor": "nome do autor",
        "paginas": 123
    }}

    Regras:
- O JSON deve estar em uma única linha ou usar apenas \\n (barra invertida dupla + n) para representar quebras de linha dentro do texto.
- NUNCA use quebras de linha reais (tecla Enter) dentro dos valores das strings.
- Responda apenas o objeto JSON.
- No campo "resumo", use apenas aspas simples ('') se precisar citar algo, nunca aspas duplas.
"""

    try:
        resposta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        response_format = {"type": "json_object"}
    )
        return resposta.choices[0].message.content

    except Exception as e:
        print("Erro na API: ", e)
        return ""
    

def extrair_infos(resposta_json):
    try:
        if not resposta_json:
            return "", "", "", 0
        
        if "```json" in resposta_json:
            resposta_json = resposta_json.split("```json")[1].split("```")[0].strip()
        elif "```" in resposta_json:
            resposta_json = resposta_json.split("```")[1].split("```")[0].strip()

        limpar_json = re.sub(r"[\x00-\x1F]+", " ", resposta_json)
        dados = json.loads(limpar_json)

        resumo = dados.get("resumo", "")
        personagens_lista = dados.get("personagens", [])
        personagens = ", ".join(personagens_lista) if isinstance(personagens_lista, list) else str(personagens_lista)
        autor = dados.get("autor", "")
        paginas = int(dados.get("paginas", 0))

        return resumo, personagens, autor, paginas
    except Exception as e:
        print(f"Erro no JSON: {e}")
        return "", "", "", 0
    
    
def salvar_banco(nome, resumo, personagens, autor, paginas):
    conn = sqlite3.connect(BANCO)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO livros (nome, resumo, personagens, autor, paginas)
            VALUES (?, ?, ?, ?, ?)
        """, (nome, resumo, personagens, autor, paginas))

        conn.commit()
        print("Livro salvo no banco!")

        gerar_txt()

    except sqlite3.IntegrityError:
        print("Esse livro já está cadastrado!")

    finally: conn.close()


def gerar_txt():
    import sqlite3

    conn = sqlite3.connect(BANCO)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT nome, resumo, personagens, autor, paginas
    FROM livros
    ORDER BY id ASC""")
    livros = cursor.fetchall()

    total_livros = len(livros)
    total_paginas = sum(livro[4] for livro in livros)

    conn.close()

    with open("relatorio.txt", "w", encoding="utf-8") as arquivo:

        arquivo.write("🦉 TONINI SKOOB 🦉\n\n")
        arquivo.write(f"📚 Total de livros cadastrados: {total_livros}\n")
        arquivo.write(f"📄 Total de páginas lidas: {total_paginas}\n\n\n")

        for i, livro in enumerate(livros, start=1):
            nome, resumo, personagens, autor, paginas = livro

            resumo_formatado = resumo

            arquivo.write(f"*** 📖 Livro {i}: {nome}\n\n")
            arquivo.write(f"- 📝 Resumo:\n{resumo_formatado}\n\n")
            arquivo.write(f"- 🙋‍♂️ Personagens Principais: {personagens}\n")
            arquivo.write(f"- ✍️ Autor(a): {autor}\n")
            arquivo.write(f"- 📄 Total de Páginas: {paginas}")
            arquivo.write("\n" + "="*60 + "\n\n")


def remover_livro (nome):
    conn = sqlite3.connect(BANCO)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM livros WHERE nome = ?", (nome,))
    livro = cursor.fetchone()

    if not livro:
        print("Livro não encontrado!")
        conn.close()
        return
    
    cursor.execute("DELETE FROM livros WHERE nome = ?", (nome,))
    conn.commit()
    conn.close()

    print("Livro removido com sucesso!")

    gerar_txt()


def main():
    criar_banco()

    while True:
        print("\n--- 🦉 Tonini Skoob 🦉 ---\n")

        print("1 - Cadastrar Livro")
        print("2 - Remover Livro")
        print("3 - Listar Livro")
        print("0 - Sair")

        opcao = input("\nEscolha uma opção: ").strip()

        if opcao == "1":
            nome_livro = input ("Digite o nome do livro: ").strip().title()
            print("\nGerando informações...")
            resposta = gerar_infos_livros(nome_livro)
            resumo, personagens, autor, paginas = extrair_infos(resposta)

            if resumo:
                salvar_banco(nome_livro, resumo, personagens, autor, paginas)
            else:
                print("Não foi possível salvar o livro.")

        elif opcao == "2":
            nome_livro = input("Digite exatamente o nome do livro que deseja remover: ").strip().title()
            remover_livro(nome_livro)

        elif opcao == "3":
            gerar_txt()
            print("Relatório Atualizado!")

        elif opcao == "0":
            print("\nSaindo do sistema...👋")
            break

        else: print("Opção inválida!")


if __name__ == "__main__":
    main()