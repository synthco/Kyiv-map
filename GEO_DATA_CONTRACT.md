# GEO_DATA_CONTRACT for `KYV`

## Summary
- Контракт геоданих описує повний конвеєр `raw -> normalized -> generated -> served`, а не тільки фінальні runtime-файли гри.
- Канонічний runtime-контракт для Subway Builder: місто `KYV` читає `buildings_index.json.gz`, `demand_data.json.gz`, `roads.geojson.gz`, `runways_taxiways.geojson.gz` через `api.cities.setCityDataFiles('KYV', ...)`, а тайли через `api.map.setTileURLOverride(...)`.
- Базова одиниця попиту — агрегований `demand point`; `pops` генеруються з нього.
- Усі нормалізовані, згенеровані й сервовані геодані мають бути в `EPSG:4326` з координатами строго у форматі `[longitude, latitude]`.

## Contract

### 1. Spatial Rules
- Для всіх нормалізованих і фінальних артефактів використовувати `EPSG:4326`.
- Порядок bbox всюди один: `[minLon, minLat, maxLon, maxLat]`.
- Production extent має бути одним безперервним регіоном, який гарантовано включає Київ, Бориспіль, Бровари, Вишгород і транспортні коридори між ними.
- Для v1 production extent формується як прямокутний bbox, а не як кастомний polygon.
- У `generated/` і served шарах не використовувати локальні CRS, Web Mercator координати або `[lat, lon]`.

### 1.1 Canonical Production BBox
- Канонічний bbox для першого production extent `KYV`:
  - `[30.095930481829672, 50.24450228086875, 31.03257386656265, 50.6325759924907]`
- Джерело: надана користувачем діагональ bbox, інтерпретована як:
  - south-west corner: `50.24450228086875, 30.095930481829672`
  - north-east corner: `50.6325759924907, 31.03257386656265`
- Для внутрішніх і зовнішніх контрактів ця діагональ надалі використовується тільки в нормалізованому bbox-форматі `[minLon, minLat, maxLon, maxLat]`.

### 1.2 Target Settlement Set
- Перший-pass settlement set для production extent формується за наданим референсом мапи.
- Обов'язково включити:
  - Київ
  - Вишгород
  - Нові Петрівці
  - Осещина
  - Новосілки
  - Пухівка
  - Зазим'я
  - Погреби
  - Бровари
  - Калинівка
  - Квітневе
  - Княжичі
  - Дударків
  - Проліски
  - Щасливе
  - Чубинське
  - Гора
  - Бориспіль
  - Гнідин
  - Вишеньки
  - Хотів
  - Лісники
  - Петропавлівська Борщагівка
  - Софіївська Борщагівка
  - Вишневе
  - Крюківщина
  - Боярка
  - Білогородка
  - Бобриця
  - Гореничі
  - Стоянка
  - Коцюбинське
  - Ірпінь
  - Буча
  - Гостомель
  - Горенка
- Ці населені пункти вважаються мінімальним inclusion set і не можуть випадати з bbox без окремого рішення в `CONTINUITY.md`.

### 2. Directory and Stage Contract
- `data-src/` містить тільки сирі зовнішні джерела: `.osm.pbf`, raw `.geojson`, `.csv`, `.parquet`, metadata про джерело.
- `build/` містить нормалізовані проміжні артефакти, придатні для повторного ETL: обрізаний extent, нормалізовані дороги, будівлі, аеропортові шари, точки попиту.
- `generated/` містить game-ready артефакти до сервінгу:
  - `generated/city-data/demand_data.json.gz`
  - `generated/city-data/buildings_index.json.gz`
  - `generated/city-data/roads.geojson.gz`
  - `generated/city-data/runways_taxiways.geojson.gz`
- Served layout має бути стабільним:
  - `/kyv/data/buildings_index.json.gz`
  - `/kyv/data/demand_data.json.gz`
  - `/kyv/data/roads.geojson.gz`
  - `/kyv/data/runways_taxiways.geojson.gz`
  - `/kyv/tiles/{z}/{x}/{y}.mvt`
  - `/kyv/foundation/{z}/{x}/{y}.mvt`

### 3. File-Level Contract

#### `demand_data.json.gz`
- JSON object з ключами `points` і `pops`.
- `points[]`: `{ id, location, jobs, residents, popIds }`.
- `location`: `[lon, lat]`.
- `jobs` і `residents`: невід’ємні числа.
- `popIds`: масив id, які реально існують у `pops`.
- `pops[]`: `{ id, size, residenceId, jobId, drivingSeconds, drivingDistance, drivingPath? }`.
- `residenceId` і `jobId` мають посилатись на існуючі `points.id`.
- `size`, `drivingSeconds`, `drivingDistance` мають бути додатними.
- `drivingPath`, якщо присутній, це масив координат `[lon, lat]`.

