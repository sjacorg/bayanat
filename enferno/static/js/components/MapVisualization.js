const MapVisualization = Vue.defineComponent({
  props: {
    open: Boolean,
    visualizeEndpoint: { type: String, default: '/admin/api/flowmap/visualize' },
    statusEndpoint: { type: String, default: '/admin/api/flowmap/status' },
    dataEndpoint: { type: String, default: '/admin/api/flowmap/data' },
    query: { type: Array, default: () => [{}] },
  },
  emits: ['update:open'],
  data: () => ({
    translations: window.translations,
    maplibreStyle: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
    tooltip: null,
    menu: false,
    windowWidth: window.innerWidth,
    windowHeight: window.innerHeight,
    mapInitialized: false,

    // ✅ New UI states
    loading: false,
    loadingMessage: '',
    errorMessage: '',
  }),
  watch: {
    open(val) {
      if (val) {
        this.clearMap();
        this.initMap();
      } else {
        this.clearMap();
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
      this.loading = true;
      this.loadingMessage = translations.startingGeneration_;
      this.errorMessage = '';

      try {
        // Step 1: Start generation
        const startRes = await api.post(this.visualizeEndpoint, { q: this.query });
        const taskId = startRes?.data?.task_id;
        if (!taskId) throw new Error(translations.mapGenerationFailed_);

        // Step 2: Wait for task completion via status endpoint
        let status = 'pending';
        let error = null;

        while (status === 'pending') {
          const res = await api.get(this.statusEndpoint);
          status = res?.data?.status;
          error = res?.data?.error;

          if (status === 'pending') {
            this.loadingMessage = translations.waitingForMapGeneration_;
            await new Promise((r) => setTimeout(r, 2000)); // small delay before polling again
          }
        }

        if (status === 'error') throw new Error(error || translations.mapGenerationFailed_);

        // Step 3: Fetch the data
        this.loadingMessage = translations.fetchingVisualizationData_;
        const dataRes = await api.get(this.dataEndpoint);
        const { locations, flows } = dataRes.data || {};
        return { locations, flows };
      } catch (err) {
        console.error(err);
        this.errorMessage = err.message || translations.mapGenerationFailed_;
        return { locations: [], flows: [] };
      } finally {
        this.loading = false;
      }
    },

    async initMap() {
      this.loading = true;
      this.loadingMessage = translations.preparingMap_;
      const data = await this.fetchData();

      if (this.errorMessage) return; // stop if error

      this.loadingMessage = translations.renderingMap_;
      let { locations, flows } = data;
      const [width, height] = [this.windowWidth, this.windowHeight];

      // Ensure locations and flows are arrays
      locations = Array.isArray(locations) ? locations : [];
      flows = Array.isArray(flows) ? flows : [];

      // Initial view state
      const initialViewState =
        locations.length > 0
          ? FlowmapBundle.FlowmapData.getViewStateForLocations(
              locations.filter((l) => Number.isFinite(l.lon) && Number.isFinite(l.lat)),
              (loc) => [loc.lon, loc.lat],
              [width, height],
              { pad: 0.3 },
            )
          : {
              longitude: 0,
              latitude: 0,
              zoom: 1,
              pitch: 0,
              bearing: 0,
            };

      // Initialize Maplibre
      this.map = new MaplibreGL.Map({
        container: 'map',
        style: this.maplibreStyle,
        interactive: false,
        center: [initialViewState.longitude, initialViewState.latitude],
        zoom: initialViewState.zoom,
        bearing: initialViewState.bearing,
        pitch: initialViewState.pitch,
      });

      const layers = [];

      if (locations.length > 0 && flows.length > 0) {
        layers.push(
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
            colorScheme: 'TealGrn',
            clusteringEnabled: true,
            highlightColor: 'orange',
            fadeEnabled: false,
            onClick: this.onClick,
          }),
        );
      }

      // Initialize Deck
      this.deck = new FlowmapBundle.DeckCore.Deck({
        canvas: 'deck-canvas',
        width: '100%',
        height: '100%',
        initialViewState,
        controller: true,
        map: true,
        onViewStateChange: ({ viewState }) => {
          this.map.jumpTo({
            center: [viewState.longitude, viewState.latitude],
            zoom: viewState.zoom,
            bearing: viewState.bearing,
            pitch: viewState.pitch,
          });
          this.menu = false;
        },
        layers,
      });

      this.mapInitialized = true;
      this.loading = false;
    },

    clearMap() {
      if (this.deck) this.deck.finalize();
      if (this.map) this.map.remove();
      this.deck = this.map = null;
      this.mapInitialized = false;
      this.tooltip = null;
      this.menu = false;
      const el = document.getElementById('map');
      if (el) el.innerHTML = '';
    },

    retry() {
      this.errorMessage = '';
      this.initMap();
    },

    onClick(info) {
      if (!info || !info.object) return;
      const obj = info.object;

      let title = '';
      let details = [];

      if (obj.type === 'flow') {
        title = translations.flowDetails_;
        details = [
          { label: translations.origin_, value: obj.origin.name },
          { label: translations.destination_, value: obj.dest.name },
          { label: translations.count_, value: obj.count },
        ];
      } else if (obj.type === 'location') {
        const totals = obj.totals || { incomingCount: 0, outgoingCount: 0 };
        title = translations.locationDetails_;
        details = [
          { label: translations.name_, value: obj.name },
          { label: translations.totalIn_, value: totals.incomingCount },
          { label: translations.totalOut_, value: totals.outgoingCount },
        ];
      }

      const content = `
        <div style="min-width:220px;">
          <div style="font-weight:600;margin-bottom:6px;">${title}</div>
          <div style="border-top:1px solid #e0e0e0;margin-bottom:4px;"></div>
          ${details
            .map(
              (d) => `
            <div style="margin-bottom:4px;">
              <div style="font-weight:500;">${d.label}</div>
              <div>${d.value}</div>
            </div>`,
            )
            .join('')}
        </div>`;
      this.tooltip = { x: info.x, y: info.y, content };
      this.menu = true;
    },
  },

  template: `
    <v-dialog fullscreen :model-value="open">
      <v-toolbar color="primary" dark>
        <v-toolbar-title>{{ translations.mapVisualization_ }}</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" @click="$emit('update:open', false)"></v-btn>
      </v-toolbar>

      <v-sheet class="relative fill-height">
        <div id="map-visualization" class="relative fill-height">
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

          <!-- Loading Overlay -->
          <v-overlay v-model="loading" persistent class="d-flex align-center justify-center" content-class="d-flex flex-column align-center justify-center">
            <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
            <div class="mt-4 text-h6">{{ loadingMessage }}</div>
          </v-overlay>

          <!-- Error Message -->
          <v-container>
            <v-card
              v-if="errorMessage"
              class="d-flex flex-column align-center justify-center text-center pa-6"
              style="inset:0; z-index:100;"
            >
              <v-icon color="error" size="64">mdi-alert-circle-outline</v-icon>
              <div class="text-h6 mt-2">{{ errorMessage }}</div>
              <v-btn class="mt-4" color="primary" @click="retry">Retry</v-btn>
            </v-card>
          </v-container>
        </div>
      </v-sheet>
    </v-dialog>
  `,
});
