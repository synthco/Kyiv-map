# CONTINUITY

## Decisions
- 2026-04-15: Tile generation tool: tippecanoe (brew install tippecanoe). MVT tiles генеруються в build/serve/kyv/tiles/ і build/serve/kyv/foundation/ через scripts/build_tiles.sh.
- 2026-04-15: Source-layer names у MVT: transportation, building, aeroway, water (main tiles); building_depth (foundation tiles).
- 2026-04-15: HTTP serving stack: python3 -m http.server 8080 (stdlib, без додаткових залежностей). Точка входу: scripts/serve.sh.
- 2026-04-15: Tile export Python deps: geopandas, pyarrow, pyogrio, shapely (pip3 install, системний python3).
- 2026-04-15: Foundation tile source layer named building_depth; якщо game layer ID building-depth не збігається — додати setLayerOverride в src/main.ts після першого smoke test.
- 2026-04-15: src/main.ts (worktree) синхронізовано з root index.js: додано CITY_DATA_BASE_URL, loadRuntimeJson, summarizeSchemaError, validateRuntimeSchemas, idempotent getCities() check.
- 2026-04-13: Проєкт переведено на шаблон `synthco/Kyiv-map` замість ручної структури `manifest.json + index.js`.
- 2026-04-13: Канонічне джерело API-рішень — тільки Subway Builder Docs v1.0.0.
- 2026-04-13: Scope v1 обмежено playable картою і валідними даними для `KYV`.
- 2026-04-13: Доставка assets у v1 локальна, через `127.0.0.1`, без hosted distribution.
- 2026-04-13: Прийняті ідентифікатори `com.ivantyshchenko.kyiv-city`, `Kyiv Metropolitan Area`, `KYV`.
- 2026-04-13: Канонічний формат геоданих винесено в окремий `GEO_DATA_CONTRACT.md`.
- 2026-04-13: Базова одиниця попиту за контрактом — clustered demand point.
- 2026-04-13: За наданим картографічним референсом зафіксовано перший-pass settlement inclusion set для `KYV`; він внесений у `GEO_DATA_CONTRACT.md` і є мінімально обов'язковим покриттям extent.
- 2026-04-13: Форма першого production extent для `KYV` зафіксована як прямокутний bbox, не polygon.
- 2026-04-13: Канонічний production bbox для `KYV` зафіксовано як `[30.095930481829672, 50.24450228086875, 31.03257386656265, 50.6325759924907]`.
- 2026-04-13: Python geodata pipeline реалізується окремо від TypeScript runtime і використовує локальний `.venv` + `requirements.txt`.
- 2026-04-13: OSM reader для Python ETL замінено з `pyrosm` на `pyosmium`.
- 2026-04-13: Для v1 `residents` у demand pipeline беруться з `WorldPop Ukraine 2025 100m`, а `jobs` будуються через OSM-inference.
- 2026-04-13: Канонічна demand-clustering resolution для v1 — grid `700m x 700m` у `EPSG:3857`.
- 2026-04-13: `build_demand_data.py` переведено з nearest-job логіки на gravity-based hub selection з route cache.
- 2026-04-13: Runtime schema key для runway data підтверджено як `RunwaysTaxiwaysGeojsonSchema`.
- 2026-04-13: Для runtime schema validation у моді використовується `fetch + DecompressionStream`, бо `api.utils.loadCityData()` у поточній збірці Subway Builder падає всередині internal helper до HTTP-запиту.
- 2026-04-13: Оскільки workspace уже лежить у системній папці модів, у корені репозиторію додано symlink `index.js -> dist/index.js`, щоб `manifest.json` з `main: "index.js"` був виконуваним без окремого symlink на `dist/`.

## Open Questions
- Який локальний стек буде основним для tiles/data serving: tileserver-gl, PMTiles, кастомний HTTP чи інший інструмент.
- Які відкриті джерела будуть канонічними для jobs/residents allocation по Київському регіону.
- Чи потрібен окремий routing service override для локального OSRM endpoint, чи достатньо стандартного game-side query flow.
- Чи буде потрібен `mapImageUrl` або thumbnail для city picker у наступній ітерації.
- Яка точна причина runtime-невідповідності `OptimizedBuildingIndexSchema` для `buildings_index.json.gz`; поточний summary обрізається через дуже велику кількість issues.

