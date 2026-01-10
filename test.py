import os

env_file=".env" 
toml_file="secrets.toml"
if not os.path.exists(env_file):
    print(f"Arquivo {env_file} não encontrado!")

print(f"🦈 Convertendo {env_file} para TOML...")

toml_lines = []

with open(env_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        # Ignora linhas vazias ou comentários
        if not line or line.startswith("#"):
            continue

        if "=" in line:
            # Separa apenas no primeiro '=' para evitar quebrar chaves que tenham = no valor
            key, value = line.split("=", 1)
            
            # Remove aspas que já existam no .env para não duplicar
            value = value.strip().strip("'").strip('"')
            
            # Formata para TOML
            toml_lines.append(f'{key.strip()} = "{value}"')

        # Imprime o resultado para você copiar
        print("\n--- COPIE O CONTEÚDO ABAIXO PARA O STREAMLIT SECRETS ---\n")
        print("\n".join(toml_lines))
        print("\n--------------------------------------------------------")

    # Opcional: Salvar em arquivo
    with open(toml_file, "w") as f:
        f.write("\n".join(toml_lines))