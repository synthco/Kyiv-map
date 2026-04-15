# AGENTS

## Project
- Це TypeScript/Vite мод для Subway Builder, побудований із шаблону `synthco/Kyiv-map`.
- Ціль проєкту: додати playable карту `Kyiv Metropolitan Area` з кодом міста `KYV`.
- Поточний scope v1: карта, city runtime, локальні тайли і city data, базова валідація.
- Канонічний формат геоданих і стадій ETL визначається `GEO_DATA_CONTRACT.md`.

## Operating Rules
- Перед запуском гри завжди запускати `bash scripts/serve.sh` в окремому терміналі.
- Після зміни геоданих або ETL — перебудовувати тайли через `bash scripts/build_tiles.sh`.
- Використовувати тільки Subway Builder Docs v1.0.0 як джерело рішень по API.
- Використовувати `pnpm` як обов'язковий пакетний менеджер і основний шлях запуску скриптів.
- Для Python geodata pipeline використовувати локальний `.venv` і `requirements.txt`.
- OSM PBF у Python pipeline читати через `pyosmium`, а не через `pyrosm`.
- Demand pipeline у v1 будується з `WorldPop 2025` для `residents` і OSM-inference для `jobs`.
- Runtime entrypoint тільки `src/main.ts`.
- `dist/` є generated output; не редагувати файли в `dist/` вручну.
- Будь-які нові питання, блокери, джерела даних, припущення або validation findings спочатку додавати в `CONTINUITY.md`.
- Усі ETL і served geodata артефакти мають відповідати `GEO_DATA_CONTRACT.md`.
- Demo UI з шаблону не повертати без окремої задачі.
- Перед кожним meaningful checkpoint потрібно проганяти `pnpm typecheck`; перед локальним використанням моду також проганяти `pnpm build`.

## Tile & Serve Pipeline
- Tile generation entry: `bash scripts/build_tiles.sh` (requires: brew install tippecanoe osmium-tool)
- Tile source export deps: `pip3 install geopandas pyarrow pyogrio shapely` (системний python3)
- Tile source script: `scripts/python/build_tile_sources.py` → виводить GeoJSON у build/tile-sources/
- Main tiles output: `build/serve/kyv/tiles/{z}/{x}/{y}.mvt` (source layers: transportation, building, aeroway, water)
- Foundation tiles output: `build/serve/kyv/foundation/{z}/{x}/{y}.mvt` (source layer: building_depth)
- City data: `build/serve/kyv/data/*.json.gz / *.geojson.gz` (вже присутні, копіюються при першому запуску ETL)
- HTTP server: `bash scripts/serve.sh` → python3 -m http.server 8080 --bind 127.0.0.1 --directory build/serve
- Serve URL base: `http://127.0.0.1:8080/kyv/...`
- Якщо source-layer names не збігаються з очікуванням гри → додати `api.map.setLayerOverride(...)` у `src/main.ts` і зафіксувати в `CONTINUITY.md`.

## Folder Responsibilities
- `src/`: runtime код моду і будь-які підтримувальні модулі для Subway Builder API.
- `src/types/`: локальні типи API v1.0.0; використовувати як type contract, не дублювати їх вручну в іншому місці.
- `scripts/`: dev tooling, game launcher, link management, ETL/validation automation.
- `scripts/python/`: Python ETL, source fetching, clipping, normalization, gzip serialization, validation.
- `data-src/`: сирі OSM/open-data джерела.
- `build/`: проміжні артефакти обробки геоданих.
- `generated/`: згенеровані city-data артефакти перед сервінгом або пакуванням.
- `dist/`: фінальна збірка моду для symlink у папку модів гри.
- `GEO_DATA_CONTRACT.md`: канонічний контракт для raw, normalized, generated і served геоданих.

## Runtime Expectations
- `src/main.ts` має реєструвати `KYV`, tile URL override і city data URLs.
- Runtime має бути idempotent і не дублювати реєстрації після hot reload.
- Не додавати місії, tweet/newspaper templates або декоративні UI-панелі у v1 без окремого рішення по scope.

## Working Agreement
- Якщо виявлено розходження між шаблоном і документацією, фіксувати це в `CONTINUITY.md` перед зміною реалізації.
- Якщо ETL або runtime потребує нового поля чи нового артефакту, спочатку оновлювати `GEO_DATA_CONTRACT.md`, а вже потім код.
- Якщо бракує локального інструменту або зовнішнього джерела даних, блокер записується в `CONTINUITY.md` з чітким наступним кроком.
- Усі нові scripts для data pipeline мають бути відокремлені від runtime логіки моду.
