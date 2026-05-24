"""
모든 fetch 스크립트가 공유하는 유틸리티.
- merge_with_existing: 기존 데이터 보존하며 안전하게 병합
- sanity_check: 데이터 무결성 검증
"""

from pathlib import Path
from typing import Optional, Tuple, List
import pandas as pd


def merge_with_existing(
    new_df: pd.DataFrame,
    output_file: Path,
    key_cols: List[str],
) -> pd.DataFrame:
    """
    새 데이터를 기존 Parquet 파일과 머지.
    같은 키(예: date+indicator)는 새 데이터로 덮어쓰지만, 새 데이터에 없는
    기존 데이터는 보존된다. 부분 fetch 실패 시 기존 데이터 보호.
    """
    if output_file.exists():
        try:
            existing = pd.read_parquet(output_file)
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=key_cols, keep="last")
        except Exception as e:
            print(f"  [WARN] 기존 파일 읽기 실패, 새 데이터로 덮어쓰기: {e}")
            combined = new_df
    else:
        combined = new_df

    combined = combined.sort_values(key_cols).reset_index(drop=True)
    combined.to_parquet(output_file, index=False)
    return combined


def sanity_check(
    df: pd.DataFrame,
    name: str,
    value_range: Optional[Tuple[float, float]] = None,
    max_lag_days: Optional[int] = None,
    date_col: str = "date",
    value_col: str = "value",
) -> List[str]:
    """
    데이터프레임의 sanity check를 수행. 경고 리스트 반환 (비어있으면 OK).
    fetch 스크립트는 이 경고를 stdout으로 출력하면 헬스체크에서 감지 가능.
    """
    warnings = []

    if df is None or df.empty:
        warnings.append(f"[{name}] 빈 DataFrame")
        return warnings

    # NaN 비율 체크
    if value_col in df.columns:
        nan_ratio = df[value_col].isna().mean()
        if nan_ratio > 0.1:
            warnings.append(f"[{name}] NaN 비율 높음: {nan_ratio:.1%}")

        # 값 범위 체크
        if value_range is not None:
            low, high = value_range
            valid = df[value_col].dropna()
            out = valid[(valid < low) | (valid > high)]
            if len(out) > 0:
                warnings.append(
                    f"[{name}] 범위 벗어난 값 {len(out)}건 "
                    f"(허용: {low}~{high}, 실제 min/max: {valid.min():.2f}/{valid.max():.2f})"
                )

    # 데이터 지연 체크
    if max_lag_days is not None and date_col in df.columns:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        if len(dates) > 0:
            latest = dates.max()
            lag = (pd.Timestamp.now().normalize() - latest.normalize()).days
            if lag > max_lag_days:
                warnings.append(
                    f"[{name}] 최신 데이터 {lag}일 전 (허용: {max_lag_days}일)"
                )

    return warnings
