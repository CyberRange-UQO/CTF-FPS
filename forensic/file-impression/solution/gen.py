#!/usr/bin/env python3
"""Genere le defi file-impression.

Pcap d'un reseau de bureau : plusieurs postes envoient des travaux d'impression
en RAW sur le port 9100 d'une imprimante reseau. Chaque job = banniere PJL +
document PostScript. Le job CONFIDENTIEL contient le flag, mais celui-ci est
emis via un tableau de codes ASCII (invisible a un grep du flux) : il faut
RENDRE la page (gs) pour le lire.
"""
import os
import random

from scapy.all import (Ether, IP, TCP, UDP, DNS, DNSQR, Raw, wrpcap)

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))

FLAG = "FPS{impression_reseau_port_9100_postscript_rendu}"
PRINTER = "10.10.20.9"           # imprimante reseau
PRINTER_MAC = "00:11:22:aa:bb:09"

UEL = b"\x1b%-12345X"


def pjl_job(name, user, ps_body):
    return (UEL
            + f'@PJL JOB NAME="{name}"\r\n'.encode()
            + f'@PJL SET USERNAME="{user}"\r\n'.encode()
            + b"@PJL ENTER LANGUAGE=POSTSCRIPT\r\n"
            + ps_body
            + UEL)


def ps_simple(title, lines):
    body = [b"%!PS-Adobe-3.0",
            b"/Helvetica-Bold findfont 22 scalefont setfont",
            b"72 760 moveto (" + title.encode() + b") show",
            b"/Helvetica findfont 14 scalefont setfont"]
    y = 720
    for ln in lines:
        body.append(f"72 {y} moveto ({ln}) show".encode())
        y -= 22
    body.append(b"showpage")
    return b"\n".join(body) + b"\n"


def ps_confidential(flag):
    codes = " ".join(str(ord(c)) for c in flag)
    return (b"%!PS-Adobe-3.0\n"
            b"/Helvetica-Bold findfont 24 scalefont setfont\n"
            b"72 760 moveto (RAPPORT TRIMESTRIEL - CONFIDENTIEL) show\n"
            b"/Helvetica findfont 13 scalefont setfont\n"
            b"72 730 moveto (Diffusion restreinte - direction uniquement.) show\n"
            b"72 700 moveto (Code de validation du document :) show\n"
            b"/Courier-Bold findfont 18 scalefont setfont\n"
            b"/codes [" + codes.encode() + b"] def\n"
            b"72 670 moveto\n"
            b"codes { /c exch def ( ) dup 0 c put show } forall\n"
            b"showpage\n")


def tcp_stream(pkts, src_ip, src_mac, sport, payload, t0):
    """Conversation TCP realiste src->PRINTER:9100 portant `payload`."""
    dmac, dip, dport = PRINTER_MAC, PRINTER, 9100
    isn_c = random.randint(1000, 4_000_000)
    isn_s = random.randint(1000, 4_000_000)

    def c2s(flags, seq, ack, data=b""):
        p = (Ether(src=src_mac, dst=dmac) / IP(src=src_ip, dst=dip)
             / TCP(sport=sport, dport=dport, flags=flags, seq=seq, ack=ack)
             / (Raw(data) if data else Raw(b"")))
        if not data:
            p = (Ether(src=src_mac, dst=dmac) / IP(src=src_ip, dst=dip)
                 / TCP(sport=sport, dport=dport, flags=flags, seq=seq, ack=ack))
        return p

    def s2c(flags, seq, ack):
        return (Ether(src=dmac, dst=src_mac) / IP(src=dip, dst=src_ip)
                / TCP(sport=dport, dport=sport, flags=flags, seq=seq, ack=ack))

    t = t0
    # handshake
    p = c2s("S", isn_c, 0); p.time = t; pkts.append(p); t += 0.001
    p = s2c("SA", isn_s, isn_c + 1); p.time = t; pkts.append(p); t += 0.001
    p = c2s("A", isn_c + 1, isn_s + 1); p.time = t; pkts.append(p); t += 0.002

    seq = isn_c + 1
    for i in range(0, len(payload), 1400):
        chunk = payload[i:i + 1400]
        p = c2s("PA", seq, isn_s + 1, chunk); p.time = t; pkts.append(p)
        seq += len(chunk); t += 0.003
        p = s2c("A", isn_s + 1, seq); p.time = t; pkts.append(p); t += 0.001
    # teardown
    p = c2s("FA", seq, isn_s + 1); p.time = t; pkts.append(p); t += 0.001
    p = s2c("FA", isn_s + 1, seq + 1); p.time = t; pkts.append(p); t += 0.001
    p = c2s("A", seq + 1, isn_s + 2); p.time = t; pkts.append(p); t += 0.5
    return t


def main():
    os.makedirs(DEFI, exist_ok=True)
    random.seed(99)
    pkts = []
    t = 1_726_300_000.0  # ~ 2026-09-14

    jobs = [
        ("10.10.20.21", "00:11:22:aa:00:21", 50100, "Ordre du jour - reunion",
         "mtremblay", ps_simple("Ordre du jour - reunion hebdo", [
             "1. Suivi des projets en cours",
             "2. Budget T4", "3. Varia"])),
        ("10.10.20.34", "00:11:22:aa:00:34", 50231, "Note interne RH",
         "plandry", ps_simple("Note interne - Ressources humaines", [
             "Rappel : fermeture des bureaux le 24 decembre.",
             "Merci de poser vos conges avant le 1er decembre."])),
        ("10.10.20.42", "00:11:22:aa:00:42", 50344,
         "Rapport Q3 - CONFIDENTIEL", "jbeaulieu", ps_confidential(FLAG)),
        ("10.10.20.27", "00:11:22:aa:00:27", 50077, "Etiquette expedition",
         "scotefrancoeur", ps_simple("Bon d'expedition", [
             "Destinataire : entrepot Est", "Colis : 3", "Poids : 14 kg"])),
    ]

    for src_ip, src_mac, sport, name, user, ps in jobs:
        payload = pjl_job(name, user, ps)
        t = tcp_stream(pkts, src_ip, src_mac, sport, payload, t)

    # bruit reseau : quelques requetes DNS
    for i in range(6):
        q = (Ether(src="00:11:22:aa:00:21", dst="00:11:22:aa:bb:01")
             / IP(src="10.10.20.21", dst="10.10.20.1")
             / UDP(sport=40000 + i, dport=53)
             / DNS(rd=1, qd=DNSQR(qname="www.corp.local")))
        q.time = t; pkts.append(q); t += 0.2

    pkts.sort(key=lambda p: p.time)
    out = os.path.join(DEFI, "capture-impression.pcap")
    wrpcap(out, pkts)
    print("genere:", out, f"({len(pkts)} paquets)")


if __name__ == "__main__":
    main()
