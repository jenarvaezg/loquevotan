import subprocess
import sys
import os

def run_step(name, command):
    print(f"--- Running {name} ---")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error in {name}: {e}")
        sys.exit(e.returncode or 1)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rebuild = "--rebuild" in sys.argv
    rebuild_flag = ["--rebuild"] if rebuild else []
    
    # 1. Scrape Deputies
    run_step("Scrape Deputies", [sys.executable, os.path.join(script_dir, "scrape_diputados.py")])
    
    # 2. Scrape Sessions
    run_step("Scrape Sessions", [sys.executable, os.path.join(script_dir, "scrape_sessions.py")])
    
    # 3. Download PDFs
    run_step("Download PDFs", [sys.executable, os.path.join(script_dir, "download_pdfs.py")])
    
    # 4. Parse PDFs
    run_step("Parse PDFs", [sys.executable, os.path.join(script_dir, "parse_pdfs.py"), *rebuild_flag])
    
    # 5. Transform
    run_step("Transform Data", [sys.executable, os.path.join(script_dir, "transform.py"), *rebuild_flag])

if __name__ == "__main__":
    main()
