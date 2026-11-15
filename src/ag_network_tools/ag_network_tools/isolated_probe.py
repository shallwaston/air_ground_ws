"""Minimal read-only C ABI; compiling the probe is an explicit prerequisite."""
import ctypes
import json

C_SOURCE = r'''
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
'''

class ActionReader:
    def __init__(self, library):
        self.library = ctypes.CDLL(str(library))
        self.library.r6_action.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_size_t]
        self.library.r6_action.restype = ctypes.c_int
        self.library.r6_mask.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        self.library.r6_mask.restype = ctypes.c_int

    def action(self, number):
        buffer = ctypes.create_string_buffer(4096)
        error = self.library.r6_action(number, buffer, len(buffer))
        if error:
            raise OSError(error, 'read-only sigaction query failed')
        return json.loads(buffer.value)

    def actions(self):
        return {str(n): self.action(n) for n in (2, 15)}

    def mask(self):
        buffer = ctypes.create_string_buffer(4096)
        error = self.library.r6_mask(buffer, len(buffer))
        if error:
            raise OSError(error, 'read-only mask query failed')
        return json.loads(buffer.value)
