import os
import requests

# --- Config ---
mistral_api_key = os.getenv("MISTRAL_API_KEY")
github_token = os.getenv("GITHUB_TOKEN")
repo = os.getenv("GITHUB_REPOSITORY")
pr_number = os.getenv("PR_NUMBER")

# --- Récupérer le diff de la PR ---
files_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
headers = {"Authorization": f"token {github_token}"}
files = requests.get(files_url, headers=headers).json()

diffs = []
for f in files:
    filename = f["filename"]
    patch = f.get("patch", "")
    diffs.append(f"### {filename}\n{patch}")

diff_text = "\n\n".join(diffs)

# --- Prompt pour Mistral ---
prompt = f"""
Tu es un assistant expert en revue de code. 
Analyse les changements suivants dans une Pull Request GitHub et produis un commentaire structuré.

### Instructions :
1. Résumé clair et concis des changements (3-5 phrases max).
2. Tableau récapitulatif avec colonnes : *Fichier* | *Résumé des changements*.
3. Diagramme de séquence Mermaid (si pertinent) représentant les flux ou appels modifiés.
4. Liste des points d’attention / risques potentiels pour le reviewer.
5. (Optionnel) Idées d’améliorations ou de tests supplémentaires.

### Pull Request Diff :
{diff_text}
"""

# --- Appel API Mistral ---
response = requests.post(
    "https://api.mistral.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {mistral_api_key}"},
    json={
        "model": "mistral-large-latest",  # ou un autre modèle que tu utilises
        "messages": [
            {"role": "system", "content": "Tu es un assistant expert en revue de code."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
)

summary = response.json()["choices"][0]["message"]["content"]

# --- Poster le commentaire sur la PR ---
comments_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
requests.post(
    comments_url,
    headers={"Authorization": f"token {github_token}"},
    json={"body": summary}
)

print("✅ Commentaire posté sur la PR avec succès.")
