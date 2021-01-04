#ifndef _WINBASE_H_
#define _WINBASE_H_

#define SP_SERIALCOMM                                                  1

#define PST_UNSPECIFIED                                                0
#define PST_RS232                                                      1
#define PST_PARALLELPORT                                               2
#define PST_RS422                                                      3
#define PST_RS423                                                      4
#define PST_RS449                                                      5
#define PST_MODEM                                                      6
#define PST_FAX                                                     0x21
#define PST_SCANNER                                                 0x22
#define PST_NETWORK_BRIDGE                                         0x100
#define PST_LAT                                                    0x101
#define PST_TCPIP_TELNET                                           0x102
#define PST_X25                                                    0x103

#define BAUD_075                                                       1
#define BAUD_110                                                       2
#define BAUD_134_5                                                     4
#define BAUD_150                                                       8
#define BAUD_300                                                      16
#define BAUD_600                                                      32
#define BAUD_1200                                                     64
#define BAUD_1800                                                    128
#define BAUD_2400                                                    256
#define BAUD_4800                                                    512
#define BAUD_7200                                                   1024
#define BAUD_9600                                                   2048
#define BAUD_14400                                                  4096
#define BAUD_19200                                                  8192
#define BAUD_38400                                                 16384
#define BAUD_56K                                                   32768
#define BAUD_128K                                                  65536
#define BAUD_115200                                               131072
#define BAUD_57600                                                262144
#define BAUD_USER                                             0x10000000

#define PCF_DTRDSR                                                     1
#define PCF_RTSCTS                                                     2
#define PCF_RLSD                                                       4
#define PCF_PARITY_CHECK                                               8
#define PCF_XONXOFF                                                   16
#define PCF_SETXCHAR                                                  32
#define PCF_TOTALTIMEOUTS                                             64
#define PCF_INTTIMEOUTS                                              128
#define PCF_SPECIALCHARS                                             256
#define PCF_16BITMODE                                                512

#define SP_PARITY                                                      1
#define SP_BAUD                                                        2
#define SP_DATABITS                                                    4
#define SP_STOPBITS                                                    8
#define SP_HANDSHAKING                                                16
#define SP_PARITY_CHECK                                               32
#define SP_RLSD                                                       64

#define DATABITS_5                                                     1
#define DATABITS_6                                                     2
#define DATABITS_7                                                     4
#define DATABITS_8                                                     8
#define DATABITS_16                                                   16
#define DATABITS_16X                                                  32

#define STOPBITS_10                                                    1
#define STOPBITS_15                                                    2
#define STOPBITS_20                                                    4

#define PARITY_NONE                                                  256
#define PARITY_ODD                                                   512
#define PARITY_EVEN                                                 1024
#define PARITY_MARK                                                 2048
#define PARITY_SPACE                                                4096

#define EXCEPTION_DEBUG_EVENT                                          1
#define CREATE_THREAD_DEBUG_EVENT                                      2
#define CREATE_PROCESS_DEBUG_EVENT                                     3
#define EXIT_THREAD_DEBUG_EVENT                                        4
#define EXIT_PROCESS_DEBUG_EVENT                                       5
#define LOAD_DLL_DEBUG_EVENT                                           6
#define UNLOAD_DLL_DEBUG_EVENT                                         7
#define OUTPUT_DEBUG_STRING_EVENT                                      8
#define RIP_EVENT                                                      9

#define HFILE_ERROR                                          ((HFILE)(-1))

#define FILE_BEGIN                                                     0
#define FILE_CURRENT                                                   1
#define FILE_END                                                       2

#define INVALID_SET_FILE_POINTER                             ((DWORD)(-1))

#define OF_READ                                                        0
#define OF_READWRITE                                                   2
#define OF_WRITE                                                       1
#define OF_SHARE_COMPAT                                                0
#define OF_SHARE_DENY_NONE                                            64
#define OF_SHARE_DENY_READ                                            48
#define OF_SHARE_DENY_WRITE                                           32
#define OF_SHARE_EXCLUSIVE                                            16
#define OF_CANCEL                                                   2048
#define OF_CREATE                                                   4096
#define OF_DELETE                                                    512
#define OF_EXIST                                                   16384
#define OF_PARSE                                                     256
#define OF_PROMPT                                                   8192
#define OF_REOPEN                                                  32768
#define OF_VERIFY                                                   1024

