int main() {
    int x = 10;
    x = x + 5 @ 2;      // invalid token: @
    int $var = 3;       // invalid token: $
    x = x ^ 1;          // invalid token: ^ , use pow() for exp
    return x;
}
