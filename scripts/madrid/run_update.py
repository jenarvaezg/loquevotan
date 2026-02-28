import subprocess
import sys
import os

def run_step(name, command):
    print(f"--- Running {name} ---")
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error in step {name}: {e}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Generate deputies from Wikipedia (Static for now)
    run_step("Generate Deputies", f"python3 {os.path.join(script_dir, 'generate_diputados.py')}")
    
    # 2. Generate votes (Mock/Investiture for now)
    run_step("Generate Votes", f"python3 {os.path.join(script_dir, 'generate_votes.py')}")
    
    # 3. Transform
    run_step("Transform Data", f"python3 {os.path.join(script_dir, 'transform.py')}")

if __name__ == "__main__":
    main()