#### `buildings_index.json.gz`
- Використовувати оптимізований формат, сумісний з `OptimizedBuildingIndexSchema`.
- Корінь: `{ cs, bbox, grid, cells, buildings, stats }`.
- `bbox`: `[minLon, minLat, maxLon, maxLat]`.
- `grid`: `[cols, rows]`.
- `buildings[]`: `{ b, f, p }`.
- `b`: bbox будівлі.
- `f`: foundation depth, число, як правило від’ємне або нуль.
- `p`: полігон будівлі як масив `[lon, lat]`.

#### `roads.geojson.gz`
- GeoJSON `FeatureCollection` у WGS84.
- Геометрія: дорожній граф регіону без негеографічних transform-ів; допустимі `LineString` або `MultiLineString`.
- Кожен feature має `properties` щонайменше з `roadClass`, `structure`, `name`.
- `roadClass` і `structure` нормалізуються до стабільного словника значень на етапі ETL; сирі OSM-теги напряму в served contract не виносяться.

#### `runways_taxiways.geojson.gz`
- GeoJSON `FeatureCollection` у WGS84.
- Містить інфраструктуру аеропорту Бориспіль, потрібну для game schema.
- Формат фіксується як schema-driven: фінальний файл має проходити runtime schema validation без додаткових runtime transform-ів.

#### `tiles`
- Vector tiles `.mvt`, узгоджені з extent `KYV`.
- Шари мають бути стабільними між білдівми; якщо layer names не збігаються з очікуванням гри, це виправляється або в ETL, або явно через `setLayerOverride`.

### 4. Normalized Intermediate Contract
- Нормалізовані будівлі, дороги, аеропортові шари й точки попиту в `build/` мають уже бути в `EPSG:4326`.
- Усі normalized entities мають мати стабільні string id.
- Для `demand points` required shape:
  - `id`
  - `coords`
  - `jobs`
  - `residents`
  - `source_refs`
  - `cluster_type`
- `jobs` і `residents` у normalized шарі можуть бути дробовими під час агрегації, але перед генерацією `demand_data.json.gz` мають бути приведені до цілих значень.
- `source_refs` зберігає provenance, але не потрапляє у served files.

## Public Interfaces / Types
- Runtime читає тільки такі артефакти:
  - `api.cities.setCityDataFiles('KYV', {...})` для `buildingsIndex`, `demandData`, `roads`, `runwaysTaxiways`
  - `api.map.setTileURLOverride({...})` для tile URLs
- Канонічні локальні type contracts:
  - `DemandDataFile`
  - `OptimizedBuildingsIndex`
  - `RoadProperties`
- Валідація має спиратися на runtime-exposed schemas:
  - `DemandDataSchema`
  - `OptimizedBuildingIndexSchema`
  - `RoadsGeojsonSchema`
  - runway schema key треба перевіряти проти фактично доступного runtime API, бо в документації й локальних типах є розбіжність імені: `RunwaysTaxiwaysSchema` vs `RunwaysTaxiwaysGeojsonSchema`

## Test Plan
- Координатний тест: усі normalized/generated/served координати проходять перевірку на `[-180..180, -90..90]` і порядок `[lon, lat]`.
- Gzip test: усі чотири served data files існують у `.gz` і коректно розпаковуються без зміни payload.
- Referential integrity test для `demand_data`:
  - кожен `pop.residenceId` існує в `points`
  - кожен `pop.jobId` існує в `points`
  - кожен `points.popIds[]` існує в `pops`
- Schema validation test:
  - `DemandDataSchema`
  - `OptimizedBuildingIndexSchema`
  - `RoadsGeojsonSchema`
  - runway schema key, який реально існує в runtime
- Extent consistency test: `buildings`, `roads`, `runways`, `demand points` лежать в одному `KYV` extent і не містять features далеко поза регіоном.
- Runtime smoke test: `src/main.ts` може читати served URLs без додаткових runtime transform-ів.

## Assumptions
- Цей документ є канонічним контрактом геоданих; `plan.md` і `CONTINUITY.md` посилаються на нього.
- Для v1 лишається локальний HTTP serving на `127.0.0.1`.
- `demand points` є єдиною базовою одиницею попиту; grid і прямі building-centroid flows не використовуються як канонічний served format.
- Словник значень для `roadClass` і `structure` буде нормалізований в ETL; сирі OSM values не вважаються фінальним контрактом.
- Точний production extent `KYV` ще треба окремо затвердити, але сам формат bbox і CRS вже зафіксований цим контрактом.
