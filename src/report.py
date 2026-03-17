import functools
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, Union

import pandas as pd

from src.utils import load_excel_data

logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

log_file_path = os.path.join(logs_dir, "app.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file_path, mode="w", encoding="utf-8")],
)


def report_to_file(filename: Optional[Union[str, Callable]] = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result_df = func(*args, **kwargs)
            if result_df is None or result_df.empty:
                return result_df
            target_file = filename if isinstance(filename, str) else f"{func.__name__}.json"
            result_df.to_json(target_file, orient="records", force_ascii=False, indent=4, date_format="iso")
            logging.info(f"Отчет '{func.__name__}' сохранен в файл: {target_file}")
            return result_df

        return wrapper

    if callable(filename):
        func_to_decorate = filename
        filename = None
        return decorator(func_to_decorate)
    return decorator


@report_to_file
def spending_by_category(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> pd.DataFrame:
    """Возвращает траты по категории за 3 месяца (регистронезависимо)."""
    if date:
        is_year_first = str(date).startswith("20")
        end_date = pd.to_datetime(date, dayfirst=not is_year_first)
    else:
        end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    df = transactions.copy()
    df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], dayfirst=True)

    report_df = df[
        (df["Категория"].str.lower() == category.lower())
        & (df["Дата платежа"] <= end_date)
        & (df["Дата платежа"] >= start_date)
    ]
    return report_df


@report_to_file
def spending_by_weekday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """Средние траты по дням недели с индексацией 1-7."""
    if date:
        is_year_first = str(date).startswith("20")
        end_date = pd.to_datetime(date, dayfirst=not is_year_first)
    else:
        end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    df = transactions.copy()
    df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], dayfirst=True)

    report_df = df[
        (df["Дата платежа"] <= end_date) & (df["Дата платежа"] >= start_date) & (df["Сумма платежа"] < 0)
    ].copy()

    report_df["Сумма платежа"] = report_df["Сумма платежа"].abs()
    report_df["День недели"] = report_df["Дата платежа"].dt.day_name(locale="Russian")

    result = report_df.groupby("День недели")["Сумма платежа"].mean().reset_index().round(2)

    weekdays_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    result["День недели"] = pd.Categorical(result["День недели"], categories=weekdays_order, ordered=True)
    result = result.sort_values("День недели").reset_index(drop=True)

    result.index = result.index + 1
    return result


@report_to_file
def spending_by_workday(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """Средние траты в рабочие и выходные дни."""
    if date:
        is_year_first = str(date).startswith("20")
        end_date = pd.to_datetime(date, dayfirst=not is_year_first)
    else:
        end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    df = transactions.copy()
    df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], dayfirst=True)

    mask = (df["Дата платежа"] >= start_date) & (df["Дата платежа"] <= end_date) & (df["Сумма платежа"] < 0)
    df_filtered = df.loc[mask].copy()

    if df_filtered.empty:
        return pd.DataFrame(columns=["Тип дня", "Средние траты"])

    df_filtered["Сумма платежа"] = df_filtered["Сумма платежа"].abs()
    df_filtered["is_weekend"] = df_filtered["Дата платежа"].dt.weekday >= 5
    df_filtered["Тип дня"] = df_filtered["is_weekend"].map({True: "Выходной", False: "Рабочий"})

    result = (
        df_filtered.groupby(["Дата платежа", "Тип дня"])["Сумма платежа"]
        .sum()
        .groupby("Тип дня")
        .mean()
        .round(2)
        .reset_index()
    )
    result.columns = ["Тип дня", "Средние траты"]
    return result


transaction_df = load_excel_data("../data/operations.xlsx")
