import os

# Root directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define paths for folders
RAW_DATA_DIR = os.path.join(BASE_DIR, "01_rawdata")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# Create outputs folder if it doesn't exist
os.makedirs(OUTPUTS_DIR, exist_ok=True)
