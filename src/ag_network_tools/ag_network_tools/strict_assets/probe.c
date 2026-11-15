
#define _GNU_SOURCE
#include <signal.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
int r6_action(int n,char *out,size_t cap){
 struct sigaction a={0};if(sigaction(n,NULL,&a))return errno;
 int k=snprintf(out,cap,"{\"handler\":\"%llx\",\"kind\":%d,\"flags\":%u,\"mask\":[",(unsigned long long)(uintptr_t)a.sa_handler,a.sa_handler==SIG_DFL?0:a.sa_handler==SIG_IGN?1:2,(unsigned)a.sa_flags);int comma=0;
 if(k<0||(size_t)k>=cap)return ERANGE;
 for(int i=1;i<NSIG;i++)if(sigismember(&a.sa_mask,i)==1){int r=snprintf(out+k,cap-k,"%s%d",comma?",":"",i);if(r<0||(size_t)r>=cap-k)return ERANGE;k+=r;comma=1;}
 if(cap-(size_t)k<3)return ERANGE;snprintf(out+k,cap-k,"]}");return 0;
}
int r6_mask(char *out,size_t cap){sigset_t m;int e=pthread_sigmask(SIG_SETMASK,NULL,&m);if(e)return e;int k=snprintf(out,cap,"[");int comma=0;for(int i=1;i<NSIG;i++)if(sigismember(&m,i)==1){int r=snprintf(out+k,cap-k,"%s%d",comma?",":"",i);if(r<0||(size_t)r>=cap-k)return ERANGE;k+=r;comma=1;}if(cap-(size_t)k<2)return ERANGE;snprintf(out+k,cap-k,"]");return 0;}