#define NMPWAIT_NOWAIT                                                 1
#define NMPWAIT_WAIT_FOREVER                                 ((DWORD)(-1))
#define NMPWAIT_USE_DEFAULT_WAIT                                       0

#define CE_BREAK                                                      16
#define CE_DNS                                                      2048
#define CE_FRAME                                                       8
#define CE_IOE                                                      1024
#define CE_MODE                                                    32768
#define CE_OOP                                                      4096
#define CE_OVERRUN                                                     2
#define CE_PTO                                                       512
#define CE_RXOVER                                                      1
#define CE_RXPARITY                                                    4
#define CE_TXFULL                                                    256

#define PROGRESS_CONTINUE                                              0
#define PROGRESS_CANCEL                                                1
#define PROGRESS_STOP                                                  2
#define PROGRESS_QUIET                                                 3

#define CALLBACK_CHUNK_FINISHED                                        0
#define CALLBACK_STREAM_SWITCH                                         1

#define COPY_FILE_FAIL_IF_EXISTS                                  0x0001
#define COPY_FILE_RESTARTABLE                                     0x0002
#define COPY_FILE_OPEN_SOURCE_FOR_WRITE                           0x0004

#define OFS_MAXPATHNAME                                              128

#define FILE_MAP_ALL_ACCESS                                      0xF001F
#define FILE_MAP_READ                                                  4
#define FILE_MAP_WRITE                                                 2
#define FILE_MAP_COPY                                                  1

#define MUTEX_ALL_ACCESS                                        0x1F0001
#define MUTEX_MODIFY_STATE                                             1

#define SEMAPHORE_ALL_ACCESS                                    0x1F0003
#define SEMAPHORE_MODIFY_STATE                                         2

#define EVENT_ALL_ACCESS                                        0x1F0003
#define EVENT_MODIFY_STATE                                             2

#define PIPE_ACCESS_DUPLEX                                             3
#define PIPE_ACCESS_INBOUND                                            1
#define PIPE_ACCESS_OUTBOUND                                           2
#define PIPE_TYPE_BYTE                                                 0
#define PIPE_TYPE_MESSAGE                                              4
#define PIPE_READMODE_BYTE                                             0
#define PIPE_READMODE_MESSAGE                                          2
#define PIPE_WAIT                                                      0
#define PIPE_NOWAIT                                                    1
#define PIPE_CLIENT_END                                                0
#define PIPE_SERVER_END                                                1
#define PIPE_UNLIMITED_INSTANCES                                     255

#define DEBUG_PROCESS                                         0x00000001
#define DEBUG_ONLY_THIS_PROCESS                               0x00000002
#define CREATE_SUSPENDED                                      0x00000004
#define DETACHED_PROCESS                                      0x00000008
#define CREATE_NEW_CONSOLE                                    0x00000010
#define NORMAL_PRIORITY_CLASS                                 0x00000020
#define IDLE_PRIORITY_CLASS                                   0x00000040
#define HIGH_PRIORITY_CLASS                                   0x00000080
#define REALTIME_PRIORITY_CLASS                               0x00000100
#define CREATE_NEW_PROCESS_GROUP                              0x00000200
#define CREATE_UNICODE_ENVIRONMENT                            0x00000400
#define CREATE_SEPARATE_WOW_VDM                               0x00000800
#define CREATE_SHARED_WOW_VDM                                 0x00001000
#define CREATE_FORCEDOS                                       0x00002000
#define BELOW_NORMAL_PRIORITY_CLASS                           0x00004000
#define ABOVE_NORMAL_PRIORITY_CLASS                           0x00008000
#define STACK_SIZE_PARAM_IS_A_RESERVATION                     0x00010000
#define CREATE_BREAKAWAY_FROM_JOB                             0x01000000
#define CREATE_WITH_USERPROFILE                               0x02000000
#define CREATE_DEFAULT_ERROR_MODE                             0x04000000
#define CREATE_NO_WINDOW                                      0x08000000

#define PROFILE_USER                                          0x10000000
#define PROFILE_KERNEL                                        0x20000000
#define PROFILE_SERVER                                        0x40000000

#define CONSOLE_TEXTMODE_BUFFER                                        1

#define CREATE_NEW                                                     1
#define CREATE_ALWAYS                                                  2
#define OPEN_EXISTING                                                  3
#define OPEN_ALWAYS                                                    4
#define TRUNCATE_EXISTING                                              5

