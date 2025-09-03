#!/usr/bin/env python3
"""
Test runner for crypto_bs package
Run all tests with proper environment setup
"""

import sys
import os
import subprocess

def run_tests():
    """Run all tests using pytest"""
    # Add current directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env = os.environ.copy()
    env['PYTHONPATH'] = current_dir

    # Run pytest
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/',
        '-v',
        '--tb=short',
        '--color=yes'
    ]

    print("Running crypto_bs tests with pytest...")
    print("=" * 60)

    result = subprocess.run(cmd, env=env, cwd=current_dir)

    if result.returncode == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {result.returncode}")
        sys.exit(result.returncode)

def run_tests_direct():
    """Run tests directly without pytest"""
    # Add current directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)

    # Import and run test file
    try:
        import tests.test_pricing
        print("Tests completed successfully!")
    except SystemExit as e:
        if e.code != 0:
            print(f"Tests failed with exit code {e.code}")
            sys.exit(e.code)
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--direct":
        run_tests_direct()
    else:
        try:
            run_tests()
        except FileNotFoundError:
            print("pytest not found, falling back to direct test execution...")
            run_tests_direct()
