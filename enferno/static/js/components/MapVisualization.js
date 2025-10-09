const MapVisualization = Vue.defineComponent({
  props: {
    open: Boolean, // control dialog from parent
  },
  emits: ['update:open'],
  data: () => ({
    MAPLIBRE_STYLE: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
    DATA_PATH: `https://gist.githubusercontent.com/ilyabo/68d3dba61d86164b940ffe60e9d36931/raw/a72938b5d51b6df9fa7bba9aa1fb7df00cd0f06a`,
    tooltip: null,
    menu: false,
    windowWidth: window.innerWidth,
    windowHeight: window.innerHeight,
    mapInitialized: false,
  }),
  watch: {
    open(val) {
      if (val && !this.mapInitialized) {
        // wait for dialog to mount
        this.$nextTick(() => this.initMap());
      }
    },
  },
  mounted() {
    window.addEventListener('resize', () => {
      this.windowWidth = window.innerWidth;
      this.windowHeight = window.innerHeight;

      this.menu = false;
    });
  },
  methods: {
    async fetchData() {
      return await Promise.all([
        FlowmapBundle.d3Fetch.csv(`${this.DATA_PATH}/locations.csv`, (row) => ({
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
      ]).then(([locations, flows]) => ({ locations, flows }));
    },

    async initMap() {
      const data = await this.fetchData();
      const { locations, flows } = data;
      const [width, height] = [this.windowWidth, this.windowHeight];

      const initialViewState = FlowmapBundle.FlowmapData.getViewStateForLocations(
        locations,
        (loc) => [loc.lon, loc.lat],
        [width, height],
        { pad: 0.3 },
      );

      const map = new FlowmapBundle.maplibre.Map({
        container: 'map',
        style: this.MAPLIBRE_STYLE,
        interactive: false,
        center: [initialViewState.longitude, initialViewState.latitude],
        zoom: initialViewState.zoom,
        bearing: initialViewState.bearing,
        pitch: initialViewState.pitch,
      });

      const deck = new FlowmapBundle.Deck.Deck({
        canvas: 'deck-canvas',
        width: '100%',
        height: '100%',
        initialViewState,
        controller: true,
        map: true,
        onViewStateChange: ({ viewState }) => {
          map.jumpTo({
            center: [viewState.longitude, viewState.latitude],
            zoom: viewState.zoom,
            bearing: viewState.bearing,
            pitch: viewState.pitch,
          });

          this.menu = false;
        },
        layers: [
          new FlowmapBundle.FlowmapLayers.FlowmapLayer({
            id: 'my-flowmap-layer',
            data: { locations, flows },
            pickable: true,
            getLocationId: (d) => d.id,
            getLocationLat: (d) => d.lat,
            getLocationLon: (d) => d.lon,
            getLocationName: (d) => d.name,
            getFlowOriginId: (f) => f.origin,
            getFlowDestId: (f) => f.dest,
            getFlowMagnitude: (f) => f.count,
            darkMode: false,
            colorScheme: 'OrRd',
            fadeEnabled: false,
            fadeOpacityEnabled: false,
            fadeAmount: 0,
            adaptiveScalesEnabled: true,
            clusteringEnabled: true,
            maxTopFlowsDisplayNum: 5000,
            highlightColor: 'orange',
            onClick: this.onClick,
          }),
        ],
      });

      this.mapInitialized = true;
    },

    onClick(info) {
      if (!info || !info.object) return;
      const obj = info.object;

      let title = '';
      let details = [];

      if (obj.type === 'flow') {
        title = 'Flow Details';
        details = [
          { label: 'Origin', value: obj.origin.name },
          { label: 'Destination', value: obj.dest.name },
          { label: 'Count', value: obj.count },
        ];
      } else if (obj.type === 'location') {
        const totals = obj.totals || { incomingCount: 0, outgoingCount: 0 };
        title = 'Location Details';
        details = [
          { label: 'Name', value: obj.name },
          { label: 'Total In', value: totals.incomingCount },
          { label: 'Total Out', value: totals.outgoingCount },
        ];
      }

      // Build HTML using plain divs
      const content = `
    <div style="min-width: 220px; word-break: break-word;">
      <div style="font-weight: 600; margin-bottom: 6px;">${title}</div>
      <div style="border-top: 1px solid #e0e0e0; margin-bottom: 4px;"></div>
      <div class="d-flex ga-2 flex-column">
      ${details
        .map(
          (d) => `
          <div style="margin-bottom: 2px;">
            <div style="font-weight: 500;">${d.label}</div>
            <div>${d.value}</div>
          </div>
        `,
        )
        .join('')}
    </div></div>
  `;

      this.tooltip = {
        x: info.x,
        y: info.y,
        content,
      };

      // Flip if near edges
      const tooltipWidth = 250;
      const tooltipHeight = 150;
      let left = this.tooltip.x;
      let top = this.tooltip.y;
      if (left + tooltipWidth > this.windowWidth) left -= tooltipWidth + 10;
      if (top + tooltipHeight > this.windowHeight) top -= tooltipHeight + 10;
      this.tooltip.x = left;
      this.tooltip.y = top;

      this.menu = true;
    },
  },

  template: `
    <v-dialog fullscreen :model-value="open">
      <v-toolbar color="primary" dark>
        <v-toolbar-title>Map Flows {{ open }}</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" @click="$emit('update:open', false)"></v-btn>
      </v-toolbar>

      <v-sheet>
        <div id="container" class="relative">
            <div id="map"></div>
            <canvas id="deck-canvas"></canvas>

            <!-- Tooltip -->
            <v-card
                v-if="menu"
                class="absolute h-fit"
                :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px', maxWidth: '250px', zIndex: 50 }"
            >
                <v-card-text v-html="tooltip.content"></v-card-text>
            </v-card>
        </div>
      </v-sheet>
    </v-dialog>
  `,
});
