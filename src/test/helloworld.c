#include <stdio.h>
#include "helloworld.h"

int main() {
    printHello();
    int a = 1;
    char b = 2;
    a -= b;
    return 0;
}

void printHello() {
    printf("Hello World!\n");
}