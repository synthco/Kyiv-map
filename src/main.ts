const MOD_ID = 'com.ivantyshchenko.kyiv-city';
const MOD_NAME = 'Kyiv Metropolitan Area';
const MOD_VERSION = '1.0.0';
const CITY_CODE = 'KYV';
const TAG = '[KyivCity]';

const LOCAL_ASSET_BASE_URL = 'http://127.0.0.1:8080/kyv';

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

function configureKyivCityRuntime() {
  if (runtimeConfigured) {
    return;
  }

  runtimeConfigured = true;

  api.registerCity(CITY_CONFIG);

  api.map.setTileURLOverride({
    cityCode: CITY_CODE,
    tilesUrl: `${LOCAL_ASSET_BASE_URL}/tiles/{z}/{x}/{y}.mvt`,
    foundationTilesUrl: `${LOCAL_ASSET_BASE_URL}/foundation/{z}/{x}/{y}.mvt`,
    maxZoom: 15,
  });

  api.cities.setCityDataFiles(CITY_CODE, {
    buildingsIndex: `${LOCAL_ASSET_BASE_URL}/data/buildings_index.json.gz`,
    demandData: `${LOCAL_ASSET_BASE_URL}/data/demand_data.json.gz`,
    roads: `${LOCAL_ASSET_BASE_URL}/data/roads.geojson.gz`,
    runwaysTaxiways: `${LOCAL_ASSET_BASE_URL}/data/runways_taxiways.geojson.gz`,
  });

  api.map.setDefaultLayerVisibility(CITY_CODE, {
    buildingFoundations: true,
    oceanFoundations: false,
  });

  console.log(`${TAG} Registered ${CITY_CODE} runtime against ${LOCAL_ASSET_BASE_URL}.`);
}

if (!api) {
  console.error(`${TAG} SubwayBuilderAPI not found.`);
} else {
  console.log(`${TAG} ${MOD_NAME} v${MOD_VERSION} | API v${api.version}`);

  try {
    configureKyivCityRuntime();
    api.hooks.onGameInit(configureKyivCityRuntime);
    api.hooks.onCityLoad((cityCode) => {
      if (cityCode === CITY_CODE) {
        console.log(`${TAG} Loaded city ${CITY_CODE}.`);
      }
    });
  } catch (error) {
    console.error(`${TAG} Failed to configure runtime:`, error);
    api.ui.showNotification(`${MOD_ID} failed to load. Check console for details.`, 'error');
  }
}
