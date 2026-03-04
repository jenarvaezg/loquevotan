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
    parser = argparse.ArgumentParser(description="Pipeline de actualización de CyL.")
    parser.add_argument("--rebuild", action="store_true", help="Fuerza reprocesado completo.")
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Procesa solo legislatura activa (11) para runs rápidos.",
    )
    parser.add_argument(
        "--ai-parse-fallback",
        action="store_true",
        help="Activa fallback IA en parse_texts para documentos de baja confianza.",
    )
    parser.add_argument(
        "--ai-parse-model",
        default=os.environ.get("CYL_PARSE_AI_MODEL", "gemini-2.5-flash"),
        help="Modelo Gemini para parse fallback (solo si --ai-parse-fallback).",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    rebuild_flag = ["--rebuild"] if args.rebuild else []
    target_legs = "11" if args.active_only else "11,10,9,8,7"
    
    # 1. Scrape deputies
    run_step(
        "Scrape Deputies",
        [sys.executable, os.path.join(script_dir, "scrape_diputados.py"), "--legislaturas", target_legs],
    )
    
    # 2. Scrape session index
    run_step(
        "Scrape Sessions Index",
        [sys.executable, os.path.join(script_dir, "scrape_sessions.py"), "--legislaturas", target_legs],
    )
    
    # 3. Download session texts (Only new ones)
    run_step("Download Texts", [sys.executable, os.path.join(script_dir, "download_texts.py")])
    
    # 4. Parse texts (Extract nominal votes)
    parse_command = [sys.executable, os.path.join(script_dir, "parse_texts.py"), *rebuild_flag]
    if args.ai_parse_fallback:
        parse_command.extend(["--ai-fallback", "--ai-model", args.ai_parse_model])
    run_step("Parse Texts", parse_command)
    
    # 5. Transform (Generate optimized JSONs for frontend)
    run_step("Transform Data", [sys.executable, os.path.join(script_dir, "transform.py"), *rebuild_flag])

if __name__ == "__main__":
    main()
