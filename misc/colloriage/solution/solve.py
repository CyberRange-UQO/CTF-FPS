import sys, math, pypdf
def vig_dec(c, k):
    return ''.join(chr((ord(x)-ord(k[i % len(k)])) % 26 + 65) for i, x in enumerate(c))
r = pypdf.PdfReader(sys.argv[1])
allleft = []
for p in r.pages:
    lines = p.extract_text().split('\n')
    i = lines.index('MOTS A TROUVER')
    letters = lines[1:i]; words = [w for w in lines[i+1:] if w.strip()]
    n = int(math.isqrt(len(letters))); assert n*n == len(letters), len(letters)
    g = [letters[k*n:(k+1)*n] for k in range(n)]
    used = set()
    for w in words:
        found = False
        for y in range(n):
            for x in range(n):
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        if (dy,dx)==(0,0): continue
                        cells = [(y+dy*k, x+dx*k) for k in range(len(w))]
                        if all(0<=a<n and 0<=b<n and g[a][b]==w[k] for k,(a,b) in enumerate(cells)):
                            used |= set(cells); found = True
        assert found, w
    left = ''.join(g[y][x] for y in range(n) for x in range(n) if (y,x) not in used)
    print(lines[0], n, left)
    allleft.append(left)
# remettre les crayons en ordre : une lettre de chaque page a tour de role
c = ''.join(''.join(t) for t in zip(*allleft))
print(c, '->', 'FLAG_' + vig_dec(c, 'CRAYON'))
