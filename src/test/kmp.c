#include <stdio.h>

#define MAXN 100005

char s[MAXN], t[MAXN];
int f[MAXN];

int main() {
    printf("Input text: ");
    scanf("%s", s);
    printf("Input pattern: ");
    scanf("%s", t);
    f[0] = -1;
    int i = 0, j = -1;
    while (t[i]) {
        while (~j && t[i] != t[j])
            j = f[j];
        f[++i] = ++j;
    }
    i = 0, j = 0;
    while (s[i]) {
        while (~j && s[i] != t[j])
            j = f[j];
        ++i;
        if (!t[++j]) {
            printf("matched at %d\n", i - j);
        }
    }
}
