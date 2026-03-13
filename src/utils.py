from datetime import datetime
import requests
import pandas as pd
import logging
from src.config import api_key
import os
logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))
log_file_path = os.path.join(logs_dir, 'app.log')

if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(log_file_path, mode='w', encoding='utf-8')])

def load_excel_data(filepath: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(filepath)
        logging.info('Файл успешно загружен.')
        return df
    except FileNotFoundError:
        logging.error(f'Файл не найден по пути: {filepath}')
        return pd.DataFrame()
    except Exception as e:
        logging.error(f'Ошибка при загрузке файла: {str(e)}')
        return pd.DataFrame()

#file_path = '../data/operations.xlsx'
#transaction_df = load_excel_data(file_path)
# print(transaction_df.head())

def say_hello() -> str:
    """
    функция для приветствия пользователя в зависимости от времени суток
    """
    hour = datetime.now().hour
    if 5 <= hour < 12:
        logging.info('Приветствие: Доброе утро!')
        return "Доброе утро!"
    elif 12 <= hour < 18:
        logging.info('Приветствие: Добрый день!')
        return "Добрый день!"
    elif 18 <= hour < 23:
        logging.info('Приветствие: Добрый вечер!')
        return "Добрый вечер!"
    else:
        logging.info('Приветствие: Доброй ночи!')
        return "Доброй ночи!"

def process_card_data(card_info: pd.DataFrame, cashback_rate: float = 0.01)-> tuple[str, float, float]:
    """
    Принимает данные карты, возвращает последние 4 цифры, общую сумму расходов и кешбэк.
    """
    if len(card_info) == 0:
        logging.warning('Данные карты пустые.')
        return None, 0, 0

    last_four = card_info["Номер карты"].iloc[0][1:]
    total_spent = round(float(card_info["Сумма операции"][card_info["Сумма операции"]< 0].sum()),2)
    cashback = round(float(abs(total_spent * cashback_rate)),2)

    logging.info(
        f'Обработаны данные карты: последние четыре цифры {last_four}, траты {total_spent}, кешбэк {cashback}.')

    return last_four, total_spent, cashback

def get_top_5_transactions(data:pd.DataFrame) -> pd.DataFrame:
    """
    Функция принимает DataFrame с данными о транзакциях и возвращает топ-5 транзакций по сумме платежа.
    """
    top_5_transactions = data.sort_values(by="Сумма операции", ascending=False).head(5)
    logging.info('Получены топ-5 транзакций.')
    return top_5_transactions

def get_currency_rate(api_key: str) -> dict:
    url = f"https://api.apilayer.com/exchangerates_data/latest?apikey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        logging.info('Курсы валют успешно получены.')
        return response.json()
    else:
        logging.error(f'API запрос не удался, статус код: {response.status_code}')
        raise Exception(f"API запрос не удался, статус код: {response.status_code}")

def get_sp500_stocks() -> dict:
    """
    функция делает запрос к MOEX API для получения данных о котировках
    """
    url = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        stock_data = []
        for item in data["securities"]["data"]:
            stock_name = item[2]
            stock_price = item[3]
            stock_data.append({"name": stock_name, "price": stock_price})
        logging.info('Данные акций успешно получены.')
        return stock_data
    else:
        logging.error('API запрос не удался')
        raise Exception(f"API запрос не удался")

def calculate_expenses_transfers(df: pd.DataFrame, start_date: str, end_date: str) -> dict:
    """
    Функция принимает датафрейм и возвращает общую сумму расходов, сортирует расходы по разделам: Раздел «Основные»,
    в котором траты по категориям отсортированы по убыванию. Данные предоставляются по 7 категориям с наибольшими
    тратами, траты по остальным категориям суммируются и попадают в категорию «Остальное»,
    Раздел «Переводы и наличные», в котором сумма по категориям «Наличные» и «Переводы» отсортирована по убыванию.
    """
    # Фильтрация данных по "Дата платежа"
    logging.info("Начало расчета расходов и переводов")
    filtered_df = df[(df["Дата платежа"] >= start_date) & (df["Дата платежа"] <= end_date) & (df["Сумма операции"] < 0)]

    total_expenses = abs(int(filtered_df["Сумма операции"].sum()))
    logging.info(f"Общая сумма расходов: {total_expenses}")

    categories = filtered_df.groupby("Категория")["Сумма операции"].sum().sort_values(ascending=False)
    top_categories = categories.head(7)
    other_expenses = categories[7:].sum()

    main_categories = [{"category": cat, "amount": abs(int(amount))} for cat, amount in top_categories.items()]
    main_categories.append({"category": "Остальное", "amount": abs(int(other_expenses))})

    transfers_and_cash = filtered_df[filtered_df["Категория"].isin(["Переводы", "Наличные"])]
    transfers_and_cash_summary = transfers_and_cash.groupby("Категория")["Сумма операции"].sum().sort_values(ascending=False)
    transfers_and_cash_data = [{"category": cat, "amount": abs(int(amount))} for cat, amount in transfers_and_cash_summary.items()]

    logging.info("Завершение расчета расходов и переводов")
    return {"expenses": {
        "total_amount": total_expenses,
        "main": main_categories
    },
        "transfers_and_cash": transfers_and_cash_data
    }

def calculate_incomes(df: pd.DataFrame, start_date: str, end_date: str) -> dict:
    """Функция подсчитывает общую сумму поступлений и группирует категории с поступлениями в раздел
    «Основные», в котором поступления по категориям отсортированы по убыванию."""
    logging.info("Начало расчета поступлений")
    filtered_df = df[(df["Дата платежа"] >= start_date) & (df["Дата платежа"] <= end_date) & (df["Сумма операции"] > 0)]

    total_income = int(filtered_df["Сумма операции"].sum())
    logging.info(f"Общая сумма поступлений: {total_income}")

    income_categories = filtered_df.groupby("Категория")["Сумма операции"].sum().sort_values(ascending=False)
    main_income_categories = [{"category": cat, "amount": int(amount)} for cat, amount in income_categories.items()]

    logging.info("Завершение расчета поступлений")
    return {
        "total_amount": total_income,
        "main": main_income_categories
    }

