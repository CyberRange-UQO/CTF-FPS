# Writeup : Jackpot

## Énoncé

« Devinez le nombre chanceux entre 1 et 1000 :). Format: `FLAG_X` (seul challenge où le
bruteforce est autorisé) ».

Aucun fichier n'est fourni : le seul moyen est d'essayer les 1000 flags possibles.

## Résolution

On automatise les soumissions via l'API CTFd avec un token (Paramètres → Access Tokens) :

```python
import requests

CTFD = "https://<url-du-ctfd>"
TOKEN = "ctfd_..."
CHALLENGE_ID = 34

s = requests.Session()
s.headers.update({"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"})
for n in range(1, 1001):
    r = s.post(f"{CTFD}/api/v1/challenges/attempt",
               json={"challenge_id": CHALLENGE_ID, "submission": f"FLAG_{n}"}).json()
    if r["data"]["status"] == "correct":
        print("FLAG_%d" % n)
        break
```

Le nombre chanceux était **677**.

## Flag

`FLAG_677`
