import PyInstaller.__main__
import os
import shutil

def build():
    # Define build arguments
    args = [
        'main.py',  # Entry point
        '--name=RPG Game',  # Executable name
        '--onedir',  # Create a directory containing the executable
        '--windowed',  # Hide the console window
        '--add-data=assets:assets',  # Include assets directory
        '--clean',  # Clean PyInstaller cache
        '--noconfirm',  # Do not ask for confirmation
        # '--icon=assets/icon.ico', # Uncomment if you have an icon
    ]

    print("Building RPG Game...")
    PyInstaller.__main__.run(args)
    print("Build complete! Check the 'dist' folder.")

if __name__ == "__main__":
    # Clean up previous builds if they exist
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')
        
    build()