#define FILE_FLAG_WRITE_THROUGH                               0x80000000
#define FILE_FLAG_OVERLAPPED                                  1073741824
#define FILE_FLAG_NO_BUFFERING                                 536870912
#define FILE_FLAG_RANDOM_ACCESS                                268435456
#define FILE_FLAG_SEQUENTIAL_SCAN                              134217728
#define FILE_FLAG_DELETE_ON_CLOSE                               67108864
#define FILE_FLAG_BACKUP_SEMANTICS                              33554432
#define FILE_FLAG_POSIX_SEMANTICS                               16777216
#define FILE_FLAG_OPEN_REPARSE_POINT                             2097152
#define FILE_FLAG_OPEN_NO_RECALL                                 1048576

#define SYMBOLIC_LINK_FLAG_DIRECTORY                                 0x1

#define CLRDTR                                                         6
#define CLRRTS                                                         4
#define SETDTR                                                         5
#define SETRTS                                                         3
#define SETXOFF                                                        1
#define SETXON                                                         2
#define SETBREAK                                                       8
#define CLRBREAK                                                       9

#define STILL_ACTIVE                                               0x103

#define FIND_FIRST_EX_CASE_SENSITIVE                                   1

#define SCS_32BIT_BINARY                                               0
#define SCS_64BIT_BINARY                                               6
#define SCS_DOS_BINARY                                                 1
#define SCS_OS216_BINARY                                               5
#define SCS_PIF_BINARY                                                 3
#define SCS_POSIX_BINARY                                               4
#define SCS_WOW_BINARY                                                 2

#define MAX_COMPUTERNAME_LENGTH                                       15

#define HW_PROFILE_GUIDLEN                                            39
#define MAX_PROFILE_LEN                                               80

#define DOCKINFO_UNDOCKED                                              1
#define DOCKINFO_DOCKED                                                2
#define DOCKINFO_USER_SUPPLIED                                         4
#define DOCKINFO_USER_UNDOCKED        (DOCKINFO_USER_SUPPLIED|DOCKINFO_UNDOCKED)
#define DOCKINFO_USER_DOCKED           (DOCKINFO_USER_SUPPLIED|DOCKINFO_DOCKED)

#define DRIVE_REMOVABLE                                                2
#define DRIVE_FIXED                                                    3
#define DRIVE_REMOTE                                                   4
#define DRIVE_CDROM                                                    5
#define DRIVE_RAMDISK                                                  6
#define DRIVE_UNKNOWN                                                  0
#define DRIVE_NO_ROOT_DIR                                              1

#define FILE_TYPE_UNKNOWN                                              0
#define FILE_TYPE_DISK                                                 1
#define FILE_TYPE_CHAR                                                 2
#define FILE_TYPE_PIPE                                                 3
#define FILE_TYPE_REMOTE                                          0x8000
#define FILE_ENCRYPTABLE                                               0
#define FILE_IS_ENCRYPTED                                              1
#define FILE_READ_ONLY                                                 8
#define FILE_ROOT_DIR                                                  3
#define FILE_SYSTEM_ATTR                                               2
#define FILE_SYSTEM_DIR                                                4
#define FILE_SYSTEM_NOT_SUPPORT                                        6
#define FILE_UNKNOWN                                                   5
#define FILE_USER_DISALLOWED                                           7

/* also in ddk/ntapi.h */
#define HANDLE_FLAG_INHERIT                                         0x01
#define HANDLE_FLAG_PROTECT_FROM_CLOSE                              0x02
/* end ntapi.h */

#define STD_INPUT_HANDLE                              (DWORD)(0xfffffff6)
#define STD_OUTPUT_HANDLE                             (DWORD)(0xfffffff5)
#define STD_ERROR_HANDLE                              (DWORD)(0xfffffff4)

#define INVALID_HANDLE_VALUE                                 (HANDLE)(-1)

#define GET_TAPE_MEDIA_INFORMATION                                     0
#define GET_TAPE_DRIVE_INFORMATION                                     1
#define SET_TAPE_MEDIA_INFORMATION                                     0
#define SET_TAPE_DRIVE_INFORMATION                                     1

