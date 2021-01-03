#ifndef _STDLIB_H_
#define _STDLIB_H_

#define RAND_MAX 32767

__cdecl int atoi (const char *_1);
__cdecl long atol (const char *_1);

__cdecl double strtod (const char *_1, char ** _2);
__cdecl double atof (const char *_1);

__cdecl int rand ();
__cdecl void srand (int _1);

__cdecl void abort ();
__cdecl void exit (int _1);

__cdecl int system (const char *_1);
__cdecl char *getenv (const char *_1);

__cdecl void *calloc (size_t _1, size_t _2);
__cdecl void *malloc (size_t _1);
__cdecl void *realloc (void *_1, size_t _2);
__cdecl void free (void *_1);

#endif