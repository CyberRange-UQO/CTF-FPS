#!/usr/bin/env python3
"""Genere access.log realiste avec une SQLi booleenne a l'aveugle.

~20 000 lignes de trafic (legitime, bots, scanners) + un attaquant unique qui
extrait un secret caractere par caractere via
  id=1 AND SUBSTRING((SELECT secret FROM config),n,1)>CHAR(x)
Le flag n'apparait JAMAIS en clair : il faut distinguer TRUE/FALSE a la taille
de la reponse (TRUE=4812, FALSE=1203) et reconstruire chaque caractere.
"""
import os
import random
import urllib.parse
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))

FLAG = "FPS{injection_sql_aveugle_boolean_based_reconstruite}"
ATTACKER = "203.0.113.47"
SIZE_TRUE, SIZE_FALSE = 4812, 1203

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
]
PAGES = ["/", "/produits.php", "/produits.php?id=3", "/produits.php?id=7",
         "/contact.php", "/a-propos.php", "/blog/", "/blog/securite-2026",
         "/panier.php", "/css/style.css", "/js/app.js", "/img/logo.png",
         "/favicon.ico", "/img/banniere.jpg"]
STATIC = (".css", ".js", ".png", ".jpg", ".ico")


def clf(ip, dt, method, path, status, size, ua, referer="-"):
    ts = dt.strftime("%d/%b/%Y:%H:%M:%S +0000")
    return (f'{ip} - - [{ts}] "{method} {path} HTTP/1.1" {status} {size} '
            f'"{referer}" "{ua}"')


def rand_ip(rng):
    return f"{rng.choice([24,41,70,99,142,196,201])}.{rng.randint(0,255)}." \
           f"{rng.randint(0,255)}.{rng.randint(1,254)}"


def main():
    os.makedirs(DEFI, exist_ok=True)
    rng = random.Random(1337)
    start = datetime(2026, 9, 14, 0, 0, 0)
    rows = []  # (datetime, line)

    # --- trafic legitime (~18 500 lignes sur 2 jours) ---
    for _ in range(18500):
        dt = start + timedelta(seconds=rng.randint(0, 2 * 24 * 3600))
        ip = rand_ip(rng)
        path = rng.choice(PAGES)
        ua = rng.choice(UAS)
        if path.endswith(STATIC):
            status, size = 200, rng.randint(400, 60000)
        else:
            status = rng.choices([200, 304, 404], [0.9, 0.07, 0.03])[0]
            size = rng.randint(1800, 5200) if status == 200 else rng.randint(180, 500)
        rows.append((dt, clf(ip, dt, "GET", path, status, size, ua,
                             referer="https://www.corp.local/")))

    # --- bots / scanners (bruit) ---
    for _ in range(1000):
        dt = start + timedelta(seconds=rng.randint(0, 2 * 24 * 3600))
        ip = rand_ip(rng)
        path = rng.choice(["/wp-login.php", "/.env", "/admin/", "/phpmyadmin/",
                           "/robots.txt", "/.git/config", "/backup.zip"])
        status = rng.choices([404, 403, 200], [0.8, 0.15, 0.05])[0]
        rows.append((dt, clf(ip, dt, "GET", path, status,
                             rng.randint(150, 600),
                             "Mozilla/5.0 (compatible; masscan/1.3)")))

    # --- attaque SQLi booleenne (recherche dichotomique par caractere) ---
    atk = start + timedelta(days=1, hours=2, minutes=13)  # fenetre ~20 min
    atk_ua = "Mozilla/5.0 (X11; Linux x86_64) sqli-tool/0.1"
    for n, ch in enumerate(FLAG, start=1):
        target = ord(ch)
        lo, hi = 31, 127  # on cherche target dans (lo, hi]
        while hi - lo > 1:
            mid = (lo + hi) // 2
            # vrai si target > mid
            cond_true = target > mid
            payload = (f"1 AND SUBSTRING((SELECT secret FROM config),{n},1)"
                       f">CHAR({mid})")
            path = "/produits.php?id=" + urllib.parse.quote(payload)
            size = SIZE_TRUE if cond_true else SIZE_FALSE
            atk += timedelta(seconds=rng.randint(1, 4))
            rows.append((atk, clf(ATTACKER, atk, "GET", path, 200, size, atk_ua,
                                  referer="-")))
            if cond_true:
                lo = mid
            else:
                hi = mid

    rows.sort(key=lambda r: r[0])
    out = os.path.join(DEFI, "access.log")
    with open(out, "w") as f:
        f.write("\n".join(line for _, line in rows) + "\n")
    print(f"genere: {out}  ({len(rows)} lignes), attaquant={ATTACKER}")


if __name__ == "__main__":
    main()
