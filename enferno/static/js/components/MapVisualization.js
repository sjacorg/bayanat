const MapVisualization = Vue.defineComponent({
  props: {
    open: Boolean,
    visualizeEndpoint: { type: String, default: '/admin/api/flowmap/visualize' },
    statusEndpoint: { type: String, default: '/admin/api/flowmap/status' },
    dataEndpoint: { type: String, default: '/admin/api/flowmap/data' },
    entitiesEndpoint: { type: String, default: '/admin/api/actors/' },
    actorsForLocationsEndpoint: { type: String, default: '/admin/api/flowmap/actors-for-locations' },
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

    localSearch: '',

    loading: false,
    loadingMessage: '',
    errorMessage: '',

    locations: [],
    flows: [],

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

    // Location-based actor drawer state
    locationActors: {
      active: false,
      loading: false,
      items: [],
      total: null,
      label: '',
      // Node-specific: store clicked node info for Total In/Out buttons
      nodeInfo: null,
      // Current filter mode: 'all' | 'in' | 'out'
      filterMode: 'all',
    },
  }),

  watch: {
    open(isOpen) {
      if (isOpen) {
        this.localSearch = this.search;
        this.resetEntities();
        this.initMapFlow();
        this.entities.drawer = false;
        this.clearLocationActors();
      }
    },

    query: {
      deep: true,
      handler() {
        this.resetEntities();
        this.clearLocationActors();
        this.$emit('closeEntityDetails');
      },
    },

    selectedEventTypes() {
      this.clearLocationActors();
      this.entities.drawer = false;
    },
  },

  computed: {
    selectedEntityMapData() {
      if (!this.entities.selected) return null;
      if (this.entityLoader) return null;

      return MobilityMapUtils.parseEventsToMapData(this.entity?.events);
    },
    computedMapData() {
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
    applyAllEventTypes() {
      this.selectedEventTypes = [...this.uniqueEventTypes];
    },
    matchesSelectedEventTypes(entity) {
      if (!this.selectedEventTypes.length) return true;

      const types = Object.keys(entity.events_by_type || {});
      if (!types.length) return true;

      return types.some(type =>
        this.selectedEventTypes.includes(type)
      );
    },

    filterMapData(baseData) {
      const { locations = [], flows = [] } = baseData;

      const visibleFlows = flows
        .filter(this.matchesSelectedEventTypes)
        .map(flow => ({
          ...flow,
          count: Object.values(flow.events_by_type || {})
            .reduce((sum, value) => sum + value, 0),
        }));

      const requiredLocationIds = new Set();
      visibleFlows.forEach(flow => {
        requiredLocationIds.add(flow.origin);
        requiredLocationIds.add(flow.dest);
      });

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

      this.applyAllEventTypes();

      this.loading = false;
    },

    async fetchData() {
      this.loading = true;
      this.loadingMessage = this.translations.startingGeneration_;

      try {
        const start = await api.post(this.visualizeEndpoint, { q: this.query });
        const taskId = start?.data?.task_id;

        if (!taskId) {
          throw new Error('MobilityMap generation failed.');
        }

        this.loadingMessage = this.translations.waitingForMapGeneration_;

        const statusResult = await MobilityMapUtils.pollUntilDone(
          async () => {
            const res = await api.get(this.statusEndpoint);
            return {
              status: res?.data?.status,
              error: res?.data?.error,
            };
          },
          { interval: 1500, timeout: 60000 },
        );

        if (statusResult.status === 'error') {
          throw new Error(statusResult.error || 'Map generation error.');
        }

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
        return { locations: [], flows: [] };
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

      this.$nextTick(() => {
        this.$refs?.infiniteScroll?.reset();
      });
    },

    loadEntities(options) {
      if (this.locationActors.active) {
        options?.done?.('empty');
        return;
      }

      if (this.entities.loading) return;
      this.entities.loading = true;

      const payload = {
        q: this.query,
        per_page: this.entities.perPage,
        cursor: this.entities.cursor,
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

          this.entities.cursor = data.nextCursor || null;
          this.entities.nextCursor = data.nextCursor || null;

          if ('total' in data) {
            this.entities.total = data.total;
          }

          options?.done?.(data.nextCursor ? 'ok' : 'empty');
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
        this.clearLocationActors();
        this.applyAllEventTypes();
      }
    },

    onEntityClick(entity) {
      this.$emit('showEntityDetails', { entity, drawerWidth: this.drawerWidth });
      this.entities.selected = entity;
    },

    /* -------------------------------------------------
       NODE / FLOW CLICK HANDLERS
    ------------------------------------------------- */

    clearLocationActors() {
      this.locationActors.active = false;
      this.locationActors.loading = false;
      this.locationActors.items = [];
      this.locationActors.total = null;
      this.locationActors.label = '';
      this.locationActors.nodeInfo = null;
      this.locationActors.filterMode = 'all';
    },

    /**
     * Called when user clicks a node on the map.
     * Opens the drawer with location info header + actors.
     */
    onNodeClicked(data) {
      // { locationIds, label, totalIn, totalOut, incomingOriginIds, outgoingDestIds }

      this.clearLocationActors();
      this.locationActors.active = true;
      this.locationActors.label = data.label;
      this.locationActors.filterMode = 'all';
      this.locationActors.nodeInfo = {
        locationIds: data.locationIds,
        totalIn: data.totalIn,
        totalOut: data.totalOut,
        incomingOriginIds: data.incomingOriginIds,
        outgoingDestIds: data.outgoingDestIds,
      };

      if (this.entities.selected) {
        this.$emit('closeEntityDetails');
        this.entities.selected = null;
      }

      this.entities.drawer = true;

      // Load all actors at this location
      this.fetchActorsForNode('all');
    },

    /**
     * Called when user clicks a flow arrow on the map.
     * Opens the drawer with actors who made that directional movement.
     */
    onFlowClicked(data) {
      // { originIds, destIds, label, count }

      this.clearLocationActors();
      this.locationActors.active = true;
      this.locationActors.label = data.label;
      this.locationActors.filterMode = 'all';
      this.locationActors.nodeInfo = null;

      if (this.entities.selected) {
        this.$emit('closeEntityDetails');
        this.entities.selected = null;
      }

      this.entities.drawer = true;

      // Load actors for this directional flow
      this.fetchActorsForFlow(data.originIds, data.destIds);
    },

    /**
     * Fetch actors for a node. Mode: 'all' | 'in' | 'out'
     */
    async fetchActorsForNode(mode) {
      const info = this.locationActors.nodeInfo;
      if (!info) return;

      this.locationActors.filterMode = mode;
      this.locationActors.loading = true;
      this.locationActors.items = [];
      this.locationActors.total = null;

      try {
        let payload;

        // Include selected event types so backend filters accordingly
        const event_types = this.selectedEventTypes.length < this.uniqueEventTypes.length
          ? this.selectedEventTypes
          : null;

        if (mode === 'in') {
          payload = {
            origin_ids: info.incomingOriginIds,
            dest_ids: info.locationIds,
            q: this.query,
            ...(event_types && { event_types }),
          };
        } else if (mode === 'out') {
          payload = {
            origin_ids: info.locationIds,
            dest_ids: info.outgoingDestIds,
            q: this.query,
            ...(event_types && { event_types }),
          };
        } else {
          payload = {
            location_ids: info.locationIds,
            q: this.query,
            ...(event_types && { event_types }),
          };
        }

        const response = await api.post(this.actorsForLocationsEndpoint, payload);
        const data = response.data;
        this.locationActors.items = data.items || [];
        this.locationActors.total = data.total ?? this.locationActors.items.length;
      } catch (err) {
        console.error('Failed to load actors:', err);
        this.$root?.showSnack?.(handleRequestError(err));
        this.locationActors.items = [];
        this.locationActors.total = 0;
      } finally {
        this.locationActors.loading = false;
      }
    },

    /**
     * Fetch actors for a directional flow.
     */
    async fetchActorsForFlow(originIds, destIds) {
      this.locationActors.loading = true;
      this.locationActors.items = [];
      this.locationActors.total = null;

      try {
        const event_types = this.selectedEventTypes.length < this.uniqueEventTypes.length
          ? this.selectedEventTypes
          : null;

        const response = await api.post(this.actorsForLocationsEndpoint, {
          origin_ids: originIds,
          dest_ids: destIds,
          q: this.query,
          ...(event_types && { event_types }),
        });

        const data = response.data;
        this.locationActors.items = data.items || [];
        this.locationActors.total = data.total ?? this.locationActors.items.length;
      } catch (err) {
        console.error('Failed to load flow actors:', err);
        this.$root?.showSnack?.(handleRequestError(err));
        this.locationActors.items = [];
        this.locationActors.total = 0;
      } finally {
        this.locationActors.loading = false;
      }
    },

    backToAllActors() {
      this.clearLocationActors();
      this.resetEntities();
    },
  },

  template: `
    <v-dialog fullscreen class="map-visualization-dialog" :model-value="open">
      <v-toolbar color="primary">
        <div class="w-33 ml-4">
          <v-toolbar-title>
            {{ translations.mapVisualization_ }}
          </v-toolbar-title>
        </div>

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

        <div class="w-33 mr-4 d-flex">
          <v-spacer></v-spacer>
          <v-btn
            icon="mdi-close"
            variant="text"
            @click="$emit('update:open', false); $emit('closeEntityDetails');"
          />
        </div>
      </v-toolbar>
      
      <v-container fluid class="pa-0 fill-height">
        <mobility-map
          v-if="open"
          ref="mobilityMapRef"
          :locations="computedMapData.locations"
          :flows="computedMapData.flows"
          class="w-100 h-100"
          :viewport-padding="{ right: drawerWidth, top: 64 }"
          :disable-clustering="Boolean(entities.selected)"
          :mode="Boolean(entities.selected) ? 'event' : null"
          @node-clicked="onNodeClicked"
          @flow-clicked="onFlowClicked"
        />

        <!-- LOADING OVERLAY -->
        <v-overlay
          :model-value="loading || entityLoader"
          persistent
          contained
          class="d-flex align-center justify-center"
        >
          <v-card elevation="6" rounded="lg" class="pa-6 text-center">
            <v-progress-circular indeterminate color="primary" size="64" />
            <div class="text-subtitle-1 mt-4">{{ loadingMessage }}</div>
          </v-card>
        </v-overlay>

        <!-- ERROR OVERLAY -->
        <div v-if="errorMessage" class="d-flex align-center justify-center fill-height">
          <v-card class="pa-8 text-center" max-width="420">
            <v-icon color="error" size="64" class="mb-4">mdi-alert-circle-outline</v-icon>
            <div class="text-h6 mb-4">{{ errorMessage }}</div>
            <v-btn color="primary" @click="retry">{{ translations.retry_ }}</v-btn>
          </v-card>
        </div>

        <!-- DRAWER -->
        <v-navigation-drawer
          v-model="entities.drawer"
          location="right"
          :width="drawerWidth"
          :scrim="false"
          temporary
        >
          <!-- Toggle button -->
          <v-card class="position-absolute pa-1" :style="{ left: '-48px', top: '50%', transform: 'translateY(-50%)', borderRadius: '12px 0 0 12px' }">
            <v-btn icon size="small" @click="toggleEntityDrawer()">
              <v-icon>{{ entities.drawer ? 'mdi-chevron-right' : 'mdi-chevron-left' }}</v-icon>
            </v-btn>
          </v-card>

          <v-container class="pt-0">

            <!-- ========== LOCATION ACTORS MODE ========== -->
            <template v-if="locationActors.active">

              <!-- Header with back button + location name -->
              <div class="d-flex align-center py-3">
                <v-btn
                  icon="mdi-arrow-left"
                  size="small"
                  variant="text"
                  @click="backToAllActors"
                />
                <div class="ml-2">
                  <div class="text-subtitle-1 font-weight-bold" style="max-width: 280px;">
                    {{ locationActors.label }}
                  </div>
                  <div v-if="locationActors.total != null && !locationActors.loading" class="text-caption text-medium-emphasis">
                    {{ locationActors.total }} {{ locationActors.total === 1 ? (translations.actor_ ?? 'actor') : (translations.actors_ ?? 'actors') }}
                  </div>
                </div>
              </div>

              <!-- Node info: Total In / Total Out buttons -->
              <div v-if="locationActors.nodeInfo" class="d-flex ga-2 mb-3">
                <v-btn
                  variant="tonal"
                  size="small"
                  :color="locationActors.filterMode === 'all' ? 'primary' : undefined"
                  @click="fetchActorsForNode('all')"
                >
                  <v-icon start size="16">mdi-account-group</v-icon>
                  {{ translations.all_ ?? 'All' }}
                </v-btn>
                <v-btn
                  variant="tonal"
                  size="small"
                  :color="locationActors.filterMode === 'in' ? 'primary' : undefined"
                  :disabled="!locationActors.nodeInfo.totalIn"
                  @click="fetchActorsForNode('in')"
                >
                  <v-icon start size="16">mdi-arrow-down</v-icon>
                  {{ translations.totalIn_ ?? 'Total In' }}: {{ locationActors.nodeInfo.totalIn }}
                </v-btn>
                <v-btn
                  variant="tonal"
                  size="small"
                  :color="locationActors.filterMode === 'out' ? 'primary' : undefined"
                  :disabled="!locationActors.nodeInfo.totalOut"
                  @click="fetchActorsForNode('out')"
                >
                  <v-icon start size="16">mdi-arrow-up</v-icon>
                  {{ translations.totalOut_ ?? 'Total Out' }}: {{ locationActors.nodeInfo.totalOut }}
                </v-btn>
              </div>

              <v-divider class="mb-2" />

              <!-- Loading -->
              <div v-if="locationActors.loading" class="d-flex justify-center py-8">
                <v-progress-circular indeterminate color="primary" />
              </div>

              <!-- Actor list -->
              <template v-if="!locationActors.loading">
                <div v-if="!locationActors.items.length" class="text-center text-medium-emphasis py-4">
                  {{ translations.noActorsFound_ ?? 'No actors found.' }}
                </div>

                <v-card
                  v-for="actor in locationActors.items"
                  :key="actor.id"
                  class="mb-2 pa-4 rounded-lg"
                  elevation="2"
                  @click="onEntityClick(actor)"
                >
                  <!-- Actor header -->
                  <div class="d-flex align-center ga-2 mb-2">
                    <v-icon size="18">mdi-account</v-icon>
                    <span class="text-subtitle-2 font-weight-medium">{{ actor.name }}</span>
                    <v-spacer />
                    <v-chip size="x-small" variant="tonal">ID {{ actor.id }}</v-chip>
                  </div>

                  <!-- ========================= -->
                  <!-- LOCATION MODE (timeline) -->
                  <!-- ========================= -->
                  <template v-if="actor.current_event">
                    <div v-if="actor.prev_event" class="text-caption text-medium-emphasis">
                      <strong>Previous:</strong>
                      {{ actor.prev_event.type }} — {{ actor.prev_event.location }}
                    </div>

                    <div class="text-caption mt-1 font-weight-medium text-primary">
                      <strong>Here:</strong>
                      {{ actor.current_event.type }} — {{ actor.current_event.location }}
                    </div>

                    <div v-if="actor.next_event" class="text-caption text-medium-emphasis mt-1">
                      <strong>Next:</strong>
                      {{ actor.next_event.type }} — {{ actor.next_event.location }}
                    </div>
                  </template>

                  <!-- ========================= -->
                  <!-- FLOW MODE -->
                  <!-- ========================= -->
                  <template v-else-if="actor.origin_event || actor.dest_event">
                    <div v-if="actor.origin_event" class="text-caption text-medium-emphasis">
                      <strong>From:</strong>
                      {{ actor.origin_event.type }} — {{ actor.origin_event.location }}
                    </div>

                    <div v-if="actor.dest_event" class="text-caption mt-1 font-weight-medium text-primary">
                      <strong>To:</strong>
                      {{ actor.dest_event.type }} — {{ actor.dest_event.location }}
                    </div>
                  </template>

                  <!-- ========================= -->
                  <!-- FALLBACK -->
                  <!-- ========================= -->
                  <template v-else>
                    <div class="text-caption text-medium-emphasis">
                      Actor has events, but no contextual data available.
                    </div>
                  </template>

                </v-card>
              </template>
            </template>

            <!-- ========== DEFAULT QUERY ACTORS MODE ========== -->
            <template v-else>
              <div class="d-flex align-center py-3">
                <v-icon class="mr-2">mdi-account-group</v-icon>
                <div>
                  <div class="text-subtitle-1 font-weight-bold">
                    {{ translations.actors_ ?? 'Actors' }}
                  </div>
                  <div v-if="entities.total != null" class="text-caption text-medium-emphasis">
                    {{ entities.total }} {{ translations.total_ ?? 'total' }}
                  </div>
                </div>
              </div>
              <v-divider class="mb-2" />

              <v-infinite-scroll
                ref="infiniteScroll"
                class="overflow-visible"
                :empty-text="!entities.items?.length ? translations.noItemsAvailable_ : translations.noMoreItemsToLoad_"
                :items="entities.items"
                @load="loadEntities({ ...$event })"
              >
                <v-card
                  v-for="entity in entities.items"
                  :key="entity.id"
                  class="mb-2 pa-4 rounded-lg"
                  elevation="2"
                  @click="onEntityClick(entity)"
                >
                  <div class="d-flex align-center ga-2">
                    <v-chip>{{ translations.id_ }} {{ entity.id }}</v-chip>
                    <span class="text-subtitle-2 font-weight-medium">{{ entity.name }}</span>
                  </div>
                </v-card>
              </v-infinite-scroll>
            </template>

          </v-container>
        </v-navigation-drawer>
      </v-container>
    </v-dialog>
  `,
});