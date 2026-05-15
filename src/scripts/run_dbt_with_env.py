import os
import subprocess
from dotenv import load_dotenv

def run_dbt():
    load_dotenv()
    
    # On s'assure que les variables d'environnement sont passées au sous-processus
    env = os.environ.copy()
    
    dbt_exe = os.path.join(os.getcwd(), "venv", "Scripts", "dbt.exe")
    project_dir = "dbt"
    profiles_dir = "dbt"
    
    cmd = [dbt_exe, "run", "--project-dir", project_dir, "--profiles-dir", profiles_dir]
    
    print(f"INFO: Execution de dbt : {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    print(result.stdout)
    if result.returncode != 0:
        print("ERROR: dbt run a echoue")
        print(result.stderr)
    else:
        print("SUCCESS: dbt run termine avec succes")

if __name__ == "__main__":
    run_dbt()
