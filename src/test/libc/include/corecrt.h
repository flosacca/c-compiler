#ifndef _CORECRT_H_
#define _CORECRT_H_

// ignore unsigned
#define unsigned
#define NULL (0)

typedef int                           errno_t;
typedef unsigned short                wint_t;
typedef unsigned short                wctype_t;
typedef long                          __time32_t;
typedef long long                     __time64_t;

#ifdef _WIN64
    typedef unsigned long long  size_t;
    typedef long long           ptrdiff_t;
    typedef long long           intptr_t;

    typedef __time64_t time_t;
#else
    typedef unsigned int    size_t;
    typedef int             ptrdiff_t;
    typedef int             intptr_t;

    typedef __time32_t time_t;
#endif

#endif