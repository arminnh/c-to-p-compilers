
int f(int (*arr[][2])[][3]) {
	return 0;
}

int main() {
	int (*i[2][2])[][5];
	int j;
	// char c = 5.5;
	// i + j;
	// j < c;

	int (*arr[4][2])[][3];
	int (* const(* const arr2)[4][2])[][3] = &arr;
	// int (*arr[2])[3];
	int k = arr2;
	f(arr);

}