## Blocked Items
- Локальне середовище поки не має `pnpm`, тому build/typecheck не можна прогнати до встановлення інструменту.
- 2026-04-13: Блокер з `pnpm` знято після `corepack pnpm install`; геодані й tile serving лишаються активними блокерами для playable карти.
- 2026-04-15: Блокер з tippecanoe/osmium знято (brew install tippecanoe osmium-tool). Tile serving знято (scripts/build_tiles.sh + scripts/serve.sh створено).
- 2026-04-15 ВІДКРИТО: Runtime підтвердження, що building_depth source-layer у foundation tiles збігається з очікуваним game layer ID; якщо ні — потрібен setLayerOverride.
- 2026-04-15 ВІДКРИТО: OSRM routing override — osrm-routed binary не встановлений; якщо гра потребує локального routing для KYV, потрібен окремий крок.
- 2026-04-15 ПІДТВЕРДЖЕНО: Tile build відпрацював успішно. 6603 main tiles + 4369 foundation tiles у build/serve/kyv/. HTTP server верифіковано: всі 4 data files → 200, tiles/9/299/172.mvt → 200, foundation/9/299/172.mvt → 200. KYV tile coords при z=9: x=299, y=172.
- 2026-04-13: `pyrosm`/`pyrobuf` blocker закрито; `osmium` успішно встановився в `.venv`, а roads/runways/buildings extraction відпрацювали на реальному `.osm.pbf`.
- 2026-04-13: `demand_data.json.gz` згенеровано, але runtime schema validation ще не проходить для `buildings_index.json.gz`, `roads.geojson.gz` і `runways_taxiways.geojson.gz`; це активний data blocker перед playable-використанням.
- 2026-04-13: `roads.geojson.gz` не відповідає runtime schema через значення `roadClass` поза дозволеним набором `highway|major|medium|minor`.
- 2026-04-13: `runways_taxiways.geojson.gz` не відповідає runtime schema, бо гра очікує `Polygon` geometry замість поточного line-like output.
- 2026-04-13: `buildings_index.json.gz` не проходить runtime schema validation; точну форму невідповідності ще треба локалізувати окремим debug pass.
- 2026-04-13: Локальний tile/foundation serving для `127.0.0.1:8080/kyv` ще не реалізовано як постійний dev stack; для runtime validation використовувався тимчасовий static server лише для `/kyv/data`.

## Data Sources Register
- OSM / GeoFabrik Ukraine: базова геометрія будівель, доріг, landuse, аеропортової інфраструктури. Статус: локальний `.osm.pbf` додано в `data-src/osm/ukraine-260412.osm.pbf`, використовується Python ETL.
- Open data для population/jobs: джерела ще не зафіксовані. Статус: відкрите питання.
- WorldPop Ukraine 2025 100m: джерело для `residents` у demand pipeline. Статус: канонічне джерело, файл локально підключений і використаний для `demand_seed.csv`.
- OSRM: локальний розрахунок `drivingSeconds` і `drivingDistance`. Статус: Docker-based OSRM pipeline відпрацьовано на `ukraine-260412.osm.pbf`; `demand_data.json.gz` згенеровано через локальний endpoint на `127.0.0.1:5001`.

