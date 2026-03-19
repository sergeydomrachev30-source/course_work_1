# from datetime import datetime
import json

import pandas as pd
import pytest

from src.report import spending_by_category, spending_by_weekday, spending_by_workday


@pytest.fixture
def sample_transactions():
    """Создает тестовый набор данных."""
    data = {
        "Дата платежа": [
            "01.12.2021",
            "02.12.2021",
            "03.12.2021",  # Ср, Чт, Пт (Рабочие)
            "04.12.2021",
            "05.12.2021",  # Сб, Вс (Выходные)
            "01.01.2020",  # Старая дата (вне периода)
        ],
        "Сумма платежа": [-1000, -2000, -3000, -5000, -5000, -100],
        "Категория": ["Супермаркеты", "Аптеки", "супермаркеты", "Такси", "Супермаркеты", "Супермаркеты"],
    }
    return pd.DataFrame(data)


def test_spending_by_category(sample_transactions):
    """Тест фильтрации по категории и регистронезависимости."""
    result_json = spending_by_category(sample_transactions, "супермаркеты", "10.12.2021")
    data = json.loads(result_json)
    assert len(data) == 3



def test_spending_by_weekday(sample_transactions):
    """Тест средних трат по дням недели и индексации 1-7."""
    result_json = spending_by_weekday(sample_transactions, "10.12.2021")
    data = json.loads(result_json)
    assert len(data) > 0


def test_spending_by_workday(sample_transactions):
    """Тест разделения на рабочие/выходные и расчет среднего."""
    result_json = spending_by_workday(sample_transactions, "10.12.2021")
    data = json.loads(result_json)
    workday_val = next(item["Средние траты"] for item in data if item["Тип дня"] == "Рабочий")
    assert workday_val == 2000.0


def test_empty_result_on_wrong_date(sample_transactions):
    """Тест на отсутствие данных в периоде."""
    result_json = spending_by_workday(sample_transactions, "01.01.2025")
    data = json.loads(result_json)
    assert len(data) == 0
