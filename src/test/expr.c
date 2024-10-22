#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

#define MAXN 100005

double calc(char op, double a, double b) {
    if (op == '+') return a + b;
    if (op == '-') return a - b;
    if (op == '*') return a * b;
    if (op == '/') return a / b;
    exit(1);
    return 0;
}

int comp(char c, char n) {
    if (c == '+' || c == '-')
        return n != '*' && n != '/';
    return c == '*' || c == '/';
}

void remove_blank(char* str) {
    char* t = str;
    while (*str) {
        if (!isblank(*str)) {
            *t++ = *str;
        }
        ++str;
    }
    *t = 0;
}

double eval(const char* expr) {
    int len = strlen(expr);
    static double values[MAXN];
    static char symbols[MAXN];
    static char value_str[MAXN];
    int n = 0;
    int m = 0;
    int i = 0;
    while (i < len) {
        while (expr[i] == '(') {
            symbols[++m] = expr[i++];
        }
        int j = 0;
        while (isdigit(expr[i]) || expr[i] == '.') {
            value_str[j++] = expr[i++];
        }
        value_str[j] = 0;
        values[++n] = atof(value_str);
        while (1) {
            while (m > 0 && comp(symbols[m], expr[i])) {
                double b = values[n--];
                double a = values[n--];
                values[++n] = calc(symbols[m--], a, b);
            }
            if (expr[i] != ')') {
                symbols[++m] = expr[i++];
                break;
            }
            if (symbols[m] != '(') {
                exit(1);
            }
            --m, ++i;
        }
    }
    return values[n];
}

int main() {
    static char expr[MAXN];
    fgets(expr, MAXN, stdin);
    remove_blank(expr);
    printf("%f\n", eval(expr));
}