#define THREAD_PRIORITY_ABOVE_NORMAL                                   1
#define THREAD_PRIORITY_BELOW_NORMAL                                 (-1)
#define THREAD_PRIORITY_HIGHEST                                        2
#define THREAD_PRIORITY_IDLE                                        (-15)
#define THREAD_PRIORITY_LOWEST                                       (-2)
#define THREAD_PRIORITY_NORMAL                                         0
#define THREAD_PRIORITY_TIME_CRITICAL                                 15
#define THREAD_PRIORITY_ERROR_RETURN                          2147483647

#define TIME_ZONE_ID_UNKNOWN                                           0
#define TIME_ZONE_ID_STANDARD                                          1
#define TIME_ZONE_ID_DAYLIGHT                                          2
#define TIME_ZONE_ID_INVALID                                  0xFFFFFFFF

#define FS_CASE_IS_PRESERVED                                           2
#define FS_CASE_SENSITIVE                                              1
#define FS_UNICODE_STORED_ON_DISK                                      4
#define FS_PERSISTENT_ACLS                                             8
#define FS_FILE_COMPRESSION                                           16
#define FS_VOL_IS_COMPRESSED                                       32768

#define GMEM_FIXED                                                     0
#define GMEM_MOVEABLE                                                  2
#define GMEM_MODIFY                                                  128
#define GPTR                                                          64
#define GHND                                                          66
#define GMEM_DDESHARE                                               8192
#define GMEM_DISCARDABLE                                             256
#define GMEM_LOWER                                                  4096
#define GMEM_NOCOMPACT                                                16
#define GMEM_NODISCARD                                                32
#define GMEM_NOT_BANKED                                             4096
#define GMEM_NOTIFY                                                16384
#define GMEM_SHARE                                                  8192
#define GMEM_ZEROINIT                                                 64
#define GMEM_DISCARDED                                             16384
#define GMEM_INVALID_HANDLE                                        32768
#define GMEM_LOCKCOUNT                                               255
#define GMEM_VALID_FLAGS                                           32626

#define STATUS_WAIT_0                                                  0
#define STATUS_ABANDONED_WAIT_0                                     0x80
#define STATUS_USER_APC                                             0xC0
#define STATUS_TIMEOUT                                             0x102
#define STATUS_PENDING                                             0x103
#define STATUS_SEGMENT_NOTIFICATION                           0x40000005
#define STATUS_GUARD_PAGE_VIOLATION                           0x80000001
#define STATUS_DATATYPE_MISALIGNMENT                          0x80000002
#define STATUS_BREAKPOINT                                     0x80000003
#define STATUS_SINGLE_STEP                                    0x80000004
#define STATUS_ACCESS_VIOLATION                               0xC0000005
#define STATUS_IN_PAGE_ERROR                                  0xC0000006
#define STATUS_INVALID_HANDLE                                 0xC0000008L
#define STATUS_NO_MEMORY                                      0xC0000017
#define STATUS_ILLEGAL_INSTRUCTION                            0xC000001D
#define STATUS_NONCONTINUABLE_EXCEPTION                       0xC0000025
#define STATUS_INVALID_DISPOSITION                            0xC0000026
#define STATUS_ARRAY_BOUNDS_EXCEEDED                          0xC000008C
#define STATUS_FLOAT_DENORMAL_OPERAND                         0xC000008D
#define STATUS_FLOAT_DIVIDE_BY_ZERO                           0xC000008E
#define STATUS_FLOAT_INEXACT_RESULT                           0xC000008F
#define STATUS_FLOAT_INVALID_OPERATION                        0xC0000090
#define STATUS_FLOAT_OVERFLOW                                 0xC0000091
#define STATUS_FLOAT_STACK_CHECK                              0xC0000092
#define STATUS_FLOAT_UNDERFLOW                                0xC0000093
#define STATUS_INTEGER_DIVIDE_BY_ZERO                         0xC0000094
#define STATUS_INTEGER_OVERFLOW                               0xC0000095
#define STATUS_PRIVILEGED_INSTRUCTION                         0xC0000096
#define STATUS_STACK_OVERFLOW                                 0xC00000FD
#define STATUS_CONTROL_C_EXIT                                 0xC000013A
#define STATUS_DLL_INIT_FAILED                                0xC0000142
#define STATUS_DLL_INIT_FAILED_LOGOFF                         0xC000026B

