import json
import logging
import os
# import re
# from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from src.utils import load_excel_data

transaction_df = load_excel_data("../data/operations.xlsx")

logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
log_file_path = os.path.join(logs_dir, "app.log")

if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file_path, mode="w", encoding="utf-8")],
)


def get_profitable_categories(df: pd.DataFrame, year: int, month: int) -> str:
    """
    Анализирует расходы по категориям из DataFrame (загруженного из Excel).
    Возвращает JSON со списком категорий и суммой трат в порядке убывания.
    """
    logging.info(f"Начало анализа за {year}-{month}")
    df["date"] = pd.to_datetime(df["Дата платежа"], dayfirst=True)

    filtered_df = df[
        df.apply(
            lambda row: row["date"].year == year and row["date"].month == month and row["Сумма платежа"] < 0, axis=1
        )
    ]
    logging.info(f"Фильтрация завершена, количество записей: {len(filtered_df)}")
    cashback_by_category = filtered_df.groupby("Категория")["Кэшбэк"].sum().astype(int)
    sorted_cashback_by_category = cashback_by_category.sort_values(ascending=False).to_dict()
    filtered_cashback_dict = {key: value for key, value in sorted_cashback_by_category.items() if value > 0}

    logging.info("Анализ завершен")
    return json.dumps(filtered_cashback_dict, ensure_ascii=False, indent=4)


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """
    Рассчитывает сумму накоплений в Инвесткопилку за заданный месяц.
    """
    if limit not in [10, 50, 100]:
        logging.error(f"Некорректное значение limit: {limit}. Допустимые значения: 10, 50, 100.")
        return 0.0

    total_savings = 0.0
    try:
        # Универсальный парсинг целевого месяца
        target_dt = pd.to_datetime(month)
    except Exception:
        logging.error(f"Некорректный формат аргумента month: {month}. Ожидается 'YYYY-MM'.")
        return 0.0

    for transaction in transactions:
        try:
            date_val = transaction.get("Дата операции")
            amount_val = transaction.get("Сумма операции")

            if date_val is None or amount_val is None:
                continue

            date_str = str(date_val)
            if "." in date_str:
                tx_date = pd.to_datetime(date_val, dayfirst=True)
            else:
                # Если точек нет (2024-03-10) — это ISO формат, dayfirst не нужен
                tx_date = pd.to_datetime(date_val)

            amount = float(amount_val)

            if tx_date.year == target_dt.year and tx_date.month == target_dt.month and amount < 0:
                expense = abs(float(amount))
                remainder = expense % limit

                if remainder == 0:
                    savings = float(limit)
                else:
                    savings = limit - remainder

                total_savings += savings
        except (ValueError, TypeError, Exception) as e:
            logging.warning(f"Ошибка в данных транзакции {transaction}: {e}")
            continue
    logging.info(f"Общая сумма накоплений за {month}: {total_savings}")
    return round(total_savings, 2)


def search_transactions(query: str, df: pd.DataFrame) -> str:
    """Ищет запрос в описании или категории транзакций."""
    try:
        query = query.lower()
        mask = df["Описание"].astype(str).str.lower().str.contains(query, na=False) | df["Категория"].astype(
            str
        ).str.lower().str.contains(query, na=False)
        results_df = df[mask]
        logging.info(f"Поиск '{query}' в {df}: найдено {len(results_df)} строк.")

        return results_df.to_json(orient="records", force_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка при работе с Excel: {e}")
        return json.dumps([])


def find_phone_transactions(df: pd.DataFrame) -> str:
    """
    Ищет транзакции, содержащие мобильные номера РФ в описании.
    Возвращает JSON-строку с найденными записями.
    """
    phone_pattern = r"(?:\+7|8)\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}"
    try:
        if "Описание" not in df.columns:
            logging.error("Колонка 'Описание' не найдена в таблице")
            return json.dumps([])

        mask = df["Описание"].astype(str).str.contains(phone_pattern, regex=True, na=False)
        results_df = df[mask]
        logging.info(f"Найдено транзакций с номерами: {len(results_df)}")

        return results_df.to_json(orient="records", force_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка при поиске: {e}")
        return json.dumps([])


def find_person_transfers(df: pd.DataFrame) -> str:
    """
    Ищет транзакции в категории 'Переводы', где в описании указано 'Имя Ф.'
    Возвращает JSON-строку.
    """
    # Регулярное выражение: Слово с большой буквы + пробел + заглавная буква с точкой
    # Находит: "Валерий А.", "Сергей З.", "Артем П."
    name_pattern = r"[А-Я][а-я]+\s[А-Я]\."

    try:
        if df.empty:
            return json.dumps([])

        # Фильтруем: категория "Переводы" И описание соответствует паттерну
        mask = (df["Категория"] == "Переводы") & (
            df["Описание"].astype(str).str.contains(name_pattern, regex=True, na=False)
        )
        results_df = df[mask]
        logging.info(f"Поиск переводов физлицам: найдено {len(results_df)}")
        return results_df.to_json(orient="records", force_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка при поиске переводов: {e}")
        return json.dumps([])
