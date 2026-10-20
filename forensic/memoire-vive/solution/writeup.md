# Writeup — memoire-vive

**Catégorie :** forensic · **Niveau :** expert · **Requiert :** serveur-compromis
**Flag :** `FPS{memfd_elf_fileless_cle_aes_masquee_par_le_pid}`

Suite de serveur-compromis : l'archive `/var/tmp/.cache/x.enc` (extraite de l'image disque) est
chiffrée par une clé qui **n'existe qu'en mémoire vive**. On fournit le **dump
mémoire brut** (`memoire.raw.xz`) et la **table de symboles Volatility 3**.

```bash
unxz memoire.raw.xz          # -> memoire.raw (256 Mo)
# les symboles vont dans un dossier passe a Volatility via -s
```

## 1. Repérer le processus fileless

```
vol -f memoire.raw -s ./symbols linux.pslist
```

Un processus apparaît sous le nom **`memfd:stage2`** (PPID 1) : sa charge utile
est exécutée depuis un **`memfd` anonyme** (`memfd_create` + `execveat`), donc
**sans fichier sur disque** — absente de l'image analysée dans serveur-compromis. On note son
**PID** (ici `129`).

```
vol -f memoire.raw -s ./symbols linux.proc.Maps --pid 129
# ... memfd:stage2 (deleted)  <- mappings exécutables anonymes
```

## 2. Extraire le binaire depuis la mémoire

Le binaire n'existe que dans le `memfd` : on le reconstruit à partir des mappings du
processus.

```
mkdir dump && vol -f memoire.raw -s ./symbols -o dump/ linux.proc.Maps --pid 129 --dump
```

Les VMA `0x400000` à `0x4c4000` (`/memfd:stage2 (deleted)`) sont contiguës : on les
concatène pour obtenir un ELF statique exploitable dans Ghidra/IDA (les section headers
manquent, mais les program headers suffisent) :

```
cat dump/pid.129.vma.0x400000-*.dmp dump/pid.129.vma.0x401000-*.dmp \
    dump/pid.129.vma.0x494000-*.dmp dump/pid.129.vma.0x4bd000-*.dmp \
    dump/pid.129.vma.0x4c2000-*.dmp > stage2.elf
strings stage2.elf | grep usage   # usage: stage2 <key_hex32> <nonce_hex8>
```

## 3. Comprendre le stockage de la clé (reverse)

Dans `main` (retrouvé via la chaîne `usage: ...`) :

- `argv[1]` (clé AES, 32 octets en hexa) et `argv[2]` (nonce, 8 octets) sont décodés
  avec `sscanf("%2x")` ;
- `getpid()` puis `snprintf("%d")` produisent le PID en ASCII ;
- ce PID passe dans une fonction de hachage reconnaissable à ses constantes
  (`0x6a09e667…`, `0x428a2f98…` : **SHA-256**, détecté aussi par le plugin FindCrypt) ;
- la clé est XORée avec ce hash et écrite dans une variable globale de `.data` qui
  commence par la chaîne `MEMKEY01`, suivie du nonce ;
- la clé en clair et `argv[1]` sont ensuite écrasés, puis le processus attend (`pause`).

La structure est donc `{ "MEMKEY01", mkey[32] = KEY ^ sha256(ascii(pid)), nonce[8] }`.

La copie **vivante** de cette variable est dans la VMA `rw-` du processus
(`pid.129.vma.0x4c2000-0x4c4000.dmp`, à l'adresse `0x4c20e0`). Si on cherche `MEMKEY01`
dans tout le dump, on trouve aussi d'autres copies (image du binaire dans le cache de
pages) dont la `mkey` est **à zéro** : il faut garder celle qui est non nulle.

## 4. Démasquer et déchiffrer

```
KEY  = mkey XOR sha256(ascii(PID))
clair = AES-CTR(KEY, nonce).decrypt(x.enc)   ; puis gunzip
```

```
python3 solve.py --xenc x.enc
# PID stage2    : 129
# KEY demasquee : a3f1c09b...
# FPS{memfd_elf_fileless_cle_aes_masquee_par_le_pid}
```

(`x.enc` s'extrait de l'image de serveur-compromis : `debugfs -R "cat /var/tmp/.cache/x.enc"
serveur.img > x.enc`.)

## Vérification de la logique sans dump

`selftest.py` rejoue la partie crypto/démasquage hors dump (simule un blob
`MEMKEY01` + un PID) :

```
python3 selftest.py        # SELF-TEST OK -> FPS{...}
```

## Comment le dump a été produit

Dump mémoire **réel** capturé sur une VM QEMU (émulation TCG, sans KVM) bootant
le noyau `6.12.107+deb13-amd64`, charge utile fileless lancée dans un initramfs,
RAM physique capturée via le moniteur QEMU (`pmemsave`). L'ISF Volatility 3 est
générée avec `dwarf2json` depuis le `vmlinux` de debug du même noyau. Tout est
reproductible : voir `build/gen-dump.sh` et `build/README.md`.

## Remédiation

- Détecter les exécutions fileless (`memfd:`/`(deleted)` exécutables, auditd
  `execveat`).
- Une clé en mémoire reste extractible : limiter sa durée de vie, cloisonner.
