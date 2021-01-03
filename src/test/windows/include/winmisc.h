#ifndef _WINMISC_H_
#define _WINMISC_H_
// This file is designed to include all the function used by us.
// It's not a standard library, but could really free ourselves from imitating the directory structure.

#include <windef.h>
#include <winnt.h>

WINAPI HANDLE GetStdHandle(DWORD nStdHandle);

typedef struct _CONSOLE_CURSOR_INFO {
    DWORD  dwSize;
    BOOL   bVisible;
} CONSOLE_CURSOR_INFO;
typedef CONSOLE_CURSOR_INFO* PCONSOLE_CURSOR_INFO;

WINAPI void Sleep(DWORD dwMilliseconds);

WINAPI BOOL SetConsoleCursorInfo(HANDLE hConsoleOutput, CONST CONSOLE_CURSOR_INFO* lpConsoleCursorInfo);

#endif