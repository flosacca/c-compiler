#include <stdio.h>
#include <string.h>

int check(const char* s) {
    int n = strlen(s);
    for (int i = 0; i < n / 2; ++i) {
        if (s[i] != s[n - i - 1])
            return i;
    }
    return -1;
}

int main() {
    static char s[100005];
    scanf("%s", s);
    int i = check(s);
    if (~i)
        printf("failed at %d\n", i);
    else
        puts("ok");
}
