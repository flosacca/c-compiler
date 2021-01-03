#ifndef _TIME_H_
#define _TIME_H_

#include <stddef.h>

#define CLOCKS_PER_SEC	((clock_t)(1000))

typedef long clock_t;

struct tm
{ /* A structure for storing the attributes of a broken-down time; (once
   * again, it isn't defined elsewhere, so no guard is necessary).  Note
   * that we are within the scope of <time.h> itself, so we must provide
   * the complete structure declaration here.
   */
  int  tm_sec;  	/* Seconds: 0-60 (to accommodate leap seconds) */
  int  tm_min;  	/* Minutes: 0-59 */
  int  tm_hour; 	/* Hours since midnight: 0-23 */
  int  tm_mday; 	/* Day of the month: 1-31 */
  int  tm_mon;  	/* Months *since* January: 0-11 */
  int  tm_year; 	/* Years since 1900 */
  int  tm_wday; 	/* Days since Sunday (0-6) */
  int  tm_yday; 	/* Days since Jan. 1: 0-365 */
  int  tm_isdst;	/* +1=Daylight Savings Time, 0=No DST, -1=unknown */
};

__cdecl clock_t  clock ();

__cdecl time_t time (time_t * _1);
__cdecl double difftime (time_t _1, time_t _2);
__cdecl time_t mktime (struct tm *_1);

__cdecl char *asctime (const struct tm *_1);

__cdecl char *ctime (const time_t *_1);
__cdecl struct tm *gmtime (const time_t *_1);
__cdecl struct tm *localtime (const time_t *_1);

__cdecl size_t strftime (char *_1, size_t _2, const char *_3, const struct tm * _4);

__cdecl char *_strdate (char *_1);
__cdecl char *_strtime (char *_1);

#endif