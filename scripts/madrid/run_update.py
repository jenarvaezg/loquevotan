import subprocess
import sys
import os
import argparse

def run_step(name, command):
    print(f"--- Running {name} ---")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error in step {name}: {e}")
        sys.exit(e.returncode or 1)

def main():
    parser = argparse.ArgumentParser(description="Pipeline de actualización de Madrid.")
    parser.add_argument("--rebuild", action="store_true", help="Fuerza reprocesado completo.")
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Procesa solo legislatura activa (XIII) para runs rápidos.",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    rebuild_flag = ["--rebuild"] if args.rebuild else []
    target_legs = "XIII" if args.active_only else "XIII,XII,XI,X"
    
    # 1. Generate deputies from Wikipedia (Static for now)
    run_step("Generate Deputies", [sys.executable, os.path.join(script_dir, "generate_diputados.py")])

    # 2. Refresh session index before downloading diaries
    run_step(
        "Scrape Sessions Index",
        [sys.executable, os.path.join(script_dir, "scrape_sessions.py"), "--legislaturas", target_legs],
    )
    
    # 3. Download session diaries
    run_step("Download PDFs", [sys.executable, os.path.join(script_dir, "download_pdfs.py")])
    
    # 4. Parse PDFs to extract votes
    run_step("Parse PDFs", [sys.executable, os.path.join(script_dir, "parse_pdfs.py"), *rebuild_flag])
    
    # 5. Transform
    run_step("Transform Data", [sys.executable, os.path.join(script_dir, "transform.py"), *rebuild_flag])

if __name__ == "__main__":
    main()
