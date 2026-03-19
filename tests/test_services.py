import json
from unittest.mock import patch

import pandas as pd
import pytest

from src.services import (find_person_transfers, find_phone_transactions, get_profitable_categories, investment_bank,
                          search_transactions)


@patch("src.utils.load_excel_data")
def test_get_profitable_categories(mock_load_excel_data):
    # Подготовка данных
    mock_data = pd.DataFrame(
        {
            "Дата платежа": ["01.06.2019", "15.06.2019", "20.06.2019"],
            "Категория": ["Ж/д билеты", "Транспорт", "Транспорт"],
            "Сумма платежа": [-500, -1000, -1500],
            "Кэшбэк": [50, 20, 30],
        }
    )
    mock_load_excel_data.return_value = mock_data
    expected_result = {"Транспорт": 50, "Ж/д билеты": 50}
    result = get_profitable_categories(mock_data, year=2019, month=6)
    assert json.loads(result) == expected_result


@pytest.fixture
def transactions_data():
    return [
        {"Дата операции": "2024-03-10", "Сумма операции": -1712},  # Март (+38 при лимите 50)
        {"Дата операции": "2024-03-15", "Сумма операции": -250},  # Март (+50 при лимите 50)
        {"Дата операции": "2024-02-01", "Сумма операции": -100},  # Февраль (игнор)
        {"Дата операции": "2024-03-20", "Сумма операции": 5000},  # Доход (игнор)
        {"Дата операции": "2024-03-25", "Сумма операции": -42},  # Март (+8 при лимите 50)
    ]


def test_investment_bank_march(transactions_data):
    """Проверяем расчет за март с лимитом 50"""
    result = investment_bank("2024-03", transactions_data, 50)
    assert result == 96.0


def test_investment_bank_february(transactions_data):
    """Проверяем расчет за февраль с лимитом 100"""
    result = investment_bank("2024-02", transactions_data, 100)
    assert result == 100.0


def test_investment_bank_different_limit(transactions_data):
    """Проверяем тот же март, но с лимитом 10"""
    result = investment_bank("2024-03", transactions_data, 10)
    assert result == 26.0


def test_empty_month(transactions_data):
    """Проверяем месяц, в котором не было трат"""
    result = investment_bank("2024-01", transactions_data, 50)
    assert result == 0.0


def test_investment_bank_standard_50():
    """Тест стандартного округления с шагом 50"""
    transactions = [
        {"Дата операции": "2024-03-10", "Сумма операции": -1712},
        {"Дата операции": "2024-03-15", "Сумма операции": -250},
    ]
    assert investment_bank("2024-03", transactions, 50) == 88.0


def test_investment_bank_limit_10():
    """Тест округления с шагом 10"""
    transactions = [
        {"Дата операции": "2024-03-10", "Сумма операции": -101},
    ]
    assert investment_bank("2024-03", transactions, 10) == 9.0


def test_investment_bank_different_months():
    """Тест игнорирования транзакций другого месяца"""
    transactions = [
        {"Дата операции": "2024-03-10", "Сумма операции": -1712},
        {"Дата операции": "2024-02-15", "Сумма операции": -500},
        {"Дата операции": "2023-03-10", "Сумма операции": -100},
    ]
    assert investment_bank("2024-03", transactions, 50) == 38.0


def test_investment_bank_income_ignored():
    """Тест: доходы (положительные суммы) не должны округляться"""
    transactions = [
        {"Дата операции": "2024-03-10", "Сумма операции": 5000},
    ]
    assert investment_bank("2024-03", transactions, 50) == 0.0


def test_investment_bank_invalid_data():
    """Тест устойчивости к ошибкам в данных"""
    transactions = [
        {"Дата операции": "2024-03-10", "Сумма операции": "много"},
        {"Дата операции": "не дата", "Сумма операции": -100},
        {"Сумма операции": -100},
    ]
    assert investment_bank("2024-03", transactions, 50) == 0.0


def test_investment_bank_wrong_month_format():
    """Тест: если сам аргумент месяца передан неверно"""
    transactions = [{"Дата операции": "2024-03-10", "Сумма операции": -100}]
    assert investment_bank("март", transactions, 50) == 0.0


@pytest.fixture
def sample_data():
    data = [
        {"id": 1, "Описание": "Купил кофе", "Категория": "Еда"},
        {"id": 2, "Описание": "Оплата интернета", "Категория": "Связь"},
        {"id": 3, "Описание": "Завтрак в кафе", "Категория": "Еда"},
    ]
    return pd.DataFrame(data)


def test_search_found(sample_data):
    result = json.loads(search_transactions("кофе", sample_data))
    assert len(result) == 1
    assert result[0]["id"] == 1


def test_search_category(sample_data):
    result = json.loads(search_transactions("Еда", sample_data))
    assert len(result) == 2


def test_search_no_results(sample_data):
    result = json.loads(search_transactions("авто", sample_data))
    assert len(result) == 0


@pytest.fixture
def sample_df():
    """Создает тестовый DataFrame с разными случаями."""
    data = {
        "Описание": [
            "Оплата связи +7 921 111-22-33",  # Стандартный плюс
            "Перевод 89001112233",  # Без разделителей через 8
            "Тинькофф Мобайл +7(995)555-55-55",  # Со скобками
            "Просто покупка в магазине",  # Без номера
            None,  # Пустая ячейка
        ],
        "Сумма": [-100, -200, -300, -500, 0],
    }
    return pd.DataFrame(data)


def test_find_phone_transactions_success(sample_df):
    """Проверяем, что функция находит все 3 корректных номера."""
    result_json = find_phone_transactions(sample_df)
    result_data = json.loads(result_json)

    # Должно найти 3 строки
    assert len(result_data) == 3
    # Проверяем, что конкретные номера попали в результат
    descriptions = [item["Описание"] for item in result_data]
    assert "89001112233" in descriptions[1]
    assert "+7(995)555-55-55" in descriptions[2]


def test_find_phone_transactions_empty():
    """Проверяем поведение, если в таблице нет номеров."""
    df = pd.DataFrame({"Описание": ["Магазин", "Такси"], "Сумма": [10, 20]})
    result = find_phone_transactions(df)
    assert json.loads(result) == []


def test_find_phone_transactions_no_column():
    """Проверяем случай, когда в DataFrame нет колонки 'Описание'."""
    df = pd.DataFrame({"Data": [1, 2, 3]})
    result = find_phone_transactions(df)
    assert json.loads(result) == []


def test_find_phone_transactions_invalid_input():
    """Проверяем обработку критической ошибки (передача не DataFrame)."""
    result = find_phone_transactions(None)  # Передаем None вместо таблицы
    assert json.loads(result) == []


@pytest.fixture
def transfer_data():
    return pd.DataFrame(
        {
            "Описание": ["Валерий А.", "Сергей З.", "Оплата в магазине", "Перевод в банк"],
            "Категория": ["Переводы", "Переводы", "Еда", "Переводы"],
        }
    )


def test_find_person_transfers_success(transfer_data):
    result = find_person_transfers(transfer_data)
    data = json.loads(result)

    # Должно найти Валерия и Сергея
    assert len(data) == 2
    assert "Валерий А." in [item["Описание"] for item in data]


def test_find_person_transfers_no_results():
    df = pd.DataFrame({"Описание": ["Пополнение"], "Категория": ["Переводы"]})
    result = find_person_transfers(df)
    assert json.loads(result) == []
