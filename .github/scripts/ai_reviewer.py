# -*- coding: utf-8 -*-
import os, sys, json, subprocess, pathlib, textwrap, requests

ALLOWED_EXTS = {
    ".cs", ".csproj", ".sln",
    ".ts", ".tsx", ".js", ".jsx",
    ".py",
    ".json", ".yml", ".yaml",
    ".md"
}

# ---------- GitHub context ----------
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_EVENT_PATH = os.getenv("GITHUB_EVENT_PATH")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not (GITHUB_REPOSITORY and GITHUB_EVENT_PATH and GITHUB_TOKEN):
    print("Missing GitHub environment variables.")
    sys.exit(1)

with open(GITHUB_EVENT_PATH, "r", encoding="utf-8") as f:
    event = json.load(f)

if "pull_request" not in event:
    print("This workflow should be triggered by pull_request.")
    sys.exit(0)

pr = event["pull_request"]
pr_number = pr["number"]
base_sha = pr["base"]["sha"]
head_sha = pr["head"]["sha"]

# ---------- Azure OpenAI ----------
AZ_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZ_API_KEY = os.getenv("AZURE_OPENAI_KEY")
AZ_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AUTO_COMMIT = os.getenv("AUTO_COMMIT", "false")

# ---------- Helpers ----------
def run(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, text=True, errors="replace").strip()

def git_diff(base: str, head: str) -> str:
    # unified diff with enough context
    return run(f"git diff {base}..{head}")

def gather_changed_files(base: str, head: str):
    out = run(f"git diff --name-only {base}..{head}")
    return [f for f in out.splitlines() if pathlib.Path(f).suffix in ALLOWED_EXTS]

def call_azure_openai(system_prompt: str, user_prompt: str) -> str:
    if not (AZ_ENDPOINT and AZ_API_KEY and AZ_DEPLOYMENT):
        raise RuntimeError("Azure OpenAI vars missing")
    url = f"{AZ_ENDPOINT}/openai/deployments/{AZ_DEPLOYMENT}/chat/completions?api-version=2025-01-01-preview"
    headers = {"api-key": AZ_API_KEY, "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def post_pr_comment(body: str):
    owner, repo = GITHUB_REPOSITORY.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    r = requests.post(url, headers=headers, json={"body": body})
    if r.status_code >= 300:
        print("Failed to post PR comment:", r.status_code, r.text)

def build_prompt(diff_text: str) -> str:
    instructions = textwrap.dedent("""
    You are a senior code reviewer. Review the provided unified diff from a GitHub Pull Request.
    - Identify bugs, smells, missing validations, performance or security issues.
    - When proposing small edits, use GitHub-style suggestion blocks with fenced code:

````suggestion
      <replacement code>
````

    - Keep suggestions minimal and directly applicable.
    - For larger refactors, describe the change and include the most critical snippet as a suggestion (also using a suggestion block).
    - IMPORTANT: Preserve indentation and syntax; do not include file headers inside suggestion blocks.
    """).strip()
    return instructions + "\n\nDIFF:\n" + diff_text

# ---------- Main ----------
def main():
    # Filter for relevant files
    changed = gather_changed_files(base_sha, head_sha)
    if not changed:
        print("No allowed files changed; nothing to review.")
        return

    raw_diff = git_diff(base_sha, head_sha)
    if not raw_diff.strip():
        print("Empty diff; nothing to review.")
        return

    # Avoid huge payloads
    MAX_CHARS = 120_000
    payload_diff = raw_diff[:MAX_CHARS]

    system = "You are a meticulous code review assistant for GitHub Pull Requests."
    user = build_prompt(payload_diff)

    print("Calling Azure OpenAI...")
    review = call_azure_openai(system, user)

    # Save artifact
    with open("ai_suggestions.md", "w", encoding="utf-8") as f:
        f.write(review)

    # Post comment on PR
    body = "### ?? AI Code Review\n\n" + review
    post_pr_comment(body)

    # Removido: lógica de auto-commit e aplicação de patch.
    # As sugestões serão exibidas como blocos de sugestão no comentário do PR.
    # O botão "Commit suggestion" aparecerá automaticamente no GitHub para cada bloco de sugestão.

    print("AI review completed.")

if __name__ == "__main__":
    main()
