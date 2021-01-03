#ifndef _STDDEF_H_
#define _STDDEF_H_

// ignore __cdecl now
#define __cdecl

#ifdef _WIN64
    typedef long long       size_t;
    typedef long long       ptrdiff_t;
    typedef long long       intptr_t;
#else
    typedef int             size_t;
    typedef int             ptrdiff_t;
    typedef int             intptr_t;
#endif

#endif