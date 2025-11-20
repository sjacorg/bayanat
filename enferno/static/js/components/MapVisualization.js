const MapVisualization = Vue.defineComponent({
  props: {
    open: Boolean,
    visualizeEndpoint: { type: String, default: '/admin/api/flowmap/visualize' },
    statusEndpoint: { type: String, default: '/admin/api/flowmap/status' },
    dataEndpoint: { type: String, default: '/admin/api/flowmap/data' },
    query: { type: Array, default: () => [{}] },
    search: { type: String, default: '' },
  },

  emits: ['update:open', 'advancedSearch', 'resetSearch', 'doSearch', 'update:search'],

  data: () => ({
    translations: window.translations,
    actorDrawer: false,

    loading: false,
    loadingMessage: '',
    errorMessage: '',

    locations: [],
    flows: [],

    people: [
      { id: 21353, name: 'Daniel Davies' },
      { id: 32145, name: 'Rebecca Alexander' },
      { id: 23524, name: 'Shawn Ochoa' },
      { id: 21342, name: 'David Kelly' },
      { id: 31342, name: 'Kelly King' },
      { id: 24382, name: 'Christine Romero' },
      { id: 29472, name: 'Samuel Matthews' },
      { id: 21647, name: 'Joan Sanders' },
      { id: 28421, name: 'Darren Burton' },
    ],
  }),

  watch: {
    open(val) {
      if (val) this.initMapFlow();
    },
  },

  methods: {
    /* -------------------------------------------------
       API ORCHESTRATION
    ------------------------------------------------- */
    async initMapFlow() {
      this.loading = true;
      this.errorMessage = '';
      this.loadingMessage = this.translations.preparingMap_ ?? 'Preparing map...';

      const result = await this.fetchData();

      if (this.errorMessage) {
        this.loading = false;
        return;
      }

      this.locations = result.locations;
      this.flows = result.flows;

      this.loading = false;
    },

    async fetchData() {
      this.loading = true;
      this.loadingMessage = this.translations.startingGeneration_ ?? 'Starting…';

      try {
        const start = await api.post(this.visualizeEndpoint, { q: this.query });
        const taskId = start?.data?.task_id;

        if (!taskId) throw new Error('Flowmap generation failed.');

        let status = 'pending';
        let error = null;

        while (status === 'pending') {
          const res = await api.get(this.statusEndpoint);
          status = res?.data?.status;
          error = res?.data?.error;

          if (status === 'pending') {
            this.loadingMessage = this.translations.waitingForMapGeneration_ ?? 'Processing…';
            await new Promise((r) => setTimeout(r, 1500));
          }
        }

        if (status === 'error') throw new Error(error || 'Map generation error.');

        this.loadingMessage = this.translations.fetchingVisualizationData_ ?? 'Loading data…';

        const dataRes = await api.get(this.dataEndpoint);

        return {
          locations: Array.isArray(dataRes.data?.locations) ? dataRes.data.locations : [],
          flows: Array.isArray(dataRes.data?.flows) ? dataRes.data.flows : [],
        };
      } catch (err) {
        console.error(err);
        this.errorMessage = err.message || 'Something went wrong';
        return { locations: [], flows: [] };
      } finally {
        this.loading = false;
      }
    },

    retry() {
      this.errorMessage = '';
      this.initMapFlow();
    },
  },

  template: `
    <v-dialog fullscreen class="map-visualization-dialog" :model-value="open">
      <v-toolbar color="primary">

        <!-- Left: Title -->
        <div class="w-33 ml-4">
          <v-toolbar-title>
            {{ translations.mapVisualization_ }}
          </v-toolbar-title>
        </div>

        <!-- Center: Search -->
        <v-text-field
          class="w-33"
          variant="solo"
          density="comfortable"
          hide-details="auto"

          :model-value="search"
          @update:model-value="$emit('update:search', $event)"
          @keydown.enter="$emit('doSearch', search)"

          append-icon="mdi-ballot"
          :append-inner-icon="!search ? '' : 'mdi-close'"
          @click:append-inner="
            $emit('update:search', '');
            $emit('resetSearch')
          "
          @click:append="$emit('advancedSearch')"
          prepend-inner-icon="mdi-magnify"
          :label="translations.search_"
        />

        <!-- Right: Close -->
        <div class="w-33 mr-4 d-flex">
          <v-spacer></v-spacer>
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="$emit('update:open', false)"
          />
        </div>
      </v-toolbar>

      <!-- MAP + OVERLAYS -->
      <v-container fluid class="pa-0 fill-height">
        <!-- MAP -->
        <flowmap
          :locations="locations"
          :flows="flows"
          class="w-100 h-100"
        />

        <!-- LOADING OVERLAY -->
        <v-overlay
          v-model="loading"
          persistent
          contained
          class="d-flex align-center justify-center"
        >
          <v-card elevation="6" rounded="lg" class="pa-6 text-center">
            <v-progress-circular
              indeterminate
              color="primary"
              size="64"
            />
            <div class="text-subtitle-1 mt-4">
              {{ loadingMessage }}
            </div>
          </v-card>
        </v-overlay>

        <!-- ERROR OVERLAY -->
        <div
          v-if="errorMessage"
          class="d-flex align-center justify-center fill-height"
        >
          <v-card class="pa-8 text-center" max-width="420">

            <v-icon
              color="error"
              size="64"
              class="mb-4"
            >
              mdi-alert-circle-outline
            </v-icon>

            <div class="text-h6 mb-4">
              {{ errorMessage }}
            </div>

            <v-btn
              color="primary"
              @click="retry"
            >
              Retry
            </v-btn>

          </v-card>
        </div>

        <!-- Drawer -->
        <v-navigation-drawer
          v-model="actorDrawer"
          location="right"
          width="380"
        >
          <!-- Toggle button that sticks out -->
          <v-card class="position-absolute pa-1" :style="{ left: '-48px', top: '50%', transform: 'translateY(-50%)', borderRadius: '12px 0 0 12px' }">
            <v-btn icon size="small" @click="actorDrawer = !actorDrawer">
              <v-icon>
                {{ actorDrawer ? 'mdi-chevron-right' : 'mdi-chevron-left' }}
              </v-icon>
            </v-btn>
          </v-card>

          <!-- Content -->
          <v-container>
            <v-card
              v-for="person in people"
              :key="person.id"
              class="mb-2 pa-4 rounded-lg"
              elevation="1"
            >
              <div class="d-flex align-center ga-2">
                <v-chip> ID {{ person.id }} </v-chip>
                <span class="text-subtitle-2 font-weight-medium">
                  {{ person.name }}
                </span>
              </div>
            </v-card>
          </v-container>
        </v-navigation-drawer>
      </v-container>
    </v-dialog>
  `,
});
