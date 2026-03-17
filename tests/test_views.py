from unittest.mock import patch

import pandas as pd
import pytest

from src.views import events_page_function, main_page_function


@pytest.fixture
def mock_df():
    """Общий DataFrame для тестов."""
    return pd.DataFrame(
        {
            "Дата платежа": ["20.12.2021", "21.12.2021"],
            "Номер карты": ["*1111", "*1111"],
            "Сумма операции": [-1500.0, 5000.0],
            "Категория": ["Супермаркеты", "Зарплата"],
            "Описание": ["Пятерочка", "Перевод"],
        }
    )


# Тест для Главной страницы
@patch("src.views.get_sp500_stocks")
@patch("src.views.get_currency_rate")
@patch("src.views.get_top_5_transactions")
@patch("src.views.process_card_data")
@patch("src.views.say_hello")
@patch("src.views.load_excel_data")
def test_main_page_function_integration(mock_load, mock_hello, mock_card, mock_top, mock_curr, mock_stocks, mock_df):
    # Настройка моков
    mock_load.return_value = mock_df
    mock_hello.return_value = "Добрый день"
    mock_card.return_value = ("1111", -1500.0, 15.0)
    mock_top.return_value = mock_df.head(1)
    mock_curr.return_value = {"rates": {"USD": 75.0}}
    mock_stocks.return_value = [{"name": "AAPL", "price": 150.0}]

    result = main_page_function("2021-12-21 12:00:00")

    assert result["greeting"] == "Добрый день"
    assert result["cards"][0]["last_digits"] == "1111"
    assert result["top_transactions"][0]["Описание"] == "Пятерочка"
    assert result["currency_data"][0]["currency"] == "USD"


# Тест для страницы Событий
@patch("src.views.get_sp500_stocks")
@patch("src.views.get_currency_rate")
@patch("src.views.calculate_incomes")
@patch("src.views.calculate_expenses_transfers")
@patch("src.views.load_excel_data")
def test_events_page_function_integration(mock_load, mock_exp, mock_inc, mock_curr, mock_stocks, mock_df):
    # Настройка моков
    mock_load.return_value = mock_df
    mock_exp.return_value = {"expenses": {"total_amount": 1500, "main": []}, "transfers_and_cash": []}
    mock_inc.return_value = {"total_amount": 5000, "main": []}
    mock_curr.return_value = {"rates": {"EUR": 85.0}}
    mock_stocks.return_value = [{"name": "MSFT", "price": 300.0}]

    # Тестируем диапазон 'M' (Месяц)
    result = events_page_function("2021-12-21", range_type="M")

    assert result["expenses"]["date_range"]["start"] == "01.12.2021"
    assert result["expenses"]["total_amount"] == 1500
    assert result["income"]["total_amount"] == 5000
    assert result["currency_data"][0]["currency"] == "EUR"
    assert result["stock_prices"][0]["name"] == "MSFT"


# Дополнительный тест на ошибку в Событиях
@patch("src.views.load_excel_data")
def test_events_page_invalid_range(mock_load):
    # Имитируем, что файл НЕ пустой, чтобы функция пошла дальше
    mock_load.return_value = pd.DataFrame({"Дата платежа": ["20.12.2021"], "Номер карты": ["*1111"]})

    with pytest.raises(ValueError, match="Некорректный диапазон данных"):
        events_page_function("2021-12-21", range_type="INVALID")


# 1. Тест на пустой файл (покрывает 'if transaction_df.empty')
@patch("src.views.load_excel_data")
def test_main_page_empty_file(mock_load):
    mock_load.return_value = pd.DataFrame()
    assert main_page_function("2021-12-21") == {}


# 2. Тест на отсутствие колонки 'Номер карты'
@patch("src.views.load_excel_data")
@patch("src.views.say_hello")
def test_main_page_no_card_column(mock_hello, mock_load):
    mock_load.return_value = pd.DataFrame({"Дата": ["2021-12-21"]})
    mock_hello.return_value = "Привет"
    result = main_page_function("2021-12-21 12:00:00")
    assert result["greeting"] == "Привет"
    assert result["cards"] == []


# 3. Тест на ошибки API (покрывает блоки 'except Exception')
@patch("src.views.get_sp500_stocks")
@patch("src.views.get_currency_rate")
@patch("src.views.get_top_5_transactions")
@patch("src.views.process_card_data")
@patch("src.views.load_excel_data")
def test_main_page_api_failure(mock_load, mock_card, mock_top, mock_curr, mock_stocks):
    mock_load.return_value = pd.DataFrame({"Номер карты": ["*1111"]})
    mock_card.return_value = ("1111", 0, 0)
    mock_top.return_value = pd.DataFrame()
    # Имитируем сбой API
    mock_curr.side_effect = Exception("API Down")
    mock_stocks.side_effect = Exception("MOEX Down")

    result = main_page_function("2021-12-21 12:00:00")
    assert result["currency_data"] == []
    assert result["stock_prices"] == []


# 4. Тесты на разные диапазоны дат (покрывает ветки 'W', 'Y', 'ALL')
@patch("src.views.calculate_incomes")
@patch("src.views.calculate_expenses_transfers")
@patch("src.views.load_excel_data")
@pytest.mark.parametrize(
    "range_type, expected_start",
    [
        ("W", "20.12.2021"),  # Понедельник недели для 21.12.2021
        ("Y", "01.01.2021"),  # Начало года
        ("ALL", "01.01.2018"),  # Константа из кода
    ],
)
def test_events_ranges(mock_load, mock_exp, mock_inc, range_type, expected_start):
    mock_load.return_value = pd.DataFrame({"Дата платежа": ["21.12.2021"], "Номер карты": ["*1"]})
    mock_exp.return_value = {"expenses": {}, "transfers_and_cash": []}
    mock_inc.return_value = {}

    result = events_page_function("2021-12-21", range_type=range_type)
    assert result["expenses"]["date_range"]["start"] == expected_start


# 5. Исправленный тест на некорректный диапазон
@patch("src.views.load_excel_data")
def test_events_invalid_range(mock_load):
    mock_load.return_value = pd.DataFrame({"Дата платежа": ["21.12.2021"]})
    with pytest.raises(ValueError, match="Некорректный диапазон данных"):
        events_page_function("2021-12-21", range_type="UNKNOWN")
