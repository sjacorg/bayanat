const MapVisualization = Vue.defineComponent({
  props: {
    open: Boolean,
    visualizeEndpoint: { type: String, default: '/admin/api/flowmap/visualize' },
    statusEndpoint: { type: String, default: '/admin/api/flowmap/status' },
    dataEndpoint: { type: String, default: '/admin/api/flowmap/data' },
    query: { type: Array, default: () => [{}] },
  },
  emits: ['update:open', 'advancedSearch'],

  data: () => ({
    // API / Tile URLs
    mapsApiEndpoint: mapsApiEndpoint,
    googleTileUrl: `https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&key=${window.__GOOGLE_MAPS_API_KEY__}`,
    translations: window.translations,

    // UI state
    tooltip: null,
    menu: false,
    windowWidth: window.innerWidth,
    windowHeight: window.innerHeight,
    loading: false,
    loadingMessage: '',
    errorMessage: '',

    // Map state
    mapInitialized: false,
    map: null,
    deck: null,

    // Attribution
    attribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
    googleAttribution: '&copy; <a href="https://www.google.com/maps">Google Maps</a>, Imagery ©2025 Google, Maxar Technologies',
  }),

  watch: {
    open(val) {
      val ? this.initMapFlow() : this.clearMap();
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
    // ------------------
    // Utils
    // ------------------
    buildTileUrls(template, subdomains = ['a','b','c']) {
      return template.includes('{s}') ? subdomains.map(s => template.replace('{s}', s)) : [template];
    },

    getInitialViewState(locations) {
      if (!locations?.length) return { longitude: 0, latitude: 0, zoom: 1, pitch: 0, bearing: 0 };
      const validLocs = locations.filter(l => Number.isFinite(l.lon) && Number.isFinite(l.lat));
      return FlowmapBundle.FlowmapData.getViewStateForLocations(validLocs, loc => [loc.lon, loc.lat], [this.windowWidth, this.windowHeight], { pad: 0.3 });
    },

    createFlowmapLayer(locations, flows) {
      if (!locations.length || !flows.length) return null;
      return new FlowmapBundle.FlowmapLayers.FlowmapLayer({
        id: 'flowmap-layer',
        data: { locations, flows },
        pickable: true,
        getLocationId: d => d.id,
        getLocationLat: d => d.lat,
        getLocationLon: d => d.lon,
        getLocationName: d => d.name,
        getFlowOriginId: f => f.origin,
        getFlowDestId: f => f.dest,
        getFlowMagnitude: f => f.count,
        darkMode: false,
        colorScheme: 'TealGrn',
        clusteringEnabled: true,
        highlightColor: 'orange',
        fadeEnabled: true,
        onClick: this.onClick,
      });
    },

    createBaseToggleControl() {
      return {
        onAdd: map => {
          this._map = map;
          const container = document.createElement('div');
          container.className = 'maplibregl-ctrl maplibregl-ctrl-group';
          const btn = document.createElement('button');
          btn.innerHTML = '<img src="/static/css/images/layers.png" class="pa-1 w-100" />';
          btn.title = 'Toggle Base Map';
          let current = 'osm';
          btn.onclick = () => {
            const showGoogle = current === 'osm';
            map.setLayoutProperty('osm-layer', 'visibility', showGoogle ? 'none' : 'visible');
            map.setLayoutProperty('google-layer', 'visibility', showGoogle ? 'visible' : 'none');
            current = showGoogle ? 'google' : 'osm';
          };
          container.appendChild(btn);
          this._container = container;
          return container;
        },
        onRemove: () => { this._container.remove(); this._map = undefined; },
      };
    },

    async fetchData() {
      this.loading = true;
      this.loadingMessage = this.translations.startingGeneration_;
      this.errorMessage = '';
      try {
        const startRes = await api.post(this.visualizeEndpoint, { q: this.query });
        const taskId = startRes?.data?.task_id;
        if (!taskId) throw new Error(this.translations.mapGenerationFailed_);

        // Poll status
        let status = 'pending', error = null;
        while (status === 'pending') {
          const res = await api.get(this.statusEndpoint);
          status = res?.data?.status;
          error = res?.data?.error;
          if (status === 'pending') {
            this.loadingMessage = this.translations.waitingForMapGeneration_;
            await new Promise(r => setTimeout(r, 2000));
          }
        }
        if (status === 'error') throw new Error(error || this.translations.mapGenerationFailed_);

        this.loadingMessage = this.translations.fetchingVisualizationData_;
        const dataRes = await api.get(this.dataEndpoint);
        return {
          locations: Array.isArray(dataRes.data?.locations) ? dataRes.data.locations : [],
          flows: Array.isArray(dataRes.data?.flows) ? dataRes.data.flows : [],
        };
      } catch (err) {
        console.error(err);
        this.errorMessage = err.message || this.translations.mapGenerationFailed_;
        return { locations: [], flows: [] };
      } finally {
        this.loading = false;
      }
    },

    async initMapFlow() {
      this.clearMap();
      this.loading = true;
      this.loadingMessage = this.translations.preparingMap_;

      const { locations, flows } = await this.fetchData();
      if (this.errorMessage) return;

      const initialViewState = this.getInitialViewState(locations);

      this.initMaplibre(initialViewState);
      this.initDeck(locations, flows, initialViewState);

      this.mapInitialized = true;
      this.loading = false;
    },

    initMaplibre(initialViewState) {
      this.map = new MaplibreGL.Map({
        container: 'map',
        interactive: false,
        center: [initialViewState.longitude, initialViewState.latitude],
        zoom: initialViewState.zoom,
        bearing: initialViewState.bearing,
        pitch: initialViewState.pitch,
        style: {
          version: 8,
          sources: { osm: { type: 'raster', tiles: this.buildTileUrls(this.mapsApiEndpoint), tileSize: 256, attribution: this.attribution, maxzoom: 19 } },
          layers: [{ id: 'osm-layer', type: 'raster', source: 'osm' }],
        },
      });
      this.map.addControl(new MaplibreGL.NavigationControl({ showCompass: false }), 'top-left');
      this.map.addControl(new MaplibreGL.FullscreenControl(), 'top-left');
      if (window.__GOOGLE_MAPS_API_KEY__) this.map.addControl(this.createBaseToggleControl(), 'top-left');

      this.map.on('load', () => {
        this.map.addSource('google', {
          type: 'raster',
          tiles: this.buildTileUrls(this.googleTileUrl, ['mt0','mt1','mt2','mt3']),
          tileSize: 256,
          maxzoom: 20,
          attribution: this.googleAttribution,
        });
        this.map.addLayer({ id: 'google-layer', type: 'raster', source: 'google', layout: { visibility: 'none' } });
      });
    },

    initDeck(locations, flows, initialViewState) {
      const flowLayer = this.createFlowmapLayer(locations, flows);
      this.deck = new FlowmapBundle.DeckCore.Deck({
        canvas: 'deck-canvas',
        width: '100%',
        height: '100%',
        initialViewState,
        controller: true,
        map: true,
        layers: flowLayer ? [flowLayer] : [],
        onViewStateChange: ({ viewState }) => {
          this.map.jumpTo({
            center: [viewState.longitude, viewState.latitude],
            zoom: viewState.zoom,
            bearing: viewState.bearing,
            pitch: viewState.pitch,
          });
          this.menu = false;
        },
      });

      this.map.on('move', () => {
        if (!this.deck) return;
        const center = this.map.getCenter();
        this.deck.setProps({
          viewState: {
            longitude: center.lng,
            latitude: center.lat,
            zoom: this.map.getZoom(),
            bearing: this.map.getBearing(),
            pitch: this.map.getPitch(),
            transitionDuration: 0,
          },
        });
      });
    },

    clearMap() {
      this.deck?.finalize();
      this.map?.remove();
      this.deck = this.map = null;
      this.mapInitialized = false;
      this.tooltip = null;
      this.menu = false;
      const el = document.getElementById('map');
      if (el) el.innerHTML = '';
    },

    retry() {
      this.errorMessage = '';
      this.initMapFlow();
    },

    onClick(info) {
      if (!info?.object) return;
      const obj = info.object;
      const title = obj.type === 'flow' ? this.translations.flowDetails_ : this.translations.locationDetails_;
      const details = obj.type === 'flow'
        ? [
            { label: this.translations.origin_, value: obj.origin.name },
            { label: this.translations.destination_, value: obj.dest.name },
            { label: this.translations.count_, value: obj.count },
          ]
        : [
            { label: this.translations.name_, value: obj.name },
            { label: this.translations.totalIn_, value: obj.totals?.incomingCount || 0 },
            { label: this.translations.totalOut_, value: obj.totals?.outgoingCount || 0 },
          ];

      this.tooltip = {
        x: info.x,
        y: info.y,
        content: `<div style="min-width:220px;">
          <div style="font-weight:600;margin-bottom:6px;">${title}</div>
          <div style="border-top:1px solid #e0e0e0;margin-bottom:4px;"></div>
          ${details.map(d => `<div style="margin-bottom:4px;"><div style="font-weight:500;">${d.label}</div><div>${d.value}</div></div>`).join('')}
        </div>`,
      };
      this.menu = true;
    },
  },

  template: `
    <v-dialog fullscreen :model-value="open">
      <v-toolbar color="primary" dark>
        <v-toolbar-title>{{ translations.mapVisualization_ }}</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn prepend-icon="mdi-ballot" variant="elevated" @click="$emit('advancedSearch')">Advanced search</v-btn>
        <v-btn icon="mdi-close" @click="$emit('update:open', false)"></v-btn>
      </v-toolbar>

      <v-sheet class="relative">
        <div id="map-visualization" class="relative">
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
