Model: ai21/jamba-large-1.7
```markdown
# How to Compile and Run C Code on Linux

This guide will walk you through the steps to compile and run a C program on a Linux system.

## Prerequisites

- A Linux distribution (e.g., Ubuntu, Fedora, etc.)
- A C compiler (GCC is commonly used and typically pre-installed on Linux systems).

## Step 1: Write Your C Program

Create a file with a `.c` extension using any text editor. For example:

```bash
nano hello.c
```

Add the following code to your file:

```c
#include <stdio.h>

int main() {
    printf("Hello, World!\n");
    return 0;
}
```

## Step 2: Compile the C Program

Use the `gcc` compiler to compile your program. Run the following command:

```bash
gcc hello.c -o hello
```

- `gcc` is the compiler command.
- `hello.c` is your source file.
- `-o hello` specifies the output file name (`hello` in this case).

## Step 3: Run the Compiled Program

After compilation, you can run the program using:

```bash
./hello
```

This will execute your program, and you should see the output:

```
Hello, World!
```

## Additional Commands

- To check if GCC is installed:

```bash
gcc --version
```

- If GCC is not installed, you can install it (for Ubuntu/Debian):

```bash
sudo apt update
sudo apt install gcc
```

For Fedora:

```bash
sudo dnf install gcc
```

## Troubleshooting

- If you encounter a "command not found" error for `gcc`, ensure it is installed.
- If you get a permission error when running the program, use:

```bash
chmod +x hello
```

```

This Markdown file explains the process with commands you need to compile and run C code on Linux.
