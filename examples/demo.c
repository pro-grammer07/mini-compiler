int sum(int n) {
    int i;
    int s;
    s = 0;
    for (i = 0; i < n; i = i + 1) {
        s = s + i;
    }
    return s;
}

int main() {
    int a[5];
    int i;
    int total;
    i = 0;
    while (i < 5) {
        a[i] = i * 2;
        i = i + 1;
    }
    total = sum(5);
    if (total > 5 && a[2] == 4) {
        total = total + 10;
    } else {
        total = total - 10;
    }
    return total;
}
