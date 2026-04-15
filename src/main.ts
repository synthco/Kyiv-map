const MOD_ID = 'com.ivantyshchenko.kyiv-city';
const MOD_NAME = 'Kyiv Metropolitan Area';
const MOD_VERSION = '1.0.0';
const CITY_CODE = 'KYV';
const TAG = '[KyivCity]';

const LOCAL_ASSET_BASE_URL = 'http://127.0.0.1:8080/kyv';
const CITY_DATA_BASE_URL = `${LOCAL_ASSET_BASE_URL}/data`;

const api = window.SubwayBuilderAPI;

const CITY_CONFIG = {
  name: MOD_NAME,
  code: CITY_CODE,
  description:
    'Kyiv regional sandbox including Kyiv, Boryspil, Brovary, and Vyshhorod.',
  population: 4500000,
  initialViewState: {
    zoom: 9.8,
    latitude: 50.4501,
    longitude: 30.5234,
    bearing: 0,
  },
  minZoom: 7.5,
} as const;

let runtimeConfigured = false;
let runtimeValidationStarted = false;

function summarizeSchemaError(error: unknown): string {
  const candidate = error as {
    issues?: unknown[];
    errors?: unknown[];
    message?: string;
  };
  const issues = candidate?.issues ?? candidate?.errors ?? [];
  if (Array.isArray(issues)) {
    const firstIssue =
      issues.length > 0 ? JSON.stringify(issues[0]).slice(0, 300) : 'none';
    return `${issues.length} issue(s); first=${firstIssue}`;
  }
  return candidate?.message ?? String(error);
}

async function loadRuntimeJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status} for ${url}`);
  if (!url.endsWith('.gz')) return response.json();
  if (!response.body) throw new Error(`Missing response body for ${url}`);
  if (typeof DecompressionStream === 'undefined')
    throw new Error('DecompressionStream is unavailable in this runtime');
  const decompressedStream = response.body.pipeThrough(
    new DecompressionStream('gzip'),
  );
  const text = await new Response(decompressedStream).text();
  return JSON.parse(text);
}

function configureKyivCityRuntime() {
  if (runtimeConfigured) return;
  runtimeConfigured = true;

  if (!api.utils.getCities().find((city) => city.code === CITY_CODE)) {
    api.registerCity(CITY_CONFIG);
  }

  api.map.setTileURLOverride({
    cityCode: CITY_CODE,
    tilesUrl: `${LOCAL_ASSET_BASE_URL}/tiles/{z}/{x}/{y}.mvt`,
    foundationTilesUrl: `${LOCAL_ASSET_BASE_URL}/foundation/{z}/{x}/{y}.mvt`,
    maxZoom: 15,
  });

  api.cities.setCityDataFiles(CITY_CODE, {
    buildingsIndex: `${CITY_DATA_BASE_URL}/buildings_index.json.gz`,
    demandData: `${CITY_DATA_BASE_URL}/demand_data.json.gz`,
    roads: `${CITY_DATA_BASE_URL}/roads.geojson.gz`,
    runwaysTaxiways: `${CITY_DATA_BASE_URL}/runways_taxiways.geojson.gz`,
  });

  api.map.setDefaultLayerVisibility(CITY_CODE, {
    buildingFoundations: true,
    oceanFoundations: false,
  });

  console.log(
    `${TAG} Registered ${CITY_CODE} runtime against ${LOCAL_ASSET_BASE_URL}.`,
  );
}

async function validateRuntimeSchemas() {
  if (runtimeValidationStarted) return;
  runtimeValidationStarted = true;

  const checks: Array<{
    label: string;
    schemaKey: keyof typeof api.schemas;
    url: string;
  }> = [
    {
      label: 'demand_data',
      schemaKey: 'DemandDataSchema',
      url: `${CITY_DATA_BASE_URL}/demand_data.json.gz`,
    },
    {
      label: 'buildings_index',
      schemaKey: 'OptimizedBuildingIndexSchema',
      url: `${CITY_DATA_BASE_URL}/buildings_index.json.gz`,
    },
    {
      label: 'roads',
      schemaKey: 'RoadsGeojsonSchema',
      url: `${CITY_DATA_BASE_URL}/roads.geojson.gz`,
    },
    {
      label: 'runways_taxiways',
      schemaKey: 'RunwaysTaxiwaysGeojsonSchema',
      url: `${CITY_DATA_BASE_URL}/runways_taxiways.geojson.gz`,
    },
  ];

  const failures: string[] = [];

  for (const check of checks) {
    try {
      const payload = await loadRuntimeJson(check.url);
      const schema = api.schemas[check.schemaKey] as
        | { safeParse: (data: unknown) => { success: boolean; error?: unknown } }
        | undefined
        | null;
      if (!schema?.safeParse) {
        failures.push(`${check.label}: missing schema ${check.schemaKey}`);
        continue;
      }
      const result = schema.safeParse(payload);
      if (!result.success) {
        failures.push(`${check.label}: ${summarizeSchemaError(result.error)}`);
        continue;
      }
      console.log(`${TAG} Runtime schema validation passed for ${check.label}.`);
    } catch (error) {
      failures.push(
        `${check.label}: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }

  if (failures.length > 0) {
    console.error(`${TAG} Runtime schema validation failed:`, failures);
    api.ui.showNotification(
      `${MOD_NAME} runtime validation failed. Check console/logs.`,
      'error',
    );
    return;
  }

  console.log(`${TAG} Runtime schema validation passed for all city data files.`);
}

if (!api) {
  console.error(`${TAG} SubwayBuilderAPI not found.`);
} else {
  console.log(`${TAG} ${MOD_NAME} v${MOD_VERSION} | API v${api.version}`);

  try {
    configureKyivCityRuntime();
    validateRuntimeSchemas();

    api.hooks.onGameInit(configureKyivCityRuntime);
    api.hooks.onGameInit(() => {
      validateRuntimeSchemas();
    });

    api.hooks.onCityLoad((cityCode) => {
      if (cityCode === CITY_CODE) {
        console.log(`${TAG} Loaded city ${CITY_CODE}.`);
      }
    });
  } catch (error) {
    console.error(`${TAG} Failed to configure runtime:`, error);
    api.ui.showNotification(
      `${MOD_ID} failed to load. Check console for details.`,
      'error',
    );
  }
}
