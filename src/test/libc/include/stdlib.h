#ifndef _STDLIB_H_
#define _STDLIB_H_

__cdecl int atoi (const char *);
__cdecl long atol (const char *);

__cdecl double strtod (const char *, char **);
__cdecl double atof (const char *);

__cdecl int rand ();
__cdecl void srand (int);

__cdecl void abort ();
__cdecl void exit (int);

__cdecl int system (const char *);
__cdecl char *getenv (const char *);

__cdecl void *calloc (size_t, size_t);
__cdecl void *malloc (size_t);
__cdecl void *realloc (void *, size_t);
__cdecl void free (void *);

#endif