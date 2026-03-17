import json
import logging
import os

from src.report import spending_by_category, spending_by_weekday, spending_by_workday
from src.services import find_person_transfers, find_phone_transactions, investment_bank
from src.utils import load_excel_data
from src.views import events_page_function, main_page_function

logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
log_file_path = os.path.join(logs_dir, "app.log")

if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file_path, mode="w", encoding="utf-8")],
)


def main() -> None:
    """
    Единая точка входа для запуска всех функциональностей проекта.
    """
    test_date = "2021-12-31"
    transaction_file = "../data/operations.xlsx"

    print(f"Старт полного анализа данных для {test_date}")

    try:
        df = load_excel_data(transaction_file)
        if df.empty:
            raise ValueError("Файл пуст")
        print("Данные из Excel успешно загружены.")
    except Exception as e:
        logging.error(f"Критическая ошибка загрузки данных: {e}")
        print("Ошибка загрузки файла. Дальнейший анализ невозможен.")
        return

    print("Анализ интерфейсов (Views)")
    try:
        main_data = main_page_function(f"{test_date} 12:00:00")
        events_data = events_page_function(test_date, range_type="M")
        print(f"Страницы сформированы. Приветствие: {main_data.get('greeting')}")
    except Exception as e:
        logging.error(f"Ошибка в модуле Views: {e}")
        main_data, events_data = {}, {}
        print("Ошибка при формировании страниц.")

    print("Генерация аналитических отчетов (Reports)")
    try:
        spending_by_category(df, "Супермаркеты", test_date)
        spending_by_weekday(df, test_date)
        spending_by_workday(df, test_date)
        print("JSON-отчеты успешно сгенерированы в корне проекта.")
    except Exception as e:
        logging.error(f"Ошибка в модуле Reports: {e}")
        print("⚠️ Часть отчетов не была создана.")

    print("Запуск сервисов поиска и накоплений (Services)")
    try:

        dict_data = df.to_dict(orient="records")
        savings = investment_bank(test_date[:7], dict_data, limit=50)

        phone_res = json.loads(find_phone_transactions(df))
        person_res = json.loads(find_person_transfers(df))

        print(f"Накоплено в инвесткопилке: {savings} ₽")
        print(f"Поиск: найдено {len(phone_res)} телефонов и {len(person_res)} личных переводов.")
    except Exception as e:
        logging.error(f"Ошибка в модуле Services: {e}")
        savings = 0
        print("Ошибка в работе поисковых сервисов.")

    final_output = {"сводка_панели": main_data, "отчет_за_месяц": events_data, "общий_инвестиционный_итог": savings}
    try:
        with open("full_project_analysis.json", "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
        print("Полный свод сохранен в 'full_project_analysis.json'")
    except Exception as e:
        logging.error(f"Ошибка сохранения финального JSON: {e}")

    print("Работа программы завершена.")


if __name__ == "__main__":
    main()
