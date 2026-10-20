# Génération du dump mémoire (F5) — reproductible, sans KVM

Les fichiers livrés au joueur (`defi/memoire.raw.xz` et
`defi/symbols/linux-6.12.107-deb13.json.xz`) sont **déjà générés et testés**.
Ce dossier permet de les **reconstruire** à l'identique.

La capture n'exige **pas** de virtualisation matérielle : QEMU tourne en
émulation logicielle (TCG). On boote un vrai noyau Linux avec un initramfs
minimal qui lance la charge utile *fileless*, puis on capture la RAM physique
du *guest* via le moniteur QEMU (`pmemsave`). Volatility 3 lit ce dump brut
directement.

## Composants

- `stage2.c` — charge utile « second étage » : reçoit la clé AES à l'exécution,
  la stocke **masquée** par `sha256(pid)` dans une structure repérable par le
  marqueur `MEMKEY01`, efface la copie en clair, reste résidente.
  (Le champ magique est `volatile` pour que `-O2` ne l'élimine pas.)
- `loader.c` — exécute `stage2` de façon *fileless* (`memfd_create` +
  `execveat`) : le process apparaît comme `memfd:stage2 (deleted)`.
- `gen-dump.sh` — régénère `memoire.raw.xz` + l'ISF.

## Prérequis hôte

```bash
apt install qemu-system-x86 busybox-static gcc xz-utils cpio
# noyau bootable + ses symboles DWARF (MÊMES versions) :
apt install linux-image-6.12.107+deb13-amd64 linux-image-6.12.107+deb13-amd64-dbg
# dwarf2json :
curl -sL -o /usr/local/bin/dwarf2json \
  https://github.com/volatilityfoundation/dwarf2json/releases/download/v0.9.0/dwarf2json-linux-amd64
chmod +x /usr/local/bin/dwarf2json
```

## Régénération

```bash
./gen-dump.sh
# -> defi/memoire.raw.xz + defi/symbols/linux-6.12.107-deb13.json.xz
```

## Notes

- L'ISF est spécifique à la version du noyau (6.12.107). Le `vmlinuz` booté et
  le `vmlinux` (DWARF) doivent être de la même version, sinon Volatility 3 ne
  résout pas les symboles.
- La clé/nonce AES sont dans `../shared_secret.py` (partagés avec F4 : c'est
  cette clé qui déchiffre `x.enc` planté dans l'image disque F4).
- Résolution : voir `../writeup.md` et `../solve.py` (testé contre le dump réel).