## Validation Findings
- 2026-04-13: Локальний runtime `src/main.ts` оновлено під `KYV`, але schema validation для city data ще не реалізована.
- 2026-04-13: `pnpm typecheck` і `pnpm build` ще не запускались через відсутній `pnpm` в середовищі.
- 2026-04-13: `corepack pnpm typecheck` пройшов успішно без TypeScript помилок.
- 2026-04-13: `corepack pnpm build` пройшов успішно; `dist/index.js` згенеровано, `manifest.json` скопійовано в `dist/`.
- 2026-04-13: `corepack pnpm dev:link` перевірено поза sandbox; у поточному workspace скрипт завершується як коректний no-op, бо репозиторій уже лежить у цільовій папці модів.
- 2026-04-13: У локальних типах виявлено розбіжність naming для runway schema: `RunwaysTaxiwaysGeojsonSchema`; у документації раніше фігурувало `RunwaysTaxiwaysSchema`.
- 2026-04-13: Створено `.venv` для Python pipeline.
- 2026-04-13: `python -m compileall scripts/python` пройшов успішно.
- 2026-04-13: `fetch_sources.py --help`, `extract_bbox.py --help`, `validate_city_data.py --help` працюють через `.venv/bin/python`.
- 2026-04-13: Python ETL extraction scripts переведені на shared `osm_reader.py` adapter поверх `pyosmium`.
- 2026-04-13: `pip install -r requirements.txt` пройшов успішно після заміни `pyrosm` на пакет `osmium` (`pyosmium`).
- 2026-04-13: Імпорт `osmium`, `geopandas`, `pyogrio`, `shapely` через `.venv/bin/python` пройшов успішно.
- 2026-04-13: `build_roads.py` успішно згенерував `build/roads.normalized.parquet` і `generated/city-data/roads.geojson.gz`; summary: `scanned=2552926 accepted=2552926 skipped=0 invalid_geometry=0 final_count=179628`.
- 2026-04-13: `build_runways.py` успішно згенерував `build/runways_taxiways.normalized.parquet` і `generated/city-data/runways_taxiways.geojson.gz`; summary: `scanned=9522 accepted=3333 skipped=6189 invalid_geometry=0 final_count=252`.
- 2026-04-13: `build_buildings.py` успішно згенерував `build/buildings.normalized.parquet` і `generated/city-data/buildings_index.json.gz`; summary: `scanned=7479826 accepted=7479820 skipped=0 invalid_geometry=6 final_count=235691`.
- 2026-04-13: Додано `build_demand_seed.py`; він генерує `demand_seed.csv` з `WorldPop` + OSM, робить jobs calibration, airport bonus і road snapping.
- 2026-04-13: `build_demand_data.py` тепер вимагає non-empty `pops`, використовує gravity-based hub selection і кешує OSRM маршрути в `build/demand_route_cache.json`.
- 2026-04-13: `build_demand_seed.py` успішно згенерував `data-src/open-data/demand_seed.csv` з `8121` retained demand points.
- 2026-04-13: `build_demand_points.py` успішно згенерував `build/demand_points.parquet`.
- 2026-04-13: `build_demand_data.py` успішно згенерував `generated/city-data/demand_data.json.gz`; runtime payload містить `8121` points і `8036` pops.
- 2026-04-13: `validate_city_data.py --strict` пройшов успішно; локальний validation report записано в `build/validation/city_data_validation.json`.
- 2026-04-13: Runtime schema validation у Subway Builder пройшла для `demand_data.json.gz`.
- 2026-04-13: Runtime schema validation у Subway Builder не пройшла для `roads.geojson.gz`; перша помилка: `roadClass` очікує одне зі значень `highway|major|medium|minor`.
- 2026-04-13: Runtime schema validation у Subway Builder не пройшла для `runways_taxiways.geojson.gz`; перша помилка: `geometry.type` очікує `Polygon`.
- 2026-04-13: Runtime schema validation у Subway Builder не пройшла для `buildings_index.json.gz`; поточний summary обрізається як `Invalid string length`, тому потрібен окремий debug pass з компактнішим schema-error report.
- 2026-04-13: У поточній game build `api.utils.loadCityData()` падає з `Failed to fetch dynamically imported module: .../helpers/loadData`; mod runtime validation переведено на власний `fetch + DecompressionStream`.

## Repo Deviations From Template
- Template metadata в `manifest.json` і `package.json` замінені на Kyiv-specific значення.
- Demo runtime у `src/main.ts` замінено на city registration/runtime configuration.
- Додані `plan.md`, `CONTINUITY.md`, `AGENTS.md`.
- Додано `GEO_DATA_CONTRACT.md` як канонічний контракт ETL і served geodata.
- Додані директорії `data-src/`, `build/`, `generated/` під geodata pipeline.
- Додано Python ETL layer: `requirements.txt`, `scripts/python/`, `.venv` workflow і Python-specific `.gitignore` правила.
- Додано demand-seed generation layer поверх `WorldPop` + OSM inference.
- Demo `src/ui/ExamplePanel.tsx` підлягає видаленню після завершення cleanup.
- 2026-04-13: `src/ui/ExamplePanel.tsx` видалено; шаблонний demo UI повністю прибрано з робочого дерева.
- 2026-04-13: `scripts/link.ts` доповнено обробкою сценарію, коли workspace вже знаходиться в системній папці модів і symlink не потрібен.
- 2026-04-13: У корені репозиторію створено symlink `index.js -> dist/index.js`, щоб поточний workspace layout у папці модів був сумісний з `manifest.json`.

## Next Session Start
- Встановити Python GIS deps системно: `pip3 install geopandas pyarrow pyogrio shapely`.
- Запустити `bash scripts/build_tiles.sh` — перевірити, що .mvt файли з'явились у build/serve/kyv/tiles/ і build/serve/kyv/foundation/.
- Запустити `bash scripts/serve.sh` і переконатись, що curl повертає 200 для всіх 4 data файлів і MVT tile.
- Запустити гру і виконати smoke test sequence (Settings > Mods, city picker, console logs).
- За результатами smoke test: підтвердити або виправити source-layer names (building_depth vs building-depth, transportation vs roads).
- Закрити open question по RunwaysTaxiwaysGeojsonSchema key через перший runtime запуск.
- Вирішити питання `roadClass` mapping (поточні значення з ETL vs очікуваний game vocabulary highway|major|medium|minor).
