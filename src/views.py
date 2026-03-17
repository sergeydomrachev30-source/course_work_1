# import json
import logging
import os
from datetime import datetime, timedelta

import pandas as pd

from src.config import api_key
from src.utils import (calculate_expenses_transfers, calculate_incomes, get_currency_rate, get_sp500_stocks,
                       get_top_5_transactions, load_excel_data, process_card_data, say_hello)

logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
log_file_path = os.path.join(logs_dir, "app.log")


def main_page_function(date_time_str: str) -> dict:
    """
    Функция принимает на вход строку с датой и временем в формате YYYY-MM-DD HH:MM:SS
    и возвращающую JSON-ответ со следующими данными: приветствие, по каждой карте: последние 4 цифры карты,
    общая сумма расходов, кешбэк (1 рубль на каждые 100 рублей), топ-5 транзакций по сумме платежа, курс валют,
    стоимость акций из S&P500
    """
    transaction_df = load_excel_data("../data/operations.xlsx")
    if transaction_df.empty:
        logging.warning("Файл пуст или не найден.")
        return {}
    # Получаем приветствие
    greeting = say_hello()
    if "Номер карты" not in transaction_df.columns:
        logging.error("В данных нет колонки 'Номер карты'")
        return {"greeting": greeting, "cards": [], "top_transactions": [], "currency_data": [], "stock_prices": []}

    cards_data = []
    for card_number in transaction_df["Номер карты"].unique():
        card_data = transaction_df[transaction_df["Номер карты"] == card_number]
        if not card_data.empty:  # Проверка на пустоту данных
            last_four, total_spent, cashback = process_card_data(card_data)
            cards_data.append({"last_digits": last_four, "total_spent": total_spent, "cashback": cashback})
        else:
            logging.warning(f"Нет данных для карты номер {card_number}.")

    top_5_transactions = get_top_5_transactions(transaction_df)
    transactions_data = top_5_transactions.to_dict(orient="records")

    try:
        currency_rates = get_currency_rate(api_key=api_key)["rates"]
        currency_data = [{"currency": key, "rate": round(value, 2)} for key, value in currency_rates.items()]
        print("Курсы валют (внутри функции):", currency_data)
    except Exception:
        currency_data = []

    try:
        stock_data = get_sp500_stocks()
    except Exception:
        stock_data = []

    response = {
        "greeting": greeting,
        "cards": cards_data,
        "top_transactions": transactions_data,
        "currency_data": currency_data,
        "stock_prices": stock_data,
    }
    return response


def events_page_function(date_str: str, range_type: str = "M") -> dict:
    """
    Основная функция для страницы 'События'. Собирает отчет по расходам,
    переводам, доходам, валютам и акциям за выбранный период.
    """
    transaction_df = load_excel_data("../data/operations.xlsx")
    if transaction_df.empty:
        logging.warning("Файл пуст или не найден.")
        return {}

    transaction_df["Дата платежа"] = pd.to_datetime(transaction_df["Дата платежа"], dayfirst=True)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    if range_type == "W":
        start_date = date_obj - timedelta(days=date_obj.weekday())
        end_date = start_date + timedelta(days=6)
    elif range_type == "M":
        start_date = date_obj.replace(day=1)
        end_date = date_obj
    elif range_type == "Y":
        start_date = date_obj.replace(month=1, day=1)
        end_date = date_obj
    elif range_type == "ALL":
        start_date = datetime(2018, 1, 1)
        end_date = date_obj
    else:
        logging.error(f"Некорректный диапазон: {range_type}")
        raise ValueError("Некорректный диапазон данных")

    start_date_str = start_date.strftime("%d.%m.%Y")
    end_date_str = end_date.strftime("%d.%m.%Y")

    result = calculate_expenses_transfers(transaction_df, start_date_str, end_date_str)
    expenses_data = result["expenses"]
    transfers_and_cash_data = result["transfers_and_cash"]

    incomes_data = calculate_incomes(transaction_df, start_date_str, end_date_str)

    try:
        currency_rates = get_currency_rate(api_key=api_key)["rates"]
        currency_data = [{"currency": key, "rate": round(value, 2)} for key, value in currency_rates.items()]
        print("Курсы валют (внутри функции):", currency_data)
    except Exception:
        currency_data = []

    try:
        stock_data = get_sp500_stocks()
    except Exception:
        stock_data = []

    response = {
        "expenses": {
            "total_amount": expenses_data.get("total_amount", 0),
            "main": expenses_data.get("main", []),
            "date_range": {"start": start_date_str, "end": end_date_str},
        },
        "transfers_and_cash": transfers_and_cash_data,
        "income": incomes_data,
        "currency_data": currency_data,
        "stock_prices": stock_data,
    }

    return response
