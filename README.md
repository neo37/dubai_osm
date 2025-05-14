# Dubai Housing Export — README

| 📑 **Меню** | **English**          | **العربية**      | **Русский**                     |
| ----------- | -------------------- | ---------------- | ------------------------------- |
| 1           | Quick start          | البدء السريع     | Быстрый старт                   |
| 2           | Requirements         | المتطلبات        | Требования                      |
| 3           | Installation         | التثبيت          | Установка                       |
| 4           | Parameters           | المعلمات         | Параметры                       |
| 5           | What the script does | كيف يعمل السكربت | Что делает скрипт               |
| 6           | Output files         | ملفات الإخراج    | Выходные файлы                  |
| 7           | Customisation        | التخصيص          | Настройка                       |
| 8           | Performance notes    | ملاحظات الأداء   | Замечания по производительности |
| 9           | Troubleshooting      | استكشاف الأخطاء  | Поиск проблем                   |
| 10          | License              | الرخصة           | Лицензия                        |

---

## 1 · Quick start | البدء السريع | Быстрый старт

```bash
# 1 — создайте и активируйте виртуальное окружение
python -m venv venv && source venv/bin/activate

# 2 — установите зависимости
pip install --upgrade osmnx geopandas pandas shapely pyproj openpyxl

# 3 — запустите
python dubai_housing_export.py
```

Запуск скрипта загрузит из OpenStreetMap **все жилые здания Дубая, у которых есть адрес**,
распределит их по районам/муниципалитету, выведет в консоль и сохранит в `dubai_housing_details.xlsx`.

---

## 2 · Requirements | المتطلبات | Требования

| Пакет                                     | Минимальная версия | Назначение                               |
| ----------------------------------------- | ------------------ | ---------------------------------------- |
| Python                                    | 3.9+               | интерпретатор                            |
| [OSMnx](https://github.com/gboeing/osmnx) | 2.1                | запросы к Overpass / обработка геометрии |
| GeoPandas                                 | 0.14               | пространственные DataFrame‑ы и join‑ы    |
| Shapely 2                                 | 2.0                | гео‑операции                             |
| pandas                                    | 2.2                | табличные данные / Excel export          |
| pyproj                                    | 3.6                | проекции CRS                             |
| openpyxl                                  | 3.1                | запись XLSX                              |

> **Tip:** На Windows easiest — установить [OSGeo4W‑shell](https://trac.osgeo.org/osgeo4w/) или WSL/Ubuntu.

---

## 3 · Installation | التثبيت | Установка

1. **Система GIS‑зависимостей**: `apt install gdal-bin libspatialindex-dev`, иначе GeoPandas может не собраться.
2. Виртуальное окружение (см. Quick start).
3. `pip install` зависимостей.
4. Сохраните `dubai_housing_export.py` в любой каталог и запустите.

---

## 4 · Parameters | المعلمات | Параметры

Все переменные находятся в блоке **CONFIG** в начале скрипта.

| Переменная      | Что делает                                                           | Значение по умолчанию                          |
| --------------- | -------------------------------------------------------------------- | ---------------------------------------------- |
| `GRID_N`        | Разбивает bounding box на `N × N` тайлов → столько Overpass‑запросов | `6` ⇒ 36 запросов                              |
| `BUILDING_TAGS` | Какие здания запрашивать                                             | `residential`, `apartments`, `house`           |
| `ADDR_COLS`     | Какие теги считать «адресом»                                         | `addr:housenumber`, `addr:street`, `addr:full` |
| `TARGET_COLS`   | Порядок/состав столбцов в Excel                                      | см. скрипт                                     |
| `OUT_XLSX`      | Имя выходного файла                                                  | `dubai_housing_details.xlsx`                   |

---

## 5 · What the script does | كيف يعمل السكربت | Что делает скрипт

1. **Бокс Дубая** — берётся административный полигон уровня 8, считается bbox.
2. **Сетка** — bbox разбивается на `GRID_N×GRID_N` тайлов.
3. **Запрос** — для каждого тайла выполняется `ox.features_from_bbox(bbox, BUILDING_TAGS)`.
4. **Фильтр адреса** — остаются только элементы, имеющие *любой* `ADDR_COLS`‑тег.
5. **Spatial join** — каждому зданию присваивается:

   * район (*district*, admin\_level 10),
   * муниципалитет (*municipality*, admin\_level 8).
6. **Консоль** — весь DataFrame тайла печатается, чтобы видеть «сырой» результат.
7. **Excel** — DataFrame дописывается в лист `Housing`.
8. В конце выводится итоговое число сохранённых строк.

---

## 6 · Output files | ملفات الإخراج | Выходные файлы

* **`dubai_housing_details.xlsx`** — одна таблица «Housing». Каждый ряд —
  одно здание, у которого *обязательно есть* адрес.

| Пример столбцов                                      | Описание             |
| ---------------------------------------------------- | -------------------- |
| `osmid`                                              | ID объекта в OSM     |
| `name`                                               | Название (если есть) |
| `addr:housenumber` / `addr:street` / `addr:postcode` | Адрес                |
| `district`                                           | Район / community    |
| `municipality`                                       | Dubai                |
| `levels` / `height`                                  | Этажность / высота   |

---

## 7 · Customisation | التخصيص | Настройка

* **Запрос других типов зданий** — добавьте значения в `BUILDING_TAGS`.
* **Увеличить детализацию** — `GRID_N = 8` → 64 маленьких запросов (медленнее, но надёжнее при тайм‑аутах).
* **CSV вместо Excel**:

  ```python
  df.to_csv("dubai_housing_details.csv", mode="a",
            header=not Path("dubai_housing_details.csv").exists(),
            index=False)
  ```
* **GeoPackage** для GIS‑ПО:

  ```python
  df.to_file("dubai_housing.gpkg", layer="housing", driver="GPKG",
             mode="a", index=False)
  ```

---

## 8 · Performance notes | ملاحظات الأداء | Замечания по производительности

* Overpass ограничивает площадь одного запроса ⇒ скрипт делит регион на тайлы.
* Если Overpass всё‑таки рвёт соединение — увеличьте `GRID_N` (меньше bbox → меньше данных на запрос).
* GeoPandas + Shapely 2 достаточно быстры, но при сотнях тысяч объектов
  spatial join может занять пару минут.
* Excel‑запись потоковая, поэтому память практически не растёт.

---

## 9 · Troubleshooting | استكشاف الأخطاء | Поиск проблем

| Симптом                                       | Причина / лечение                                             |
| --------------------------------------------- | ------------------------------------------------------------- |
| `No matching features`                        | В конкретном тайле нет зданий с адресом — норма.              |
| `features_from_bbox() timeout`                | Overpass перегружен: увеличьте `GRID_N` или попробуйте позже. |
| `right_df should be GeoDataFrame`             | Изменена логика join: обновите скрипт (v ≥ 2025‑05‑14).       |
| `UserWarning: area is X times max query area` | OSMnx сам разобьёт запрос — просто подождите.                 |

---

## 10 · License | الرخصة | Лицензия

MIT License © 2025 Your Name.
Основано на данных © OpenStreetMap contributors (ODbL).