#define EXCEPTION_ACCESS_VIOLATION                     STATUS_ACCESS_VIOLATION
#define EXCEPTION_DATATYPE_MISALIGNMENT              STATUS_DATATYPE_MISALIGNMENT
#define EXCEPTION_BREAKPOINT                              STATUS_BREAKPOINT
#define EXCEPTION_SINGLE_STEP                             STATUS_SINGLE_STEP
#define EXCEPTION_ARRAY_BOUNDS_EXCEEDED              STATUS_ARRAY_BOUNDS_EXCEEDED
#define EXCEPTION_FLT_DENORMAL_OPERAND              STATUS_FLOAT_DENORMAL_OPERAND
#define EXCEPTION_FLT_DIVIDE_BY_ZERO                 STATUS_FLOAT_DIVIDE_BY_ZERO
#define EXCEPTION_FLT_INEXACT_RESULT                 STATUS_FLOAT_INEXACT_RESULT
#define EXCEPTION_FLT_INVALID_OPERATION             STATUS_FLOAT_INVALID_OPERATION
#define EXCEPTION_FLT_OVERFLOW                          STATUS_FLOAT_OVERFLOW
#define EXCEPTION_FLT_STACK_CHECK                      STATUS_FLOAT_STACK_CHECK
#define EXCEPTION_FLT_UNDERFLOW                         STATUS_FLOAT_UNDERFLOW
#define EXCEPTION_INT_DIVIDE_BY_ZERO                 STATUS_INTEGER_DIVIDE_BY_ZERO
#define EXCEPTION_INT_OVERFLOW                          STATUS_INTEGER_OVERFLOW
#define EXCEPTION_PRIV_INSTRUCTION                   STATUS_PRIVILEGED_INSTRUCTION
#define EXCEPTION_IN_PAGE_ERROR                          STATUS_IN_PAGE_ERROR
#define EXCEPTION_ILLEGAL_INSTRUCTION                 STATUS_ILLEGAL_INSTRUCTION
#define EXCEPTION_NONCONTINUABLE_EXCEPTION          STATUS_NONCONTINUABLE_EXCEPTION
#define EXCEPTION_STACK_OVERFLOW                         STATUS_STACK_OVERFLOW
#define EXCEPTION_INVALID_DISPOSITION                 STATUS_INVALID_DISPOSITION
#define EXCEPTION_GUARD_PAGE                          STATUS_GUARD_PAGE_VIOLATION
#define EXCEPTION_INVALID_HANDLE                        STATUS_INVALID_HANDLE
#define CONTROL_C_EXIT                                  STATUS_CONTROL_C_EXIT

#define PROCESS_HEAP_REGION                                            1
#define PROCESS_HEAP_UNCOMMITTED_RANGE                                 2
#define PROCESS_HEAP_ENTRY_BUSY                                        4
#define PROCESS_HEAP_ENTRY_MOVEABLE                                   16
#define PROCESS_HEAP_ENTRY_DDESHARE                                   32

#define DONT_RESOLVE_DLL_REFERENCES                                    1
#define LOAD_LIBRARY_AS_DATAFILE                                       2
#define LOAD_WITH_ALTERED_SEARCH_PATH                                  8

#define LMEM_FIXED                                                     0
#define LMEM_MOVEABLE                                                  2
#define LMEM_NONZEROLHND                                               2
#define LMEM_NONZEROLPTR                                               0
#define LMEM_DISCARDABLE                                            3840
#define LMEM_NOCOMPACT                                                16
#define LMEM_NODISCARD                                                32
#define LMEM_ZEROINIT                                                 64
#define LMEM_DISCARDED                                             16384
#define LMEM_MODIFY                                                  128
#define LMEM_INVALID_HANDLE                                        32768
#define LMEM_LOCKCOUNT                                               255

#define LPTR                                                          64
#define LHND                                                          66
#define NONZEROLHND                                                    2
#define NONZEROLPTR                                                    0

#define LOCKFILE_FAIL_IMMEDIATELY                                      1
#define LOCKFILE_EXCLUSIVE_LOCK                                        2

#define LOGON32_PROVIDER_DEFAULT                                       0
#define LOGON32_PROVIDER_WINNT35                                       1
#define LOGON32_LOGON_INTERACTIVE                                      2
#define LOGON32_LOGON_NETWORK                                          3
#define LOGON32_LOGON_BATCH                                            4
#define LOGON32_LOGON_SERVICE                                          5
#define LOGON32_LOGON_UNLOCK                                           7

