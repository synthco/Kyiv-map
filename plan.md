# Kyiv Metropolitan Area Mod Plan

## Project Context
- Проєкт базується на шаблоні [`synthco/Kyiv-map`](https://github.com/synthco/Kyiv-map) і використовує TypeScript/Vite workflow для Subway Builder Modding API v1.0.0.
- Робочий цикл репозиторію: `pnpm build` збирає мод у `dist/`, `pnpm dev:link` лінкує `dist/` у папку модів гри, `pnpm dev` запускає watcher і гру з логами, `pnpm typecheck` перевіряє типи.
- Канонічні джерела рішень по API: тільки офіційна документація Subway Builder v1.0.0, насамперед `Custom Cities Guide`, `Development Tools`, `First Mod`, `Electron Setup`, `Lifecycle Hooks`, `Type Reference`.
- Канонічний контракт геоданих для ETL і runtime зафіксовано в `GEO_DATA_CONTRACT.md`.
- Scope v1: один playable city-pack `KYV` для регіону Kyiv Metropolitan Area без місій, flavor-контенту та необов'язкового UI.

## Repository Baseline
- `manifest.json`: метадані моду для менеджера модів гри; копіюється в `dist/`.
- `package.json`: `pnpm`-first workflow, скрипти `build`, `dev`, `dev:link`, `dev:unlink`, `typecheck`.
- `src/main.ts`: єдиний runtime entrypoint моду; збирається в `dist/index.js` як IIFE.
- `src/types/`: локальні типи Modding API v1.0.0; використовувати як type contract для runtime і tooling.
- `scripts/run.ts`: локальний запуск Subway Builder з логами в `debug/latest.log`.
- `scripts/link.ts`: symlink `dist/` у системну папку модів.
- `vite.config.ts`: збірка entrypoint у `dist/index.js` і копіювання `manifest.json`.
- `data-src/`: сирі OSM/open-data джерела.
- `build/`: проміжні ETL-артефакти і результати підготовки даних.
- `generated/`: згенеровані city-data артефакти перед пакуванням або сервінгом.
- `dist/`: тільки фінальний mod output для Subway Builder, без ручних правок.
- `GEO_DATA_CONTRACT.md`: канонічний контракт для `raw -> normalized -> generated -> served` артефактів.

## Implementation Phases

### 1. Template Cleanup
- Замінити template metadata у `manifest.json` і `package.json` на значення проєкту Kyiv.
- Переписати `src/main.ts` з demo runtime на city runtime для `KYV`.
- Видалити demo UI-компонент `src/ui/ExamplePanel.tsx` і не залишати декоративного UI в v1.

### 2. City Runtime
- Залишити entrypoint у `src/main.ts`.
- Реєструвати місто `KYV` через `window.SubwayBuilderAPI.registerCity(...)`.
- Підключати локальний tiles endpoint через `api.map.setTileURLOverride(...)`.
- Підключати city data URLs через `api.cities.setCityDataFiles('KYV', ...)`.
- Додавати лише documented runtime настройки: без кастомних місій, новин, tweet templates і діагностичного UI.

### 3. Geodata ETL
- Завантажити сирі OSM/open-data в `data-src/`.
- Зафіксувати прямокутний bbox extent `[30.095930481829672, 50.24450228086875, 31.03257386656265, 50.6325759924907]`.
- Використовувати settlement inclusion set з `GEO_DATA_CONTRACT.md` як нижню межу покриття для першого production extent.
- Підготувати геометрію будівель, доріг, landuse і аеропортової інфраструктури згідно з `GEO_DATA_CONTRACT.md`.

### 4. Demand Model
- Побудувати `demand_data.json.gz` на базі реальних open-data + OSM.
- Рознести `jobs` і `residents` по clustered demand points з явною фіксацією джерел і припущень.
- Рахувати `drivingSeconds` і `drivingDistance` через локальний OSRM.

### 5. Tile Serving
- Згенерувати векторні тайли для dev/runtime.
- Підняти локальний HTTP endpoint для тайлів і gzip-даних.
- Перевірити відповідність source layer names очікуванням гри; override-и додавати тільки за потреби.

### 6. Validation
- Ганяти `pnpm typecheck` для TypeScript шару.
- Валідовувати `demand_data`, `buildings_index`, `roads`, `runways_taxiways` через documented schemas і вимоги `GEO_DATA_CONTRACT.md`.
- Записувати всі schema mismatch та runtime issues в `CONTINUITY.md`.

### 7. Playtesting
- Smoke test включення моду в `Settings > Mods`.
- Smoke test появи `KYV` у списку міст і коректного `initialViewState`.
- Smoke test побудови станцій і треків у Києві, біля Борисполя, Броварів та Вишгорода.

### 8. Local Packaging
- Збирати мод через `pnpm build`.
- Підключати мод у гру через `pnpm dev:link`, а не ручним копіюванням.
- Вважати v1 local-dev/local-use only, доки окремо не буде спроєктовано hosted або packaged asset delivery.

## Per-phase Deliverables
- `Template Cleanup`: оновлені `manifest.json`, `package.json`, `src/main.ts`; прибраний demo UI.
- `City Runtime`: runtime реєструє `KYV` і знає URL-и тайлів та city data.
- `Geodata ETL`: сирі джерела в `data-src/`, зафіксований bbox, підготовлені проміжні файли в `build/`.
- `Demand Model`: валідний або близький до валідного `demand_data.json.gz` у `generated/`, побудований з clustered demand points.
- `Tile Serving`: локальний endpoint віддає tiles і gzip-дані, runtime може їх читати.
- `Validation`: задокументовані результати `typecheck`, schema validation і runtime smoke tests.
- `Playtesting`: зафіксовані сценарії відтворення і знайдені проблеми.
- `Local Packaging`: `dist/` придатний для symlink у Subway Builder mods folder.

## Definition of Done
- Мод з'являється в Subway Builder і вмикається без критичних помилок.
- Місто `KYV` доступне в city picker і відкривається з коректним стартовим видом на Київський регіон.
- Runtime читає локальні тайли та city data з `127.0.0.1`.
- `DemandDataSchema`, `OptimizedBuildingIndexSchema`, `RoadsGeojsonSchema`, `RunwaysTaxiwaysSchema` проходять або мають задокументовані відхилення.
- Усі generated і served геодані відповідають `GEO_DATA_CONTRACT.md`.
- `pnpm typecheck` і `pnpm build` проходять.
- Усі нові питання, блокери, джерела даних і результати перевірок зафіксовані в `CONTINUITY.md`.
