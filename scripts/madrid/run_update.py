import subprocess
import sys
import os

def run_step(name, command):
    print(f"--- Running {name} ---")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error in step {name}: {e}")
        sys.exit(e.returncode or 1)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rebuild = "--rebuild" in sys.argv
    rebuild_flag = ["--rebuild"] if rebuild else []
    
    # 1. Generate deputies from Wikipedia (Static for now)
    run_step("Generate Deputies", [sys.executable, os.path.join(script_dir, "generate_diputados.py")])
    
    # 2. Download session diaries
    run_step("Download PDFs", [sys.executable, os.path.join(script_dir, "download_pdfs.py")])
    
    # 3. Parse PDFs to extract votes
    run_step("Parse PDFs", [sys.executable, os.path.join(script_dir, "parse_pdfs.py"), *rebuild_flag])
    
    # 4. Transform
    run_step("Transform Data", [sys.executable, os.path.join(script_dir, "transform.py"), *rebuild_flag])

if __name__ == "__main__":
    main()
