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
    
    # 1. Scrape deputies
    run_step("Scrape Deputies", [sys.executable, os.path.join(script_dir, "scrape_diputados.py")])
    
    # 2. Scrape session index
    run_step("Scrape Sessions Index", [sys.executable, os.path.join(script_dir, "scrape_sessions.py")])
    
    # 3. Download session texts (Only new ones)
    run_step("Download Texts", [sys.executable, os.path.join(script_dir, "download_texts.py")])
    
    # 4. Parse texts (Extract nominal votes)
    run_step("Parse Texts", [sys.executable, os.path.join(script_dir, "parse_texts.py"), *rebuild_flag])
    
    # 5. Transform (Generate optimized JSONs for frontend)
    run_step("Transform Data", [sys.executable, os.path.join(script_dir, "transform.py"), *rebuild_flag])

if __name__ == "__main__":
    main()
