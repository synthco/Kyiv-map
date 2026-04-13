# CONTINUITY

## Decisions
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

## Open Questions
- Який локальний стек буде основним для tiles/data serving: tileserver-gl, PMTiles, кастомний HTTP чи інший інструмент.
- Які відкриті джерела будуть канонічними для jobs/residents allocation по Київському регіону.
- Чи потрібен окремий routing service override для локального OSRM endpoint, чи достатньо стандартного game-side query flow.
- Чи буде потрібен `mapImageUrl` або thumbnail для city picker у наступній ітерації.
- Який фактичний runtime key існує для валідації runway файлу: `RunwaysTaxiwaysSchema` чи `RunwaysTaxiwaysGeojsonSchema`.

## Blocked Items
- В репозиторії ще немає сирих геоданих, demand data pipeline або локального tile server.
- Локальне середовище поки не має `pnpm`, тому build/typecheck не можна прогнати до встановлення інструменту.
- 2026-04-13: Блокер з `pnpm` знято після `corepack pnpm install`; геодані й tile serving лишаються активними блокерами для playable карти.

## Data Sources Register
- OSM / GeoFabrik Ukraine: базова геометрія будівель, доріг, landuse, аеропортової інфраструктури. Статус: заплановано.
- Open data для population/jobs: джерела ще не зафіксовані. Статус: відкрите питання.
- OSRM: локальний розрахунок `drivingSeconds` і `drivingDistance`. Статус: заплановано.

## Validation Findings
- 2026-04-13: Локальний runtime `src/main.ts` оновлено під `KYV`, але schema validation для city data ще не реалізована.
- 2026-04-13: `pnpm typecheck` і `pnpm build` ще не запускались через відсутній `pnpm` в середовищі.
- 2026-04-13: `corepack pnpm typecheck` пройшов успішно без TypeScript помилок.
- 2026-04-13: `corepack pnpm build` пройшов успішно; `dist/index.js` згенеровано, `manifest.json` скопійовано в `dist/`.
- 2026-04-13: `corepack pnpm dev:link` перевірено поза sandbox; у поточному workspace скрипт завершується як коректний no-op, бо репозиторій уже лежить у цільовій папці модів.
- 2026-04-13: У локальних типах виявлено розбіжність naming для runway schema: `RunwaysTaxiwaysGeojsonSchema`; у документації раніше фігурувало `RunwaysTaxiwaysSchema`.

## Repo Deviations From Template
- Template metadata в `manifest.json` і `package.json` замінені на Kyiv-specific значення.
- Demo runtime у `src/main.ts` замінено на city registration/runtime configuration.
- Додані `plan.md`, `CONTINUITY.md`, `AGENTS.md`.
- Додано `GEO_DATA_CONTRACT.md` як канонічний контракт ETL і served geodata.
- Додані директорії `data-src/`, `build/`, `generated/` під geodata pipeline.
- Demo `src/ui/ExamplePanel.tsx` підлягає видаленню після завершення cleanup.
- 2026-04-13: `src/ui/ExamplePanel.tsx` видалено; шаблонний demo UI повністю прибрано з робочого дерева.
- 2026-04-13: `scripts/link.ts` доповнено обробкою сценарію, коли workspace вже знаходиться в системній папці модів і symlink не потрібен.

## Next Session Start
- Використати затверджений bbox `KYV` у першому ETL scaffold і cropping pipeline.
- Додати перші scripts для ETL або хоча б каркас валідації city data.
- Перенести фактичні результати `typecheck`/`build` у release checklist після появи data pipeline.
- Підготувати локальний tile/data serving stack для `127.0.0.1`.
- Перевірити runtime schema key для runway validation і зафіксувати його в ETL tooling.
