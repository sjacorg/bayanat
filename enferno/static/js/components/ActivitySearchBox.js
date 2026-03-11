const ActivitySearchBox = Vue.defineComponent({
  props: {
    modelValue: {
      type: Object,
      required: true,
    },
  },

  mixins: [globalMixin],

  emits: ['update:modelValue', 'search', 'close'],

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
        this.$emit('update:modelValue', newVal);
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
    filtersCount() {
      let count = 0;
      if (this.q.user) count++;
      if (this.q.model) count++;
      if (this.q.action) count++;
      return count;
    },

    dateCount() {
      let count = 0;
      if (this.q.created) count++;
      return count;
    },

    totalActiveFilters() {
      return this.filtersCount + this.dateCount;
    },
  },

  template: /* html */ `
    <v-sheet>
      <v-card>
        <v-toolbar :title="translations.searchActivities_">
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

          <v-expansion-panels v-model="openPanels" multiple variant="accordion" class="search-panels mt-3 px-4 pb-4">

            <!-- 1. FILTERS (User, Type, Action) -->
            <v-expansion-panel value="0">
              <v-expansion-panel-title>
                <div class="d-flex align-center ga-2 w-100">
                  <v-icon size="small" color="primary">mdi-filter</v-icon>
                  <span class="text-subtitle-2 font-weight-medium">{{ translations.filters_ }}</span>
                  <v-badge v-if="filtersCount > 0" :content="filtersCount" color="primary" inline></v-badge>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text eager>

                <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.USER_ }}</div>
                <v-chip-group column v-model="q.user" selected-class="text-primary" class="mb-3">
                  <v-chip :value="user.id" size="small" v-for="user in $root.users" filter variant="outlined" :key="user.id">{{ user.display_name }}</v-chip>
                </v-chip-group>

                <v-divider class="my-3"></v-divider>

                <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.SELECTTYPE_ }}</div>
                <v-chip-group column v-model="q.model" selected-class="text-primary" class="mb-3">
                  <v-chip size="small" v-for="item in $root.models" :value="item" filter variant="outlined" :key="item">{{ item }}</v-chip>
                </v-chip-group>

                <v-divider class="my-3"></v-divider>

                <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.SELECTACTION_ }}</div>
                <v-chip-group column v-model="q.action" selected-class="text-primary">
                  <v-chip size="small" v-for="action in $root.actionTypes" :value="action" filter variant="outlined" :key="action">{{ action }}</v-chip>
                </v-chip-group>

              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- 2. DATES -->
            <v-expansion-panel value="1">
              <v-expansion-panel-title>
                <div class="d-flex align-center ga-2 w-100">
                  <v-icon size="small" color="primary">mdi-calendar-range</v-icon>
                  <span class="text-subtitle-2 font-weight-medium">{{ translations.dates_ }}</span>
                  <v-badge v-if="dateCount > 0" :content="dateCount" color="primary" inline></v-badge>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text eager>
                <pop-date-range-field
                    :label="translations.activityDate_"
                    v-model="q.created"
                ></pop-date-range-field>
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