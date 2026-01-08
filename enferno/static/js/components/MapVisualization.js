const MapVisualization = Vue.defineComponent({
  props: {
    open: Boolean,
    visualizeEndpoint: { type: String, default: '/admin/api/flowmap/visualize' },
    statusEndpoint: { type: String, default: '/admin/api/flowmap/status' },
    dataEndpoint: { type: String, default: '/admin/api/flowmap/data' },
    entitiesEndpoint: { type: String, default: '/admin/api/actors/' },
    query: { type: Array, default: () => [{}] },
    search: { type: String, default: '' },
    entity: { type: Object, default: () => null },
    entityLoader: { type: Boolean, default: false },
  },

  emits: [
    'update:open',
    'advancedSearch',
    'resetSearch',
    'doSearch',
    'update:search',
    'showEntityDetails',
    'closeEntityDetails',
  ],

  data: () => ({
    translations: window.translations,
    selectedEventTypes: [],
    drawerWidth: 398,
    navHeight: 64,

    localSearch: '',

    loading: false,
    loadingMessage: '',
    errorMessage: '',

    locations: [],
    flows: [],

    infiniteScrollCallback: null,
    entities: {
      selected: null,
      drawer: false,
      loading: false,
      items: [],
      cursor: null,
      nextCursor: null,
      perPage: 30,
      total: null,
    },
  }),

  watch: {
    open(isOpen) {
      if (isOpen) {
        this.localSearch = this.search;
        this.resetEntities();
        this.initMapFlow();
        this.entities.drawer = false;
      }
    },

    query: {
      deep: true,
      handler() {
        this.resetEntities();
        this.$emit('closeEntityDetails');
      },
    },
    entity: {
      handler(nextEntity) {
        // When an entity is selected, show all event types
        if (nextEntity && Object.keys(nextEntity).length === 0) {
          this.selectedEventTypes = this.getDefaultSelectedEventTypes(this.uniqueEventTypes);
        } else {
          this.selectedEventTypes = [...this.uniqueEventTypes];
        }
      },
    },
  },

  computed: {
    selectedEntityMapData() {
      if (!this.entities.selected) return null;
      if (this.entityLoader) return null;

      return MobilityMapUtils.parseEventsToMapData(this.entity?.events);
    },
    computedMapData() {
      // If an actor has been selected, use its map data else use the full data
      const baseData = this.selectedEntityMapData
        ? this.selectedEntityMapData
        : {
            locations: this.locations,
            flows: this.flows,
          };

      return this.filterMapData(baseData);
    },
    uniqueEventTypes() {
      const uniqueTypes = new Set();

      if (this.entity?.events) {
        this.entity.events.forEach((event) => {
          if (event?.eventtype?.title) {
            uniqueTypes.add(event.eventtype.title);
          }
        })
        return [...uniqueTypes];
      }

      this.locations.forEach((loc) => {
        if (loc.events_by_type) {
          Object.keys(loc.events_by_type).forEach((eventType) => uniqueTypes.add(eventType));
        }
      })
      this.flows.forEach((flow) => {
        if (flow.events_by_type) {
          Object.keys(flow.events_by_type).forEach((eventType) => uniqueTypes.add(eventType));
        }
      })
      return [...uniqueTypes];
    },
  },

  methods: {
    getDefaultSelectedEventTypes(eventTypes = []) {
      return [...eventTypes].filter(this.isDefaultSelectedEventType);
    },
    isDefaultSelectedEventType(eventType) {
      return eventType !== 'Residence' && eventType !== 'Birth';
    },
    matchesSelectedEventTypes(entity) {
      // No filters selected → show everything
      if (!this.selectedEventTypes.length) return true;

      const types = Object.keys(entity.events_by_type || {});
      if (!types.length) return true;

      return types.some(type =>
        this.selectedEventTypes.includes(type)
      );
    },

    filterMapData(baseData) {
      const { locations = [], flows = [] } = baseData;

      // STEP 1: filter flows first + add count
      const visibleFlows = flows
        .filter(this.matchesSelectedEventTypes)
        .map(flow => ({
          ...flow,
          count: Object.values(flow.events_by_type || {})
            .reduce((sum, value) => sum + value, 0),
        }));

      // STEP 2: collect required location IDs from visible flows
      const requiredLocationIds = new Set();
      visibleFlows.forEach(flow => {
        requiredLocationIds.add(flow.origin);
        requiredLocationIds.add(flow.dest);
      });

      // STEP 3: filter locations
      const visibleLocations = locations.filter(loc =>
        this.matchesSelectedEventTypes(loc) ||
        requiredLocationIds.has(loc.id)
      );

      return {
        locations: visibleLocations,
        flows: visibleFlows,
      };
    },
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

      // Preselect all event types, omit Residence and Birth by default
      this.selectedEventTypes = this.getDefaultSelectedEventTypes(this.uniqueEventTypes);

      this.loading = false;
    },

    async fetchData() {
      this.loading = true;
      this.loadingMessage = this.translations.startingGeneration_;

      try {
        // 1. Start the background job
        const start = await api.post(this.visualizeEndpoint, { q: this.query });
        const taskId = start?.data?.task_id;

        if (!taskId) {
          throw new Error('MobilityMap generation failed.');
        }

        // 2. Poll status using the helper
        this.loadingMessage = this.translations.waitingForMapGeneration_;

        const statusResult = await MobilityMapUtils.pollUntilDone(
          async () => {
            const res = await api.get(this.statusEndpoint);

            return {
              status: res?.data?.status,
              error: res?.data?.error,
            };
          },
          {
            interval: 1500,
            timeout: 60000,
          },
        );

        // 3. Handle errors
        if (statusResult.status === 'error') {
          throw new Error(statusResult.error || 'Map generation error.');
        }

        // 4. Fetch generated data
        this.loadingMessage = this.translations.fetchingVisualizationData_;

        const dataRes = await api.get(this.dataEndpoint);

        const metadata = dataRes.data?.metadata || {};
        this.$root.showSnack(this.translations.loadedLocationsFlowsAndActors_(metadata));

        return {
          locations: Array.isArray(dataRes.data?.locations) ? dataRes.data.locations : [],
          flows: Array.isArray(dataRes.data?.flows) ? dataRes.data.flows : [],
        };
      } catch (err) {
        console.error(err);
        this.errorMessage = err.message || 'Something went wrong';
        this.$root.showSnack(handleRequestError(err));
        return {
          locations: [],
          flows: [],
        };
      } finally {
        this.loading = false;
      }
    },

    retry() {
      this.errorMessage = '';
      this.initMapFlow();
    },

    resetEntities() {
      this.entities.items = [];
      this.entities.cursor = null;
      this.entities.nextCursor = null;
      this.entities.total = null;
      this.entities.loading = false;
      this.infiniteScrollCallback = null;

      // Reset the v-infinite-scroll internal state
      this.$nextTick(() => {
        this.$refs?.infiniteScroll?.reset();
      });
    },

    loadEntities(options) {
      if (options?.done) {
        this.infiniteScrollCallback = options.done;
      }

      if (this.entities.loading) return;

      this.entities.loading = true;

      const payload = {
        q: this.query, // 👈 EXACT SAME QUERY AS PARENT
        per_page: this.entities.perPage,
        cursor: this.entities.cursor, // null for first request
        include_count: true,
      };

      api
        .post(this.entitiesEndpoint, payload)
        .then((response) => {
          const data = response.data;

          if (!this.entities.cursor) {
            this.entities.items = data.items;
          } else {
            this.entities.items.push(...data.items);
          }

          // Save new cursor
          this.entities.cursor = data.nextCursor || null;
          this.entities.nextCursor = data.nextCursor || null;

          if ('total' in data) {
            this.entities.total = data.total;
          }

          const hasMore = !!data.nextCursor;

          options?.done?.(hasMore ? 'ok' : 'empty');
        })
        .catch((err) => {
          console.error('Entity load failed:', err);
          options?.done?.('error');
        })
        .finally(() => {
          this.entities.loading = false;
        });
    },

    toggleEntityDrawer() {
      this.entities.drawer = !this.entities.drawer;

      this.$refs.mobilityMapRef.tooltip.visible = false;

      if (!this.entities.drawer) {
        this.$emit('closeEntityDetails');
        this.entities.selected = null;
      }
    },

    onEntityClick(entity) {
      this.$emit('showEntityDetails', entity);
      this.entities.selected = entity;
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
          v-model="localSearch"
          @keydown.enter="
            $emit('update:search', localSearch);
            $emit('doSearch');
          "
          @click:append-inner="
            localSearch = '';
            $emit('update:search', '');
            $emit('resetSearch')
          "
          append-icon="mdi-ballot"
          :append-inner-icon="!localSearch ? '' : 'mdi-close'"
          @click:append="$emit('advancedSearch')"
          prepend-inner-icon="mdi-magnify"
          :label="translations.search_"
        />
        <v-menu v-if="uniqueEventTypes.length > 1" :close-on-content-click="false">
          <template v-slot:activator="{ props: menuProps }">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props: tooltipProps }">
                <v-btn
                  v-bind="{ ...menuProps, ...tooltipProps }"
                  icon="mdi-tag-multiple"
                  variant="text"
                  density="compact"
                  class="ml-4"
                />
              </template>
              {{ translations.showOrHideEventTypes_ }}
            </v-tooltip>
          </template>

          <v-list
            v-model:selected="selectedEventTypes"
            select-strategy="leaf"
          >
            <v-list-item
              v-for="(eventType, index) in uniqueEventTypes"
              :key="index"
              :title="eventType"
              :value="eventType"
            >
              <template v-slot:prepend="{ isSelected, select }">
                <v-list-item-action start>
                  <v-checkbox-btn
                    :model-value="isSelected"
                    @update:model-value="select"
                  />
                </v-list-item-action>
              </template>
            </v-list-item>
          </v-list>
        </v-menu>

        <!-- Right: Close -->
        <div class="w-33 mr-4 d-flex">
          <v-spacer></v-spacer>
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="$emit('update:open', false); $emit('closeEntityDetails');"
          />
        </div>
      </v-toolbar>
      
      <!-- MAP + OVERLAYS -->
      <v-container fluid class="pa-0 fill-height">
        <!-- MAP -->
        <mobility-map
          v-if="open"
          ref="mobilityMapRef"
          :locations="computedMapData.locations"
          :flows="computedMapData.flows"
          class="w-100 h-100"
          :viewport-padding="{ right: entities.drawer ? drawerWidth : 0, top: navHeight }"
          :disable-clustering="Boolean(entities.selected)"
          :mode="Boolean(entities.selected) ? 'event' : null"
        />

        <!-- LOADING OVERLAY -->
        <v-overlay
          :model-value="loading || entityLoader"
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
              {{ translations.retry_ }}
            </v-btn>

          </v-card>
        </div>

        <!-- Drawer -->
        <v-navigation-drawer
          v-model="entities.drawer"
          location="right"
          :width="drawerWidth"
          :scrim="false"
          temporary
        >
          <!-- Toggle button that sticks out -->
          <v-card class="position-absolute pa-1" :style="{ left: '-48px', top: '50%', transform: 'translateY(-50%)', borderRadius: '12px 0 0 12px' }">
            <v-btn icon size="small" @click="toggleEntityDrawer()">
              <v-icon>
                {{ entities.drawer ? 'mdi-chevron-right' : 'mdi-chevron-left' }}
              </v-icon>
            </v-btn>
          </v-card>

          <!-- Content -->
          <v-container class="pt-0">
            <v-infinite-scroll ref="infiniteScroll" class="overflow-visible" :empty-text="!entities.items?.length ? translations.noItemsAvailable_ : translations.noMoreItemsToLoad_" :items="entities.items" @load="loadEntities({ ...$event })">
              <v-card
                v-for="entity in entities.items"
                :key="entity.id"
                class="mb-2 pa-4 rounded-lg"
                elevation="2"
                @click="onEntityClick(entity)"
              >
                <div class="d-flex align-center ga-2">
                  <v-chip> {{ translations.id_ }} {{ entity.id }} </v-chip>
                  <span class="text-subtitle-2 font-weight-medium">
                    {{ entity.name }}
                  </span>
                </div>
              </v-card>
            </v-infinite-scroll>
          </v-container>
        </v-navigation-drawer>
      </v-container>
    </v-dialog>
  `,
});
