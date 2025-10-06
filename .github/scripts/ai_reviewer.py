# -*- coding: utf-8 -*-
#!/usr/bin/env python3
import os, json, textwrap, requests
from github import Github, Auth

EXCLUDED_ALWAYS = {".github/scripts/ai_reviewer.py"}

def get_pr_and_patch(repo_fullname, pr_number, gh_token):
    g = Github(auth=Auth.Token(gh_token))
    repo = g.get_repo(repo_fullname)
    pr = repo.get_pull(pr_number)
    patch = ""
    for f in pr.get_files():
        if f.filename in EXCLUDED_ALWAYS: continue
        if f.patch:
            patch += f"\n### {f.filename}\n```diff\n{f.patch}\n```\n"
    return pr, patch.strip()

def call_llm(patch):
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    api_key = os.environ["AZURE_OPENAI_KEY"]
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-10-21"
    prompt = textwrap.dedent(f"""
    Você é um revisor de código. Para cada melhoria, gere um bloco suggestion do GitHub:
    ````suggestion
    <código sugerido>
    ````
    PATCH:
    {patch}
    """).strip()
    body = {
        "messages": [
            {"role": "system", "content": "Responda apenas com sugestões em blocos suggestion."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    headers = {"Content-Type": "application/json", "api-key": api_key}
    r = requests.post(url, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def main():
    repo_fullname = os.environ["GITHUB_REPOSITORY"]
    pr_number = int(os.environ["PR_NUMBER"])
    gh_token = os.environ["GITHUB_TOKEN"]
    pr, patch = get_pr_and_patch(repo_fullname, pr_number, gh_token)
    if not patch:
        print("Nada a revisar.")
        return
    review = call_llm(patch)
    pr.create_issue_comment("### ?? AI Code Review\n\n" + review)
    print("Sugestões postadas.")

if __name__ == "__main__":
    main()
