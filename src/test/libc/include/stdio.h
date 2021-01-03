#ifndef _STDIO_H_
#define _STDIO_H_

#include <stddef.h>

#define STDIN_FILENO	0
#define STDOUT_FILENO	1
#define STDERR_FILENO	2

typedef struct _iobuf
{
  char	*_ptr;
  int	 _cnt;
  char	*_base;
  int	 _flag;
  int	 _file;
  int	 _charbuf;
  int	 _bufsiz;
  char	*_tmpfname;
} FILE;

FILE _iob[];	/* An array of FILE imported from DLL. */

__cdecl FILE * fopen (const char *, const char *);
__cdecl FILE * freopen (const char *, const char *, FILE *);
__cdecl int    fflush (FILE *);
__cdecl int    fclose (FILE *);
__cdecl int    remove (const char *);
__cdecl int    rename (const char *, const char *);
__cdecl FILE * tmpfile ();
__cdecl char * tmpnam (char *);

__cdecl int    fprintf (FILE *, const char *, ...);
__cdecl int    printf (const char *, ...);
__cdecl int    sprintf (char *, const char *, ...);
__cdecl int    fscanf (FILE *, const char *, ...);
__cdecl int    scanf (const char *, ...);
__cdecl int    sscanf (const char *, const char *, ...);

__cdecl int    fgetc (FILE *);
__cdecl char * fgets (char *, int, FILE *);
__cdecl int    fputc (int, FILE *);
__cdecl int    fputs (const char *, FILE *);
__cdecl char * gets (char *);
__cdecl int    puts (const char *);
__cdecl int    ungetc (int, FILE *);
__cdecl int    getchar();
__cdecl int    putchar(int);

__cdecl size_t fread (void *, size_t, size_t, FILE *);
__cdecl size_t fwrite (const void *, size_t, size_t, FILE *);
__cdecl int    fseek (FILE *, long, int);
__cdecl long   ftell (FILE *);
__cdecl void   rewind (FILE *);

#endif
