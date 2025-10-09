const MapVisualization = Vue.defineComponent({  
    data: () => ({
        MAPLIBRE_STYLE: "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
        DATA_PATH: `https://gist.githubusercontent.com/ilyabo/68d3dba61d86164b940ffe60e9d36931/raw/a72938b5d51b6df9fa7bba9aa1fb7df00cd0f06a`,
    }),
  mounted() {
    this.fetchData().then((data) => {
        const {locations, flows} = data;
        const [width, height] = [globalThis.innerWidth, globalThis.innerHeight];
        const initialViewState = FlowmapBundle.FlowmapData.getViewStateForLocations(
            locations,
            (loc) => [loc.lon, loc.lat],
            [width, height],
            {pad: 0.3}
        );

        const map = new FlowmapBundle.maplibre.Map({
            container: "map",
            style: this.MAPLIBRE_STYLE,
            // Note: deck.gl will be in charge of interaction and event handling
            interactive: false,
            center: [initialViewState.longitude, initialViewState.latitude],
            zoom: initialViewState.zoom,
            bearing: initialViewState.bearing,
            pitch: initialViewState.pitch,
        });

        const deck = new FlowmapBundle.Deck.Deck({
            canvas: "deck-canvas",
            width: "100%",
            height: "100%",
            initialViewState: initialViewState,
            controller: true,
            map: true,
            onViewStateChange: ({viewState}) => {
            map.jumpTo({
                center: [viewState.longitude, viewState.latitude],
                zoom: viewState.zoom,
                bearing: viewState.bearing,
                pitch: viewState.pitch,
            });
            },
            layers: [],
        });

        deck.setProps({
            layers: [
                new FlowmapBundle.FlowmapLayers.FlowmapLayer({
                    id: "my-flowmap-layer",
                    data: {locations, flows},
                    pickable: true,
                    getLocationId: (loc) => loc.id,
                    getLocationLat: (loc) => loc.lat,
                    getLocationLon: (loc) => loc.lon,
                    getFlowOriginId: (flow) => flow.origin,
                    getFlowDestId: (flow) => flow.dest,
                    getFlowMagnitude: (flow) => flow.count,
                    getLocationName: (loc) => loc.name,
                }),
            ],
        });
    });
  },
  methods: {
    async fetchData() {
        return await Promise.all([
            FlowmapBundle.d3Fetch.csv(`${this.DATA_PATH}/locations.csv`, (row, i) => ({
            id: row.id,
            name: row.name,
            lat: Number(row.lat),
            lon: Number(row.lon),
            })),
            FlowmapBundle.d3Fetch.csv(`${this.DATA_PATH}/flows.csv`, (row) => ({
            origin: row.origin,
            dest: row.dest,
            count: Number(row.count),
            })),
        ]).then(([locations, flows]) => ({locations, flows}));
        }
  },
  template: `
    <div id="container">
      <div id="map"></div>
      <canvas id="deck-canvas"></canvas>
    </div>
  `,
});
