#ifndef _WINDEF_H_
#define _WINDEF_H_

#define STDCALL __stdcall
#define FASTCALL __fastcall
#define WINAPI __stdcall

// for now, ignore unsigned
#define unsigned

#define VOID void
#define CONST const
#define TRUE 1
#define FALSE 0

typedef unsigned long       DWORD;
typedef int                 BOOL;
typedef unsigned char       BYTE;
typedef unsigned short      WORD;
// typedef float               FLOAT;
// typedef FLOAT               *PFLOAT;
typedef BOOL                *PBOOL;
typedef BOOL                *LPBOOL;
typedef BYTE                *PBYTE;
typedef BYTE                *LPBYTE;
typedef int                 *PINT;
typedef int                 *LPINT;
typedef WORD                *PWORD;
typedef WORD                *LPWORD;
typedef long                *LPLONG;
typedef DWORD               *PDWORD;
typedef DWORD               *LPDWORD;
typedef void                *LPVOID;

typedef int                 INT;
typedef unsigned int        UINT;
typedef unsigned int        *PUINT;

#endif