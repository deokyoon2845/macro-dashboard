"""
모든 데이터 파일의 무결성을 점검하고 문제 발견 시 Gmail로 알람.
워크플로의 마지막 단계에서 실행된다.
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import HEALTH_CHECKS

DATA_DIR = Path(__file__).parent.parent / "data"


def check_file(name: str, config: dict) -> list:
    """파일 하나 검증, 문제 리스트 반환."""
    issues = []
    path = DATA_DIR / name

    if not path.exists():
        issues.append(f"{name}: 파일 없음")
        return issues

    try:
        df = pd.read_parquet(path)
    except Exception as e:
        issues.append(f"{name}: 읽기 실패 ({e})")
        return issues

    if len(df) < config.get("min_rows", 0):
        issues.append(f"{name}: 행 수 부족 ({len(df)} < {config['min_rows']})")

    max_lag = config.get("max_lag_days")
    if max_lag and "date" in df.columns:
        dates = pd.to_datetime(df["date"], errors="coerce").dropna()
        if len(dates) == 0:
            issues.append(f"{name}: 유효한 날짜 없음")
        else:
            lag = (pd.Timestamp.now().normalize() - dates.max().normalize()).days
            if lag > max_lag:
                issues.append(f"{name}: 데이터 {lag}일 지연 (허용: {max_lag}일)")

    return issues


def send_gmail_alert(issues: list, repo_url: str = "") -> bool:
    """Gmail 알람 발송. 성공 시 True 반환."""
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        print("  Gmail 환경변수 없음. 발송 스킵.")
        return False

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    body_lines = [
        f"Macro Monitor — 데이터 헬스체크 실패",
        f"시각: {timestamp}",
        f"이슈 {len(issues)}건:",
        "",
    ]
    body_lines.extend(f"  - {issue}" for issue in issues)
    body_lines.append("")
    if repo_url:
        body_lines.append(f"확인: {repo_url}/actions")
    body = "\n".join(body_lines)

    msg = MIMEText(body)
    msg["Subject"] = f"[Macro Alert] 데이터 헬스체크 이슈 {len(issues)}건"
    msg["From"] = gmail_user
    msg["To"] = gmail_user

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
        print(f"  Gmail 발송 완료: {gmail_user}")
        return True
    except Exception as e:
        print(f"  Gmail 발송 실패: {e}")
        return False


def main():
    print(f"[Health Check] 시작: {datetime.utcnow().isoformat()}Z")

    all_issues = []
    for name, config in HEALTH_CHECKS.items():
        issues = check_file(name, config)
        if issues:
            for issue in issues:
                print(f"  ⚠ {issue}")
            all_issues.extend(issues)
        else:
            print(f"  ✓ {name}")

    if all_issues:
        print(f"\n총 {len(all_issues)}건 이슈. 알람 시도.")
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        repo_url = f"https://github.com/{repo}" if repo else ""
        send_gmail_alert(all_issues, repo_url)
        sys.exit(0)  # 이슈는 정보이고, 워크플로 자체는 실패시키지 않음
    else:
        print("\n✓ 전체 정상")


if __name__ == "__main__":
    main()
