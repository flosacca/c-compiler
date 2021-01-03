#include <stdio.h>
#include "helloworld.h"

int main() {
    printHello();
    for (int i = 0; i < 10; i++) {
        printf("%d\n", i);
        for (int i = 0; i < 2; ++i) {
            printf("lala: %d\n", Suck);
        }
    }
    return 0;
}

void printHello() {
    printf("Hello World!\n");
}