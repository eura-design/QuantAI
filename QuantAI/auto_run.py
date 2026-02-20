import schedule
import time
import subprocess
import os
from datetime import datetime

# 설정: 실행 주기 (1시간마다)
INTERVAL_MINUTES = 60

def run_analysis():
    print(f"\n[AutoRun] Starting Analysis... {datetime.now()}")
    
    # 1. AI 분석 실행 (main.py)
    try:
        subprocess.run(["python", "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Analysis failed: {e}")
        return

    # 2. GitHub 배포 (git push)
    print("[AutoRun] Deploying to GitHub...")
    try:
        subprocess.run(["git", "add", "index.html"], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto Update: {datetime.now()}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("[SUCCESS] Deployed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Deploy failed: {e}")

# 스케줄 설정
# 매시 정각에 실행하려면 schedule.every().hour.at(":00").do(run_analysis)
# 1시간마다 실행
schedule.every(60).minutes.do(run_analysis)

if __name__ == "__main__":
    print("========================================")
    print(f"[QuantAI] Auto-Runner Started")
    print(f"[Schedule] Every {INTERVAL_MINUTES} minutes")
    print("========================================")
    
    # 시작하자마자 1회 즉시 실행
    run_analysis()
    
    while True:
        schedule.run_pending()
        time.sleep(1)