#define MOVEFILE_REPLACE_EXISTING                                      1
#define MOVEFILE_COPY_ALLOWED                                          2
#define MOVEFILE_DELAY_UNTIL_REBOOT                                    4
#define MOVEFILE_WRITE_THROUGH                                         8

#define MAXIMUM_WAIT_OBJECTS                                          64
#define MAXIMUM_SUSPEND_COUNT                                       0x7F

#define WAIT_OBJECT_0                                                  0
#define WAIT_ABANDONED_0                                             128

/* WAIT_TIMEOUT is also defined in <winerror.h>.  We MUST ensure that the
 * definitions are IDENTICALLY the same in BOTH headers; they are defined
 * without guards, to give the compiler an opportunity to check this.
 */
#define WAIT_TIMEOUT                                                 258L

#define WAIT_IO_COMPLETION                                          0xC0
#define WAIT_ABANDONED                                               128
#define WAIT_FAILED                                  ((DWORD)(0xFFFFFFFF))

#define PURGE_TXABORT                                                  1
#define PURGE_RXABORT                                                  2
#define PURGE_TXCLEAR                                                  4
#define PURGE_RXCLEAR                                                  8

#define EVENTLOG_SUCCESS                                               0
#define EVENTLOG_FORWARDS_READ                                         4
#define EVENTLOG_BACKWARDS_READ                                        8
#define EVENTLOG_SEEK_READ                                             2
#define EVENTLOG_SEQUENTIAL_READ                                       1
#define EVENTLOG_ERROR_TYPE                                            1
#define EVENTLOG_WARNING_TYPE                                          2
#define EVENTLOG_INFORMATION_TYPE                                      4
#define EVENTLOG_AUDIT_SUCCESS                                         8
#define EVENTLOG_AUDIT_FAILURE                                        16

#define FORMAT_MESSAGE_ALLOCATE_BUFFER                               256
#define FORMAT_MESSAGE_IGNORE_INSERTS                                512
#define FORMAT_MESSAGE_FROM_STRING                                  1024
#define FORMAT_MESSAGE_FROM_HMODULE                                 2048
#define FORMAT_MESSAGE_FROM_SYSTEM                                  4096
#define FORMAT_MESSAGE_ARGUMENT_ARRAY                               8192
#define FORMAT_MESSAGE_MAX_WIDTH_MASK                                255

#define EV_BREAK                                                      64
#define EV_CTS                                                         8
#define EV_DSR                                                        16
#define EV_ERR                                                       128
#define EV_EVENT1                                                   2048
#define EV_EVENT2                                                   4096
#define EV_PERR                                                      512
#define EV_RING                                                      256
#define EV_RLSD                                                       32
#define EV_RX80FULL                                                 1024
#define EV_RXCHAR                                                      1
#define EV_RXFLAG                                                      2
#define EV_TXEMPTY                                                     4

/* also in ddk/ntapi.h */
/* To restore default error mode, call SetErrorMode (0).  */
#define SEM_FAILCRITICALERRORS                                    0x0001
#define SEM_NOGPFAULTERRORBOX                                     0x0002
#define SEM_NOALIGNMENTFAULTEXCEPT                                0x0004
#define SEM_NOOPENFILEERRORBOX                                    0x8000
/* end ntapi.h */

#define SLE_ERROR                                                      1
#define SLE_MINORERROR                                                 2
#define SLE_WARNING                                                    3

#define SHUTDOWN_NORETRY                                               1

#define EXCEPTION_EXECUTE_HANDLER                                      1
#define EXCEPTION_CONTINUE_EXECUTION                                 (-1)
#define EXCEPTION_CONTINUE_SEARCH                                      0

#define MAXINTATOM                                                0xC000
#define INVALID_ATOM                                           ((ATOM)(0))

#define IGNORE                                                         0
#define INFINITE                                              0xFFFFFFFF
#define NOPARITY                                                       0
#define ODDPARITY                                                      1
#define EVENPARITY                                                     2
#define MARKPARITY                                                     3
#define SPACEPARITY                                                    4
#define ONESTOPBIT                                                     0
#define ONE5STOPBITS                                                   1
#define TWOSTOPBITS                                                    2
#define CBR_110                                                      110
#define CBR_300                                                      300
#define CBR_600                                                      600
#define CBR_1200                                                    1200
#define CBR_2400                                                    2400
#define CBR_4800                                                    4800
#define CBR_9600                                                    9600
#define CBR_14400                                                  14400
#define CBR_19200                                                  19200
#define CBR_38400                                                  38400
#define CBR_56000                                                  56000
#define CBR_57600                                                  57600
#define CBR_115200                                                115200
#define CBR_128000                                                128000
#define CBR_256000                                                256000

