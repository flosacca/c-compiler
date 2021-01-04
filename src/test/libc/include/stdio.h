#ifndef _STDIO_H_
#define _STDIO_H_

#include <stddef.h>

#define stdin   (&_iob[STDIN_FILENO])
#define stdout  (&_iob[STDOUT_FILENO])
#define stderr  (&_iob[STDERR_FILENO])

#define STDIN_FILENO    0
#define STDOUT_FILENO   1
#define STDERR_FILENO   2

#define EOF             (-1)

#define SEEK_SET         0
#define SEEK_CUR         1
#define SEEK_END         2

typedef struct _iobuf
{
  char  *_ptr;
  int    _cnt;
  char  *_base;
  int    _flag;
  int    _file;
  int    _charbuf;
  int    _bufsiz;
  char  *_tmpfname;
} FILE;

extern FILE _iob[]; /* An array of FILE imported from DLL. */

__cdecl FILE * fopen (const char * _1, const char * _2);
__cdecl FILE * freopen (const char * _1, const char * _2, FILE * _3);
__cdecl int    fflush (FILE *_1);
__cdecl int    fclose (FILE *_1);
__cdecl int    remove (const char *_1);
__cdecl int    rename (const char *_1, const char * _2);
__cdecl FILE * tmpfile ();
__cdecl char * tmpnam (char *_1);

__cdecl int    fprintf (FILE *_1, const char *_2, ...);
__cdecl int    printf (const char *_1, ...);
__cdecl int    sprintf (char *_1, const char *_2, ...);
__cdecl int    fscanf (FILE *_1, const char *_2, ...);
__cdecl int    scanf (const char *_1, ...);
__cdecl int    sscanf (const char *_1, const char *_2, ...);

__cdecl int    fgetc (FILE *_1);
__cdecl char * fgets (char *_1, int _2, FILE *_3);
__cdecl int    fputc (int _1, FILE *_2);
__cdecl int    fputs (const char *_1, FILE *_2);
__cdecl char * gets (char *_1);
__cdecl int    puts (const char *_1);
__cdecl int    ungetc (int _1, FILE *_2);
__cdecl int    getchar();
__cdecl int    putchar(int _1);

__cdecl size_t fread (void* _1, size_t _2, size_t _3, FILE *_4);
__cdecl size_t fwrite (const void* _1, size_t _2, size_t _3, FILE *_4);
__cdecl int    fseek (FILE *_1, long _2, int _3);
__cdecl long   ftell (FILE *_1);
__cdecl void   rewind (FILE *_1);

#endif
