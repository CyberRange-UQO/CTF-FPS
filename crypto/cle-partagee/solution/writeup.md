# Writeup — cle-partagee

**Catégorie :** crypto · **Niveau :** débutant
**Flag :** `FPS{reutiliser_un_keystream_xor_est_un_two_time_pad}`

## Analyse

Un chiffrement XOR est sûr uniquement si le keystream n'est **jamais réutilisé**
(c'est un one-time pad). Ici la même clé a servi pour deux fichiers :

```
brochure.pdf.enc = brochure.pdf  XOR  K
memo.enc         = memo          XOR  K
```

Or la brochure est un document **public** : on en a la version en clair.

## Résolution

On récupère le keystream avec le document connu, puis on déchiffre le memo :

```python
K    = brochure_clair XOR brochure_enc
memo = memo_enc XOR K[:len(memo_enc)]
```

```
python3 solve.py
# ... Jeton de validation : FPS{reutiliser_un_keystream_xor_est_un_two_time_pad}
```

Le keystream recouvre toute la longueur du memo (le memo est plus court que la
brochure), donc le déchiffrement est complet. Même sans la brochure, un
`brochure_enc XOR memo_enc = brochure XOR memo` suivi d'un *crib-dragging* sur
l'en-tête `%PDF` suffirait.

## Remédiation

- Un keystream ne se réutilise jamais (nonce unique par message).
- Préférer un chiffrement authentifié standard (AES-GCM, ChaCha20-Poly1305).
