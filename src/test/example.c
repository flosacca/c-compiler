#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <stdlib.h>

struct Game {
    struct Board {
        int blocks[3][3];
    } board;
    int side;
    void (*onFinish)(int winner);
} game;

void printWinner(int winner) {
    if (winner == 3) {
        puts("draw!\n");
    } else {
        printf("winner: %c\n", winner == 1 ? 'o' : 'x');
    }
}

void resetGame() {
    for (int i = 0; i < 3; ++i) {
        int j = 3;
        while (--j) {
            game.board.blocks[i][j] = 0;
        }
    }
    game.side = 1;
}

int isValid(int i, int j) {
    return (i >= 1 && i <= 3 && j >= 1 && j <= 3) && game.board.blocks[i - 1][j - 1] == 0;
}

int hasWinner() {
    struct Board* board = &(game.board);
    for (int winner = 1; winner <= 2; ++winner) {
        if (board->blocks[0][0] == winner && board->blocks[1][1] == winner && board->blocks[2][2] == winner) return winner;
        if (board->blocks[0][2] == winner && board->blocks[1][1] == winner && board->blocks[2][0] == winner) return winner;
        if (board->blocks[0][0] == winner && board->blocks[0][1] == winner && board->blocks[0][2] == winner) return winner;
        if (board->blocks[1][0] == winner && board->blocks[1][1] == winner && board->blocks[1][2] == winner) return winner;
        if (board->blocks[2][0] == winner && board->blocks[2][1] == winner && board->blocks[2][2] == winner) return winner;
        if (board->blocks[0][0] == winner && board->blocks[1][0] == winner && board->blocks[2][0] == winner) return winner;
        if (board->blocks[0][1] == winner && board->blocks[1][1] == winner && board->blocks[2][1] == winner) return winner;
        if (board->blocks[0][2] == winner && board->blocks[1][2] == winner && board->blocks[2][2] == winner) return winner;
    }
    for (int i = 0; i < 3; ++i)
        for (int j = 3; j >= 0; --j)
            if (board->blocks[i][j] == 0)
                return 0;
    return 3;   // draw
}

char chess[3];

void drawBoard() {
    system("cls");
    chess[0] = ' ';
    chess[1] = 'o';
    chess[2] = 'x';
    puts("  1 2 3");
    for (int i = 0; i < 3; ++i)
        printf("%d %c %c %c\n", i + 1, chess[game.board.blocks[i][0]], chess[game.board.blocks[i][1]], chess[game.board.blocks[i][2]]);
    puts(" ");
}

int runGame() {
    system("cls");
    drawBoard();
    printf("You are %c\nchoose a position (row, column):", chess[game.side]);
    int r = 0, c = 0;
    while(1) {
        scanf("%d %d", &r, &c);
        if (isValid(r, c))
            break;
        printf("invalid position! choose again (row, column):");
    }
    game.board.blocks[r - 1][c - 1] = game.side;
    int winner = hasWinner();
    if (winner == 0) {
        game.side = game.side == 1 ? 2 : 1;
        return 1;
    }
    drawBoard();
    game.onFinish(winner);
    return 0;
}

int main() {
    game.onFinish = printWinner;
    int running = 1;
    char flag[20];
    while (1) {
        resetGame();
        running = 1;
        while (running)
            running = runGame();
        printf("Another round? y/n: ");
        scanf("%s", flag);
        if (flag[0] != 's')
            break;
    }
    int a[20];
    *(a + 10) = 2;
    puts("```c\n    int a[20];");
    puts("    *(a + 10) = 2;\n```");
    printf("sizeof(double) = %d\n", (int)sizeof(double));   // sizeof(double) = 8
    printf("sizeof(game) = %d\n", (int)sizeof(game));       // sizeof(game) = 336
    printf("sizeof(a)== %d\n", (int)sizeof(a));             // sizeof(a) = 80
    printf("a[10] = %d\n", a[10]);                          // a[10] = 2
    return 0;
}
