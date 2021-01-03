#include <stdio.h>
#include <string.h>

int check(const char* s) {
    int n = strlen(s);
    for (int i = n / 2; ~i; --i)
        if (s[i] != s[n - i - 1]) {
            printf("mismatch at %d\n", i);
            return 0;
        }
    return 1;
}

int main() {
    const char* s = "ababa";
    if (check(s))
        puts("yes");
    else
        puts("no");
    return 0;
}
