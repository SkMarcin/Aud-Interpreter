import os
import shutil

# --- Configuration ---
TEST_ROOT_DIR = "examples/long_example/test_environment"

# --- Main Cleanup Logic ---
def cleanup_test_environment():
    print(f"--- Cleaning up test environment in '{TEST_ROOT_DIR}' ---")

    if os.path.exists(TEST_ROOT_DIR):
        try:
            shutil.rmtree(TEST_ROOT_DIR)
            print(f"Successfully removed '{TEST_ROOT_DIR}'.")
        except OSError as e:
            print(f"Error removing directory {TEST_ROOT_DIR}: {e}")
    else:
        print(f"'{TEST_ROOT_DIR}' does not exist. Nothing to clean up.")

    print("\n--- Cleanup complete! ---")


if __name__ == "__main__":
    cleanup_test_environment()