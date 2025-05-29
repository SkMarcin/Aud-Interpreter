import os
import shutil

# --- Configuration ---
TEST_ROOT_DIR = "examples/long_example/test_environment"
MUSIC_COLLECTION_DIR = os.path.join(TEST_ROOT_DIR, "music_collection_test")
SHORT_TRACKS_DEST_DIR = os.path.join(TEST_ROOT_DIR, "short_tracks_test")
MP3_SOURCE_DIR = "examples/long_example/mp3_source_files"

MIN_DURATION_TEST = 3000

# --- Helper Function ---
def create_and_populate_folder(folder_path, files_to_copy, source_dir):
    """Creates a folder and copies specified files into it."""
    os.makedirs(folder_path, exist_ok=True)
    print(f"Created: {folder_path}")
    for file_name in files_to_copy:
        src_path = os.path.join(source_dir, file_name)
        dest_path = os.path.join(folder_path, file_name)
        if os.path.exists(src_path):
            shutil.copyfile(src_path, dest_path)
            print(f"  Copied '{file_name}' to '{folder_path}'")
        else:
            print(f"  WARNING: Source file '{src_path}' not found. Skipping.")

# --- Main Setup Logic ---
def setup_test_environment():
    print(f"--- Setting up test environment in '{TEST_ROOT_DIR}' ---")

    # 1. Clean up any previous test environment
    if os.path.exists(TEST_ROOT_DIR):
        print(f"Existing '{TEST_ROOT_DIR}' found. Cleaning up...")
        shutil.rmtree(TEST_ROOT_DIR)
        print("Cleanup complete.")

    # 2. Create base directories
    os.makedirs(MUSIC_COLLECTION_DIR, exist_ok=True)
    os.makedirs(SHORT_TRACKS_DEST_DIR, exist_ok=True)
    print(f"Created primary directories: {MUSIC_COLLECTION_DIR} and {SHORT_TRACKS_DEST_DIR}")

    if not os.path.exists(MP3_SOURCE_DIR):
        print(f"\nERROR: The '{MP3_SOURCE_DIR}' folder was not found.")
        print("Please create this folder and place your actual short and long MP3 files inside it.")
        print("Example files needed: short_track_1.mp3, long_track_A.mp3, etc.")
        return

    # 3. Populate music_collection_test with subfolders and files
    print("\nPopulating music_collection_test with files and subfolders...")

    # Root of music_collection
    create_and_populate_folder(
        MUSIC_COLLECTION_DIR,
        ["long_track_A.mp3", "short_track_A.mp3"],
        MP3_SOURCE_DIR
    )
    # Create a dummy non-audio file
    with open(os.path.join(MUSIC_COLLECTION_DIR, "non_audio_file.txt"), "w") as f:
        f.write("This is not an audio file.")

    # Subfolder 1: GenreA
    genre_a_path = os.path.join(MUSIC_COLLECTION_DIR, "GenreA")
    create_and_populate_folder(
        genre_a_path,
        ["long_track_B.mp3", "short_track_B.mp3"],
        MP3_SOURCE_DIR
    )

    # Subfolder 2: GenreB (empty to test empty folder handling)
    genre_b_path = os.path.join(MUSIC_COLLECTION_DIR, "GenreB")
    os.makedirs(genre_b_path, exist_ok=True)
    print(f"Created (empty): {genre_b_path}")


if __name__ == "__main__":
    setup_test_environment()