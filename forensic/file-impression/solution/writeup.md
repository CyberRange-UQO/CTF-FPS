# Writeup — file-impression

**Catégorie :** forensic · **Niveau :** intermédiaire
**Flag :** `FPS{impression_reseau_port_9100_postscript_rendu}`

## Analyse

Les imprimantes réseau acceptent des travaux en **RAW sur le port TCP 9100**
(JetDirect). Chaque job est précédé d'une bannière **PJL** (`@PJL JOB
NAME=...`, `@PJL SET USERNAME=...`) puis du document (ici **PostScript**).

La capture contient 4 travaux. Le job `10.10.20.42 → 10.10.20.9:9100` porte
`@PJL JOB NAME="Rapport Q3 - CONFIDENTIEL"`.

## Résolution

1. **Reassembler** le flux TCP vers `:9100` (Wireshark : *Follow TCP Stream*,
   ou `tshark -z follow,tcp,raw,<n>`, ou scapy par n° de séquence).
2. **Isoler** le PostScript entre `@PJL ENTER LANGUAGE=POSTSCRIPT` et l'UEL
   final (`\x1b%-12345X`).
3. **Rendre** la page :
   ```
   gs -q -dNOPAUSE -dBATCH -r150 -sDEVICE=png16m -sOutputFile=job.png job.ps
   ```

Le flag n'apparaît **pas** dans le flux brut : le PostScript l'émet via un
tableau de **codes ASCII** (`/codes [70 80 83 ...] def ... forall`). Un
`grep FPS{` sur le pcap ne donne rien — il faut vraiment rendre la page.

```
python3 solve.py
# flux 10.10.20.42:50344 -> job 'Rapport Q3 - CONFIDENTIEL'
#   rendu -> FPS{impression_reseau_port_9100_postscript_rendu}
```

## Remédiation

- Chiffrer/authentifier les impressions sensibles (IPPS, pull-printing).
- Segmenter le VLAN imprimantes ; le port 9100 en clair expose tout document.

*(`gen.py` reconstruit le pcap ; rendu validé avec Ghostscript.)*
