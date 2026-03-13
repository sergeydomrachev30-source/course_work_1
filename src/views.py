import json
import logging
from datetime import datetime, timedelta
from src.utils import say_hello, load_excel_data, process_card_data, get_top_5_transactions, get_currency_rate, \
    get_sp500_stocks, calculate_expenses_transfers, calculate_incomes
from src.config import api_key

#загруженный DataFrame с данными транзакций
#transaction_df = load_excel_data('../data/operations.xlsx')

def main_page_function(date_time_str:str)->dict:
    """
    Функция принимает на вход строку с датой и временем в формате YYYY-MM-DD HH:MM:SS
    и возвращающую JSON-ответ со следующими данными: приветствие, по каждой карте: последние 4 цифры карты,
    общая сумма расходов, кешбэк (1 рубль на каждые 100 рублей), топ-5 транзакций по сумме платежа, курс валют,
    стоимость акций из S&P500
    """
    # Получаем приветствие
    transaction_df = load_excel_data('../data/operations.xlsx')
    greeting = say_hello()

    # Обрабатываем данные по картам
    cards_data = []
    for card_number in transaction_df["Номер карты"].unique():
        card_data = transaction_df[transaction_df["Номер карты"] == card_number]
        if not card_data.empty:  # Проверка на пустоту данных
            last_four, total_spent, cashback = process_card_data(card_data)
            cards_data.append({
                "last_digits": last_four,
                "total_spent": total_spent,
                "cashback": cashback
            })
        else:
            logging.warning(f'Нет данных для карты номер {card_number}.')

    # Получаем топ-5 транзакций
    top_5_transactions = get_top_5_transactions(transaction_df)
    transactions_data  = top_5_transactions.to_dict(orient='records')

    # Получаем курсы валют
    currency_rates = get_currency_rate(api_key=api_key)["rates"]
    currency_data = [{"currency": key, "rate": round(value, 2)} for key, value in currency_rates.items()]
    #print("Курсы валют (внутри функции):", currency_data)
    # Получаем стоимость акций
    stock_data = get_sp500_stocks()

    response = {
        "greeting": greeting,
        "cards": cards_data,
        "top_transactions": transactions_data,
        "currency_data": currency_data,
        "stock_prices": stock_data
            }
    return response

response_to_main = main_page_function("2021-12-21 12:00:00")
print(json.dumps(response_to_main, ensure_ascii=False, indent=2))

def events_page_function(date_str:str, range_type:str = "M")->dict:
    """
    Функция принимает на вход строку с датой и второй необязательный параметр — диапазон данных.
    Возвращаемый JSON-ответ содержит следующие данные: общая сумма расходов и категории трат
    по убыванию, сумма по категориям «Наличные» и «Переводы», общая сумма поступлений, курс валют,
    стоимость акций из S&P 500.
    """
    transaction_df = load_excel_data('../data/operations.xlsx')
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    if range_type == 'W':
        start_date = date_obj - timedelta(days=date_obj.weekday())
        end_date = start_date + timedelta(days=6)
    elif range_type == 'M':
        start_date = date_obj.replace(day=1)
        end_date = date_obj
    elif range_type == 'Y':
        start_date = date_obj.replace(month=1, day=1)
        end_date = date_obj
    elif range_type == 'ALL':
        start_date = '2018-01-01'
        end_date = date_obj
    else:
        raise ValueError("Некорректный диапазон данных")

    start_date_str = start_date.strftime('%d.%m.%Y')
    end_date_str = end_date.strftime('%d.%m.%Y')

    result = calculate_expenses_transfers(transaction_df, start_date_str, end_date_str)
    expenses_data = result["expenses"]
    transfers_and_cash_data = result["transfers_and_cash"]
    incomes_data = calculate_incomes(transaction_df, start_date_str, end_date_str)
    currency_rates = get_currency_rate(api_key=api_key)["rates"]
    currency_data = [{"currency": key, "rate": value} for key, value in currency_rates.items()]
    stock_data = get_sp500_stocks()

    response = {
        "expenses": {"date_range": {"start": start_date_str, "end": end_date_str}, **expenses_data},
        "transfers_and_cash": transfers_and_cash_data,
        "income": incomes_data,
        "currency_data": currency_data,
        "stock_prices": stock_data
    }
    return response

response_to_events = events_page_function("2021-01-21", "M")
print(json.dumps(response_to_events, ensure_ascii=False, indent=2))

