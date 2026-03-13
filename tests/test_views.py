import pytest
from unittest.mock import patch
import pandas as pd
from src.views import main_page_function
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)

# Фикстура для данных о транзакциях
@pytest.fixture
def transaction_data_fixture():
    return pd.DataFrame({
        'Номер карты': ['1234', '5678'],
        'Сумма операции': [1000.00, 2000.00],
        'Описание': ['Транзакция 1', 'Транзакция 2']
    })

@pytest.mark.parametrize("date_time_str, expected_greeting", [
    ('2021-12-21 06:00:00', "Доброе утро!"),
    ('2021-12-21 14:00:00', "Добрый день!"),
    ('2021-12-21 19:00:00', "Добрый вечер!"),
    ('2021-12-21 02:00:00', "Доброй ночи!")
])
@patch('src.utils.datetime')  # Путь к модулю datetime, где используется
@patch('src.views.load_excel_data')
@patch('src.utils.process_card_data')
@patch('src.utils.get_currency_rate')
@patch('src.utils.get_sp500_stocks')
@patch('src.utils.say_hello')
@patch('src.utils.get_top_5_transactions')
def test_main_page_function(mock_get_top_5_transactions, mock_say_hello,
                            mock_get_sp500_stocks, mock_get_currency_rate,
                            mock_process_card_data, mock_load_excel_data,
                            mock_datetime,  # Добавляем мок
                            transaction_data_fixture,
                            date_time_str, expected_greeting):
    # Установка времени для тестов
    mock_datetime.now.return_value = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')

    # Настройка моков
    mock_load_excel_data.return_value = transaction_data_fixture
    mock_say_hello.return_value = expected_greeting
    mock_get_top_5_transactions.return_value = transaction_data_fixture.head(5)
    mock_get_currency_rate.return_value = {"rates": {"USD": 74.0}}
    mock_get_sp500_stocks.return_value = [{"stock": "AAPL", "price": 150.12}]
    mock_process_card_data.return_value = ("1234", 1000.0, 10.0)

    result = main_page_function(date_time_str)

    # Выполнение проверок
    assert result['greeting'] == expected_greeting
    assert len(result['cards']) == len(transaction_data_fixture['Номер карты'].unique())
    assert len(result['top_transactions']) == 2  # в зависимости от данных фикстуры
    # Проверка курса валют для USD с округлением
    usd_rate = next((item['rate'] for item in result['currency_data'] if item['currency'] == 'USD'), None)
    assert round(usd_rate, 2) == 74.0
    assert result['stock_prices'][0]['price'] == 150.12