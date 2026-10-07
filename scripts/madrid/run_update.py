import subprocess
import sys
import os
import argparse

def run_step(name, command, fatal=True):
    print(f"--- Running {name} ---")
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error in step {name}: {e}")
        if fatal:
            sys.exit(e.returncode or 1)
        return False

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

    # 2. Refresh session index before downloading diaries. asambleamadrid.es
    # blocks some networks (GitHub-hosted runners included): without access,
    # still rebuild the published data from the diaries already downloaded so
    # transform fixes (e.g. ISO dates) reach Madrid too.
    online = run_step(
        "Scrape Sessions Index",
        [sys.executable, os.path.join(script_dir, "scrape_sessions.py"), "--legislaturas", target_legs],
        fatal=False,
    )

    # 3. Download session diaries
    if online:
        run_step("Download PDFs", [sys.executable, os.path.join(script_dir, "download_pdfs.py")])
    else:
        print("::warning title=Madrid::Sin acceso a asambleamadrid.es; se regenera con los diarios ya descargados.")
    
    # 4. Parse PDFs to extract votes
    run_step("Parse PDFs", [sys.executable, os.path.join(script_dir, "parse_pdfs.py"), *rebuild_flag])
    
    # 5. Transform
    run_step("Transform Data", [sys.executable, os.path.join(script_dir, "transform.py"), *rebuild_flag])

if __name__ == "__main__":
    main()
