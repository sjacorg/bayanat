const LocationSearchBox = Vue.defineComponent({
  props: {
    modelValue: {
      type: Object,
      required: true,
    },
  },

  data: () => {
    return {
      translations: window.translations,
      q: {},
      openPanels: ['0'],
    };
  },

  watch: {
    q: {
      handler(newVal) {
        this.$emit("update:modelValue", newVal);
      },
      deep: true,
    },
    modelValue: function (newVal, oldVal) {
      if (newVal !== oldVal) {
        this.q = newVal;
      }
    },
  },

  created() {
    this.q = this.modelValue;
  },

  computed: {
    textSearchCount() {
      let count = 0;
      if (this.q.title) count++;
      if (this.q.tsv) count++;
      return count;
    },

    detailsCount() {
      let count = 0;
      if (this.q.location_type) count++;
      if (this.q.admin_level) count++;
      if (this.q.country) count++;
      if (this.q.tags?.length) count++;
      return count;
    },

    geoCount() {
      let count = 0;
      if (this.q.latlng) count++;
      return count;
    },

    totalActiveFilters() {
      return this.textSearchCount + this.detailsCount + this.geoCount;
    },
  },

  template: /* html */ `
    <v-sheet>
      <v-card>
        <v-toolbar :title="translations.searchLocations_">
          <template #append>
            <v-btn icon="mdi-close" @click="$emit('close')"></v-btn>
          </template>
        </v-toolbar>

        <div class="search-box-redesign">
          <!-- Active filters summary -->
          <v-sheet v-if="totalActiveFilters > 0" class="mx-4 mt-3 pa-3 rounded-lg d-flex align-center" color="primary" variant="tonal">
            <v-icon size="small" class="me-2">mdi-filter-check</v-icon>
            <span class="text-body-2 font-weight-medium">{{ translations.activeFiltersCount_(totalActiveFilters) }}</span>
          </v-sheet>

          <!-- Collapsible search sections -->
          <v-expansion-panels v-model="openPanels" multiple variant="accordion" class="search-panels mt-3 px-4 pb-4">

            <!-- 1. TEXT SEARCH -->
            <v-expansion-panel value="0">
              <v-expansion-panel-title>
                <div class="d-flex align-center ga-2 w-100">
                  <v-icon size="small" color="primary">mdi-text-search</v-icon>
                  <span class="text-subtitle-2 font-weight-medium">{{ translations.textSearch_ }}</span>
                  <v-badge v-if="textSearchCount > 0" :content="textSearchCount" color="primary" inline></v-badge>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text eager>
                <v-text-field
                    v-model="q.title"
                    :label="translations.title_"
                    clearable
                    variant="outlined"
                    density="comfortable"
                    prepend-inner-icon="mdi-format-title"
                    @keydown.enter="$emit('search', q)"
                    class="mb-1"
                ></v-text-field>

                <v-text-field
                    v-model="q.tsv"
                    :label="translations.description_"
                    clearable
                    variant="outlined"
                    density="comfortable"
                    prepend-inner-icon="mdi-text"
                ></v-text-field>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- 2. DETAILS -->
            <v-expansion-panel value="1">
              <v-expansion-panel-title>
                <div class="d-flex align-center ga-2 w-100">
                  <v-icon size="small" color="primary">mdi-details</v-icon>
                  <span class="text-subtitle-2 font-weight-medium">{{ translations.details_ }}</span>
                  <v-badge v-if="detailsCount > 0" :content="detailsCount" color="primary" inline></v-badge>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text eager>
                <search-field
                    v-model="q.location_type"
                    api="/admin/api/location-types/"
                    item-title="title"
                    item-value="id"
                    :multiple="false"
                    :label="translations.locationType_"
                ></search-field>

                <search-field
                    api="/admin/api/location-admin-levels/"
                    item-title="title"
                    item-value="id"
                    v-model="q.admin_level"
                    :multiple="false"
                    :label="translations.adminLevel_"
                ></search-field>

                <search-field
                    v-model="q.country"
                    api="/admin/api/countries/"
                    item-title="title"
                    item-value="id"
                    :multiple="false"
                    clearable
                    :label="translations.country_"
                ></search-field>

                <v-combobox
                    v-model="q.tags"
                    :label="translations.tags_"
                    multiple
                    chips
                    closable-chips
                    small-chips
                    clearable
                    variant="outlined"
                    density="comfortable"
                    prepend-inner-icon="mdi-tag-multiple"
                ></v-combobox>
                <div class="d-flex align-center mt-n2">
                  <v-checkbox :label="translations.any_" density="compact" v-model="q.optags" color="primary" class="me-4" hide-details></v-checkbox>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- 3. GEOSPATIAL -->
            <v-expansion-panel value="2">
              <v-expansion-panel-title>
                <div class="d-flex align-center ga-2 w-100">
                  <v-icon size="small" color="primary">mdi-map-marker-radius</v-icon>
                  <span class="text-subtitle-2 font-weight-medium">{{ translations.geospatial_ }}</span>
                  <v-badge v-if="geoCount > 0" :content="geoCount" color="primary" inline></v-badge>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <geo-map
                    class="flex-grow-1"
                    v-model="q.latlng"
                    :map-height="200"
                    :radius-controls="true"
                />
              </v-expansion-panel-text>
            </v-expansion-panel>

          </v-expansion-panels>
        </div>
      </v-card>

      <!-- Action buttons -->
      <v-card tile elevation="10" color="grey-lighten-5">
        <v-card-text class="d-flex justify-center ga-3">
          <v-btn @click="q = {}" variant="text">{{ translations.clearSearch_ }}</v-btn>
          <v-btn @click="$emit('search', q)" color="primary" variant="elevated" prepend-icon="mdi-magnify">{{ translations.search_ }}</v-btn>
        </v-card-text>
      </v-card>

    </v-sheet>
  `,
});