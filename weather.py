from dataclasses import dataclass 
import sys
import json
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor



NUM_WORKERS = 5


@dataclass
class WeatherData:
    city: str
    temperature: float
    country: str


def load_cities(file_path: str) -> List[str]:
    """Загружает список уникальных городов из текстового файла."""
    unique_cities = []
    seen = set()

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            city = line.strip()
            if city and city.lower() not in seen:
                seen.add(city.lower())
                unique_cities.append(city)

    return unique_cities


def fetch_weather_data(city: str) -> Optional[WeatherData]:
    """Получает данные о погоде через API wttr.in для указанного города."""
    url = f"https://wttr.in/{city}?format=j1"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

            current_condition = payload["current_condition"][0]
            temp_c = float(current_condition["temp_C"])

            nearest_area = payload["nearest_area"][0]
            country = nearest_area["country"][0]["value"]

            return WeatherData(city=city, temperature=temp_c, country=country)
    except (urllib.error.URLError, KeyError, ValueError, IndexError) as err:
        print(f"Не удалось получить данные для города '{city}': {err}")
        return None

def fetch_all_weather(cities: List[str]) -> List[WeatherData]:
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        results = executor.map(fetch_weather_data, cities)

    return [data for data in results if data is not None]

def format_temperature(temp: float) -> str:
    """Форматирует температуру с подстановкой знака '+' для положительных значений."""
    rounded_temp = round(temp)
    return f"+{rounded_temp}" if rounded_temp > 0 else f"{rounded_temp}"


def print_weather_list(weather_records: List[WeatherData]) -> None:
    """Выводит список погоды по каждому городу."""
    print("--- Информация по городам ---")
    for record in weather_records:
        temp_str = format_temperature(record.temperature)
        print(f"{record.city}, {record.country} {temp_str} °C")

def get_country_stats(weather_records: List[WeatherData]) -> Dict[str, Dict[str, Any]]:
    """Группирует данные по странам и возвращает словарь со статистикой."""
    country_groups: Dict[str, List[float]] = {}
    for record in weather_records:
        country_groups.setdefault(record.country, []).append(record.temperature)

    stats = {}
    for country, temps in country_groups.items():
        count = len(temps)
        stats[country] = {
            "city_count": count,
            "avg_temperature": round(sum(temps) / count, 1),
            "min_temperature": round(min(temps), 1),
            "max_temperature": round(max(temps), 1)
        }
    return stats


def print_country_stats(stats: Dict[str, Dict[str, Any]]) -> None:
    """Выводит агрегированную статистику по странам в консоль."""
    print("\n--- Статистика по странам ---")
    for country, data in stats.items():
        count = data["city_count"]
        avg_str = format_temperature(data["avg_temperature"])
        min_str = format_temperature(data["min_temperature"])
        max_str = format_temperature(data["max_temperature"])

        cities_label = "city" if count == 1 else "cities"
        print(
            f"{country} - {count} {cities_label}, "
            f"avg: {avg_str} °C, "
            f"min: {min_str} °C, "
            f"max: {max_str} °C"
        )


def save_stats_to_json(stats: Dict[str, Dict[str, Any]], output_file: str = "country_stats.json") -> None:
    """Сохраняет статистику по странам в JSON-файл."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)
    print(f"Статистика успешно сохранена в '{output_file}'")

def main() -> None:
    if len(sys.argv) < 2:
        print("Ошибка: не указан путь к файлу.")
        print("Использование: python script.py <путь_к_файлу>")
        return

    file_path = sys.argv[1]

    try:
        cities = load_cities(file_path)
    except FileNotFoundError:
        print(f"Ошибка: файл '{file_path}' не найден.")
        return

    weather_records = fetch_all_weather(cities)

    if not weather_records:
        print("Не удалось загрузить данные ни по одному городу.")
        return

    print_weather_list(weather_records)

    stats = get_country_stats(weather_records)
    print_country_stats(stats)

    # Вопрос о сохранении статистики
    answer = input("\nСохранить статистику по странам в json файл? (да/нет): ").strip().lower()
    if answer in ("да", "yes", "y", "d"):
        save_stats_to_json(stats)



if __name__ == "__main__":
    main()
