# AGENTS

## Project
- Це TypeScript/Vite мод для Subway Builder, побудований із шаблону `synthco/Kyiv-map`.
- Ціль проєкту: додати playable карту `Kyiv Metropolitan Area` з кодом міста `KYV`.
- Поточний scope v1: карта, city runtime, локальні тайли і city data, базова валідація.
- Канонічний формат геоданих і стадій ETL визначається `GEO_DATA_CONTRACT.md`.

## Operating Rules
- Використовувати тільки Subway Builder Docs v1.0.0 як джерело рішень по API.
- Використовувати `pnpm` як обов'язковий пакетний менеджер і основний шлях запуску скриптів.
- Runtime entrypoint тільки `src/main.ts`.
- `dist/` є generated output; не редагувати файли в `dist/` вручну.
- Будь-які нові питання, блокери, джерела даних, припущення або validation findings спочатку додавати в `CONTINUITY.md`.
- Усі ETL і served geodata артефакти мають відповідати `GEO_DATA_CONTRACT.md`.
- Demo UI з шаблону не повертати без окремої задачі.
- Перед кожним meaningful checkpoint потрібно проганяти `pnpm typecheck`; перед локальним використанням моду також проганяти `pnpm build`.

## Folder Responsibilities
- `src/`: runtime код моду і будь-які підтримувальні модулі для Subway Builder API.
- `src/types/`: локальні типи API v1.0.0; використовувати як type contract, не дублювати їх вручну в іншому місці.
- `scripts/`: dev tooling, game launcher, link management, ETL/validation automation.
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
