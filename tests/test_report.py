# from datetime import datetime

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
    # Проверяем "супермаркеты" (с маленькой буквы)
    result = spending_by_category(sample_transactions, "супермаркеты", "10.12.2021")

    # Должно быть 3 записи (01.12, 03.12 и 05.12)
    # Запись от 2020 года не должна попасть
    assert len(result) == 3
    assert all(result["Категория"].str.lower() == "супермаркеты")


def test_spending_by_weekday(sample_transactions):
    """Тест средних трат по дням недели и индексации 1-7."""
    result = spending_by_weekday(sample_transactions, "10.12.2021")

    # Проверяем, что индекс начинается с 1
    assert result.index[0] == 1
    # Проверяем наличие конкретного дня (например, Суббота)
    assert "Суббота" in result["День недели"].values
    # Значения должны быть положительными (abs)
    assert result["Сумма платежа"].iloc[0] > 0


def test_spending_by_workday(sample_transactions):
    """Тест разделения на рабочие/выходные и расчет среднего."""
    result = spending_by_workday(sample_transactions, "10.12.2021")

    # Рабочие дни (01, 02, 03 дек): среднее от (1000, 2000, 3000) = 2000
    # Выходные дни (04, 05 дек): среднее от (5000, 5000) = 5000

    workday_val = result.loc[result["Тип дня"] == "Рабочий", "Средние траты"].values[0]
    weekend_val = result.loc[result["Тип дня"] == "Выходной", "Средние траты"].values[0]

    assert workday_val == 2000.0
    assert weekend_val == 5000.0


def test_empty_result_on_wrong_date(sample_transactions):
    """Тест на отсутствие данных в периоде."""
    result = spending_by_workday(sample_transactions, "01.01.2025")
    assert result.empty or len(result) == 0
