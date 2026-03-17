from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.utils import (calculate_expenses_transfers, calculate_incomes, get_currency_rate, get_sp500_stocks,
                       get_top_5_transactions, load_excel_data, process_card_data, say_hello)


@patch("pandas.read_excel")
def test_load_excel_data(mock_read_excel):
    mock_read_excel.return_value = pd.DataFrame({"data": [1, 2, 3]})
    result = load_excel_data("fake_path.xlsx")
    assert not result.empty, "DataFrame должен быть не пустым при успешной загрузке."
    assert result.equals(mock_read_excel.return_value)


@patch("pandas.read_excel")
def test_load_excel_data_file_not_found(mock_read_excel):
    mock_read_excel.side_effect = FileNotFoundError
    result = load_excel_data("fake_path.xlsx")
    assert result.empty, "DataFrame должен быть пустым, если файл не найден."


@patch("pandas.read_excel")
def test_load_excel_data_other_exception(mock_read_excel):
    mock_read_excel.side_effect = Exception("Some error")
    result = load_excel_data("fake_path.xlsx")
    assert result.empty, "DataFrame должен быть пустым при возникновении исключения."


@pytest.mark.parametrize(
    "hour,expected_greeting", [(6, "Доброе утро!"), (13, "Добрый день!"), (19, "Добрый вечер!"), (3, "Доброй ночи!")]
)
@patch("src.utils.datetime")
def test_say_hello(mock_datetime, hour, expected_greeting):
    mock_datetime.now.return_value = datetime(2023, 1, 1, hour, 0)
    assert say_hello() == expected_greeting


# Фикстура для данных о картах
@pytest.fixture
def card_data_fixture():
    return pd.DataFrame(
        {"Номер карты": ["*1234", "*5678"], "Сумма операции": [-1000, -2000]}  # Отрицательные значения для трат
    )


# Тест для функции process_card_data
@patch("src.utils.pd.read_excel")
def test_process_card_data(mock_read_excel, card_data_fixture):
    mock_read_excel.return_value = card_data_fixture
    result = process_card_data(mock_read_excel.return_value)
    assert result == ("1234", -3000.0, 30.0)  # Ожидаемое значение с учетом трат


def test_get_top_5_transactions(card_data_fixture):
    top_5 = get_top_5_transactions(card_data_fixture)
    assert len(top_5) <= 5


@patch("src.utils.pd.read_excel")
def test_get_top_5_transactions_with_mock(mock_read_excel):
    mock_read_excel.return_value = pd.DataFrame(
        {
            "Сумма операции": [300, 500, 400, 100, 200],
            "Описание": ["Транзакция1", "Транзакция2", "Транзакция3", "Транзакция4", "Транзакция5"],
        }
    )
    result = get_top_5_transactions(mock_read_excel.return_value)
    assert len(result) == 5
    assert result.iloc[0]["Сумма операции"] == 500


# Тест для функции get_currency_rate
@patch("src.utils.requests.get")
def test_get_currency_rate(mock_get):
    mock_response = mock_get.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {"rates": {"USD": 74.0}}
    result = get_currency_rate("dummy_key")
    assert result["rates"]["USD"] == 74.0


@pytest.fixture
def mock_response_data():
    return {"securities": {"data": [["ABRD", "TQBR", "АбрауДюрсо", 158.2], ["AFLT", "TQBR", "Аэрофлот", 51.8]]}}


@patch("requests.get")
def test_get_sp500_stocks(mock_get, mock_response_data):
    # Настройка mock объекта
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    mock_get.return_value = mock_response

    # Вызов тестируемой функции
    stocks = get_sp500_stocks()

    # Проверка результатов
    assert len(stocks) == 2
    assert stocks[0]["name"] == "АбрауДюрсо"
    assert stocks[0]["price"] == 158.2
    assert stocks[1]["name"] == "Аэрофлот"
    assert stocks[1]["price"] == 51.8


# Фикстура для данных о транзакциях с форматом даты DD.MM.YYYY
@pytest.fixture
def transaction_data_fixture():
    return pd.DataFrame(
        {
            "Дата платежа": ["01.01.2023", "15.01.2023", "20.01.2023"],
            "Категория": ["Переводы", "Наличные", "Пополнения"],
            "Сумма операции": [-1000, -500, 2000],
        }
    )


# Тест для функции calculate_expenses_transfers
@pytest.mark.parametrize(
    "start_date,end_date,expected_total",
    [
        ("01.01.2023", "31.01.2023", 1500),  # Изменён формат даты
    ],
)
def test_calculate_expenses_transfers(transaction_data_fixture, start_date, end_date, expected_total):
    # Преобразуем даты в нужный формат внутри теста
    transaction_data_fixture["Дата платежа"] = pd.to_datetime(
        transaction_data_fixture["Дата платежа"], format="%d.%m.%Y"
    )
    result = calculate_expenses_transfers(transaction_data_fixture, start_date, end_date)
    assert result["expenses"]["total_amount"] == expected_total


@pytest.fixture
def expense_data_fixture():
    return pd.DataFrame(
        {
            "Дата платежа": ["2023-01-01", "2023-01-15", "2023-01-20"],
            "Категория": ["Продукты", "Транспорт", "Переводы"],
            "Сумма операции": [-1000, -200, -500],
        }
    )


# Тест для функции calculate_incomes
@pytest.mark.parametrize(
    "start_date,end_date,expected_total",
    [
        ("01.01.2023", "31.01.2023", 2000),
    ],
)
def test_calculate_incomes(transaction_data_fixture, start_date, end_date, expected_total):
    # Преобразуем даты в нужный формат внутри теста
    transaction_data_fixture["Дата платежа"] = pd.to_datetime(
        transaction_data_fixture["Дата платежа"], format="%d.%m.%Y"
    )
    result = calculate_incomes(transaction_data_fixture, start_date, end_date)
    assert result["total_amount"] == expected_total