#define BACKUP_INVALID                                                 0
#define BACKUP_DATA                                                    1
#define BACKUP_EA_DATA                                                 2
#define BACKUP_SECURITY_DATA                                           3
#define BACKUP_ALTERNATE_DATA                                          4
#define BACKUP_LINK                                                    5
#define BACKUP_PROPERTY_DATA                                           6
#define BACKUP_OBJECT_ID                                               7
#define BACKUP_REPARSE_DATA                                            8
#define BACKUP_SPARSE_BLOCK                                            9

#define STREAM_NORMAL_ATTRIBUTE                                        0
#define STREAM_MODIFIED_WHEN_READ                                      1
#define STREAM_CONTAINS_SECURITY                                       2
#define STREAM_CONTAINS_PROPERTIES                                     4

#define STARTF_USESHOWWINDOW                                           1
#define STARTF_USESIZE                                                 2
#define STARTF_USEPOSITION                                             4
#define STARTF_USECOUNTCHARS                                           8
#define STARTF_USEFILLATTRIBUTE                                       16
#define STARTF_RUNFULLSCREEN                                          32
#define STARTF_FORCEONFEEDBACK                                        64
#define STARTF_FORCEOFFFEEDBACK                                      128
#define STARTF_USESTDHANDLES                                         256
#define STARTF_USEHOTKEY                                             512

#define TC_NORMAL                                                      0
#define TC_HARDERR                                                     1
#define TC_GP_TRAP                                                     2
#define TC_SIGNAL                                                      3

#define AC_LINE_OFFLINE                                                0
#define AC_LINE_ONLINE                                                 1
#define AC_LINE_BACKUP_POWER                                           2
#define AC_LINE_UNKNOWN                                              255

#define BATTERY_FLAG_HIGH                                              1
#define BATTERY_FLAG_LOW                                               2
#define BATTERY_FLAG_CRITICAL                                          4
#define BATTERY_FLAG_CHARGING                                          8
#define BATTERY_FLAG_NO_BATTERY                                      128
#define BATTERY_FLAG_UNKNOWN                                         255
#define BATTERY_PERCENTAGE_UNKNOWN                                   255
#define BATTERY_LIFE_UNKNOWN                                  0xFFFFFFFF

#define DDD_RAW_TARGET_PATH                                            1
#define DDD_REMOVE_DEFINITION                                          2
#define DDD_EXACT_MATCH_ON_REMOVE                                      4

#define HINSTANCE_ERROR                                               32

#define MS_CTS_ON                                                     16
#define MS_DSR_ON                                                     32
#define MS_RING_ON                                                    64
#define MS_RLSD_ON                                                   128

#define DTR_CONTROL_DISABLE                                            0
#define DTR_CONTROL_ENABLE                                             1
#define DTR_CONTROL_HANDSHAKE                                          2

#define RTS_CONTROL_DISABLE                                            0
#define RTS_CONTROL_ENABLE                                             1
#define RTS_CONTROL_HANDSHAKE                                          2
#define RTS_CONTROL_TOGGLE                                             3

#define SECURITY_ANONYMOUS                            (SecurityAnonymous<<16)
#define SECURITY_IDENTIFICATION                       (SecurityIdentification<<16)
#define SECURITY_IMPERSONATION                        (SecurityImpersonation<<16)
#define SECURITY_DELEGATION                           (SecurityDelegation<<16)
#define SECURITY_CONTEXT_TRACKING                                0x40000
#define SECURITY_EFFECTIVE_ONLY                                  0x80000
#define SECURITY_SQOS_PRESENT                                   0x100000
#define SECURITY_VALID_SQOS_FLAGS                               0x1F0000

#define INVALID_FILE_SIZE                                     0xFFFFFFFF
#define TLS_OUT_OF_INDEXES                            (DWORD)(0xFFFFFFFF)

#define GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS                0x00000004
#define GET_MODULE_HANDLE_EX_FLAG_PIN                         0x00000001
#define GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT          0x00000002

#define WRITE_WATCH_FLAG_RESET                                         1


#endif
