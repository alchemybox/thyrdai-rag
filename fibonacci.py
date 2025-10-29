#!/usr/bin/env python3
"""
Fibonacci Sequence Calculator

This module provides multiple implementations for calculating Fibonacci numbers.
"""


def fibonacci_iterative(n):
    """
    Calculate the nth Fibonacci number using an iterative approach.

    Args:
        n (int): The position in the Fibonacci sequence (0-indexed)

    Returns:
        int: The nth Fibonacci number

    Raises:
        ValueError: If n is negative

    Time Complexity: O(n)
    Space Complexity: O(1)
    """
    if n < 0:
        raise ValueError("n must be non-negative")

    if n <= 1:
        return n

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b

    return b


def fibonacci_recursive(n):
    """
    Calculate the nth Fibonacci number using a recursive approach.

    Args:
        n (int): The position in the Fibonacci sequence (0-indexed)

    Returns:
        int: The nth Fibonacci number

    Raises:
        ValueError: If n is negative

    Time Complexity: O(2^n)
    Space Complexity: O(n) due to call stack

    Note: This is inefficient for large n due to repeated calculations.
    """
    if n < 0:
        raise ValueError("n must be non-negative")

    if n <= 1:
        return n

    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_memoized(n, memo=None):
    """
    Calculate the nth Fibonacci number using memoization.

    Args:
        n (int): The position in the Fibonacci sequence (0-indexed)
        memo (dict): Dictionary to store previously calculated values

    Returns:
        int: The nth Fibonacci number

    Raises:
        ValueError: If n is negative

    Time Complexity: O(n)
    Space Complexity: O(n)
    """
    if memo is None:
        memo = {}

    if n < 0:
        raise ValueError("n must be non-negative")

    if n <= 1:
        return n

    if n in memo:
        return memo[n]

    memo[n] = fibonacci_memoized(n - 1, memo) + fibonacci_memoized(n - 2, memo)
    return memo[n]


def fibonacci_generator(count):
    """
    Generate Fibonacci numbers up to count.

    Args:
        count (int): Number of Fibonacci numbers to generate

    Yields:
        int: Next Fibonacci number in the sequence

    Raises:
        ValueError: If count is negative

    Example:
        >>> list(fibonacci_generator(5))
        [0, 1, 1, 2, 3]
    """
    if count < 0:
        raise ValueError("count must be non-negative")

    a, b = 0, 1
    for _ in range(count):
        yield a
        a, b = b, a + b


def fibonacci_sequence(n):
    """
    Generate a list of the first n Fibonacci numbers.

    Args:
        n (int): Number of Fibonacci numbers to generate

    Returns:
        list: List containing the first n Fibonacci numbers

    Raises:
        ValueError: If n is negative

    Example:
        >>> fibonacci_sequence(7)
        [0, 1, 1, 2, 3, 5, 8]
    """
    if n < 0:
        raise ValueError("n must be non-negative")

    return list(fibonacci_generator(n))


def main():
    """
    Demonstrate the different Fibonacci implementations.
    """
    print("Fibonacci Sequence Calculator")
    print("=" * 50)

    # Calculate the first 10 Fibonacci numbers
    n = 10
    print(f"\nFirst {n} Fibonacci numbers:")
    print(fibonacci_sequence(n))

    # Calculate specific Fibonacci numbers
    print(f"\nCalculating specific Fibonacci numbers:")
    for i in [5, 10, 15, 20]:
        result = fibonacci_iterative(i)
        print(f"F({i}) = {result}")

    # Demonstrate the generator
    print(f"\nUsing generator to get first 15 Fibonacci numbers:")
    fib_gen = fibonacci_generator(15)
    print([num for num in fib_gen])

    # Compare methods (for smaller values)
    test_n = 10
    print(f"\nComparing methods for F({test_n}):")
    print(f"  Iterative:  {fibonacci_iterative(test_n)}")
    print(f"  Recursive:  {fibonacci_recursive(test_n)}")
    print(f"  Memoized:   {fibonacci_memoized(test_n)}")


if __name__ == "__main__":
    main()
