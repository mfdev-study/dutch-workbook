#include <stdio.h>
#include <stdlib.h>

int binarySearch(int arr[], int size, int target) {
    int left = 0, right = size - 1;

    while (left <= right) {
        int mid = left + (right - left) / 2;

        if (arr[mid] == target)
            return mid;
        else if (arr[mid] < target)
            left = mid + 1;
        else
            right = mid - 1;
    }

    return -1;
}

int main() {
    int size;
    int *arr = NULL;
    int target;

    printf("Enter array size: ");
    if (scanf("%d", &size) != 1 || size <= 0) {
        printf("Error: Invalid array size. Must be a positive integer.\n");
        return 1;
    }

    arr = (int *)malloc(size * sizeof(int));
    if (arr == NULL) {
        printf("Error: Memory allocation failed.\n");
        return 1;
    }

    printf("Enter %d integers (sorted for binary search):\n", size);
    for (int i = 0; i < size; i++) {
        if (scanf("%d", &arr[i]) != 1) {
            printf("Error: Invalid input for element %d.\n", i);
            free(arr);
            return 1;
        }
    }

    printf("Enter target value to search: ");
    if (scanf("%d", &target) != 1) {
        printf("Error: Invalid target value.\n");
        free(arr);
        return 1;
    }

    int result = binarySearch(arr, size, target);

    if (result != -1)
        printf("Element found at index %d\n", result);
    else
        printf("Element not found\n");

    free(arr);
    return 0;
}
