/* stage2 - charge utile "second etage" (fileless, lancee via memfd).
 *
 * La cle AES lui est fournie a l'execution (argv[1], hex 32 octets) - comme si
 * elle venait du C2. Elle n'est JAMAIS stockee en clair de maniere persistante :
 * on la garde en memoire XORee avec sha256(pid), et on efface la copie en clair.
 * L'artefact present dans le dump memoire est donc :
 *     struct { "MEMKEY01", mkey[32] = KEY ^ sha256(ascii(pid)), nonce[8] }
 * Pour retrouver KEY il faut le PID du processus (via Volatility) + ce buffer.
 *
 * Compilation : gcc -O2 -o stage2 stage2.c
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* ---- SHA-256 (domaine public, compact) ---- */
typedef struct { uint32_t s[8]; uint64_t n; uint8_t b[64]; size_t c; } sha;
static uint32_t rr(uint32_t x,int n){return (x>>n)|(x<<(32-n));}
static void sha_blk(sha*h,const uint8_t*p){
  static const uint32_t K[64]={
  0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
  0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
  0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
  0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
  0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
  0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
  0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
  0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
  uint32_t w[64],a,b,c,d,e,f,g,hh,t1,t2;int i;
  for(i=0;i<16;i++)w[i]=(p[i*4]<<24)|(p[i*4+1]<<16)|(p[i*4+2]<<8)|p[i*4+3];
  for(i=16;i<64;i++){uint32_t s0=rr(w[i-15],7)^rr(w[i-15],18)^(w[i-15]>>3);
    uint32_t s1=rr(w[i-2],17)^rr(w[i-2],19)^(w[i-2]>>10);w[i]=w[i-16]+s0+w[i-7]+s1;}
  a=h->s[0];b=h->s[1];c=h->s[2];d=h->s[3];e=h->s[4];f=h->s[5];g=h->s[6];hh=h->s[7];
  for(i=0;i<64;i++){uint32_t S1=rr(e,6)^rr(e,11)^rr(e,25);uint32_t ch=(e&f)^(~e&g);
    t1=hh+S1+ch+K[i]+w[i];uint32_t S0=rr(a,2)^rr(a,13)^rr(a,22);
    uint32_t mj=(a&b)^(a&c)^(b&c);t2=S0+mj;hh=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;}
  h->s[0]+=a;h->s[1]+=b;h->s[2]+=c;h->s[3]+=d;h->s[4]+=e;h->s[5]+=f;h->s[6]+=g;h->s[7]+=hh;
}
static void sha_init(sha*h){uint32_t iv[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
  0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};memcpy(h->s,iv,32);h->n=0;h->c=0;}
static void sha_upd(sha*h,const uint8_t*p,size_t l){h->n+=l;while(l--){h->b[h->c++]=*p++;
  if(h->c==64){sha_blk(h,h->b);h->c=0;}}}
static void sha_fin(sha*h,uint8_t*o){uint64_t bits=h->n*8;uint8_t pad=0x80;sha_upd(h,&pad,1);
  pad=0;while(h->c!=56)sha_upd(h,&pad,1);uint8_t L[8];int i;for(i=0;i<8;i++)L[i]=bits>>(56-8*i);
  sha_upd(h,L,8);for(i=0;i<8;i++){o[i*4]=h->s[i]>>24;o[i*4+1]=h->s[i]>>16;
  o[i*4+2]=h->s[i]>>8;o[i*4+3]=h->s[i];}}
static void sha256(const uint8_t*p,size_t l,uint8_t*o){sha h;sha_init(&h);sha_upd(&h,p,l);sha_fin(&h,o);}

/* ---- artefact memoire ---- */
struct keyblob { char magic[8]; uint8_t mkey[32]; uint8_t nonce[8]; };
/* volatile : empeche -O2 d'eliminer le marqueur 'magic' (jamais relu dans ce
   binaire, mais c'est precisement lui qui doit rester reperable en memoire). */
static volatile struct keyblob g = { {'M','E','M','K','E','Y','0','1'}, {0}, {0} };

static int unhex(const char*s,uint8_t*o,int n){
  for(int i=0;i<n;i++){unsigned v;if(sscanf(s+2*i,"%2x",&v)!=1)return -1;o[i]=v;}return 0;}

int main(int argc,char**argv){
  if(argc<3){fprintf(stderr,"usage: stage2 <key_hex32> <nonce_hex8>\n");return 1;}
  uint8_t key[32],nonce[8],mask[32];
  if(unhex(argv[1],key,32)||unhex(argv[2],nonce,8))return 1;

  char pidbuf[16];int pl=snprintf(pidbuf,sizeof pidbuf,"%d",(int)getpid());
  sha256((uint8_t*)pidbuf,pl,mask);              /* mask = sha256(ascii(pid)) */

  for(int i=0;i<32;i++)g.mkey[i]=key[i]^mask[i]; /* stockage masque */
  memcpy(g.nonce,nonce,8);

  /* effacer les copies en clair */
  memset(key,0,sizeof key);
  memset(argv[1],'0',strlen(argv[1]));

  /* rester resident pour figurer dans le dump memoire */
  for(;;) pause();
  return 0;
}
