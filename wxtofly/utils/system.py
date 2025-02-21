import os, shutil
from pathlib import Path

# initialize run output path subdirectory
def create_clean_run_output_subdir(run_output_path, *paths):
    
    output_path = Path(os.path.join(run_output_path, *paths))

    if output_path.exists():
        for p in output_path.iterdir():
            if p.is_dir():
                shutil.rmtree(p.resolve())
            elif p.is_file():
                p.unlink()
    else:
        os.makedirs(str(output_path.resolve()))
    return str(output_path.resolve())

# returns list of direct subdirectories
def get_direct_subdirectories(path):
    return list(filter(lambda x: os.path.isdir(os.path.join(path, x)), os.listdir(path)))