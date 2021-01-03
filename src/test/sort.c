#include <stdio.h>

#define N 100005

void swap(int* a, int* b) {
    int v = *a;
    *a = *b;
    *b = v;
}

void quick_sort(int* a, int n) {
    if (n <= 1)
        return;
    int v = a[0];
    int i = -1;
    int j = n;
    for (;;) {
        for (;;)
            if (a[++i] >= v) break;
        for (;;)
            if (a[--j] <= v) break;
        if (i >= j)
            break;
        swap(&a[i], &a[j]);
    }
    int m = j + 1;
    quick_sort(a, m);
    quick_sort(&a[m], n - m);
}

int a[N];

int main() {
    int n = 0;
    while (~scanf("%d", a + n))
        ++n;
    quick_sort(a, n);
    for (int i = 0; i < n; ++i)
        printf("%d%s", a[i], i < n - 1 ? " ": "\n");
}
