const LabelSearchField = Vue.defineComponent({
  extends: SearchField,
  props: {
    itemTitle: { type: String, default: 'title' },
    itemValue: { type: String, default: 'id' },
    itemSubtitle: { type: String, default: 'path' },
  },
  computed: {
    labelQueryParams() {
      return {
        ...this.queryParams,
        mode: this.queryParams.mode ?? 2,
      };
    },
    selectedDuplicateLeaves() {
      if (!window.LabelPathUtils) return [];
      const selectedItems = Array.isArray(this.modelValue)
        ? this.modelValue
        : [this.modelValue].filter(Boolean);
      const counts = {};
      selectedItems.forEach(item => {
        const key = window.LabelPathUtils.leafKey(item);
        if (key) counts[key] = (counts[key] || 0) + 1;
      });
      return Object.keys(counts).filter(key => counts[key] > 1);
    },
  },
  methods: {
    isLabelPathItem(item) {
      return Boolean(window.LabelPathUtils && item);
    },
    itemPrimaryTitle(item) {
      return this.isLabelPathItem(item) ? window.LabelPathUtils.title(item) : item?.title || '';
    },
    itemSecondaryTitle(item) {
      return this.isLabelPathItem(item) ? window.LabelPathUtils.secondaryTitle(item) : '';
    },
    itemCollapsedPath(item) {
      return this.isLabelPathItem(item) ? window.LabelPathUtils.collapsedPath(item) : '';
    },
    selectionTitle(item) {
      return this.isLabelPathItem(item) ? window.LabelPathUtils.title(item) : item?.title || item || '';
    },
    selectionHasPath(item) {
      return this.selectionParts(item).hasPath;
    },
    selectionMarkerIcon() {
      return this.selectionParts().markerIcon;
    },
    selectionIsRtl() {
      return this.selectionParts().isRtl;
    },
    selectionLeaf(item) {
      return this.selectionParts(item).leaf;
    },
    selectionParent(item) {
      return this.selectionParts(item).parent;
    },
    selectionShowsParent(item) {
      return this.selectionParts(item).showParent;
    },
    selectionParts(item = null) {
      if (!this.isLabelPathItem(item)) {
        return {
          hasPath: false,
          isRtl: Boolean(window.LabelPathUtils?.isRtl()),
          leaf: this.selectionTitle(item),
          markerIcon: window.LabelPathUtils?.isRtl() ? 'mdi-chevron-left' : 'mdi-chevron-right',
          parent: '',
          showParent: false,
        };
      }
      return window.LabelPathUtils.chipParts(item, this.selectedDuplicateLeaves);
    },
    debouncedSearch: debounce(function (search) {
      this.loading = true;
      api
        .get('/admin/api/labels/', {
          params: {
            q: search,
            ...this.labelQueryParams,
            per_page: 100,
          },
        })
        .then((response) => {
          this.items = this._mergeSelected(response.data.items);
        })
        .catch(console.error)
        .finally(() => {
          this.loading = false;
        });
    }, 350),
  },
  template: `
    <v-autocomplete
      ref="autocomplete"
      :disabled="disabled"
      :menu-props="{ offsetY: true }"
      :auto-select-first="true"
      :model-value="modelValue"
      @update:model-value="onSelect"
      v-model:search="searchQuery"
      @update:focused="onFocused"
      :hide-no-data="loading"
      hide-selected
      no-filter
      item-color="secondary"
      :label="label"
      :items="filteredItems"
      :item-title="itemTitle"
      :item-value="itemValue"
      prepend-inner-icon="mdi-magnify"
      :multiple="multiple"
      chips
      :closable-chips="multiple"
      clearable
      clear-on-select
      :return-object="returnObject"
      v-bind="$attrs"
      :loading="loading"
      :rules="rules"
    >
      <template v-slot:item="{ item, props }">
        <v-list-item v-bind="props" density="compact">
          <template v-if="multiple" v-slot:prepend="{ isActive }">
            <v-checkbox-btn :model-value="isActive" density="compact" tabindex="-1" style="pointer-events: none;"></v-checkbox-btn>
          </template>
          <template v-slot:title>
            <span class="text-body-2">{{ itemPrimaryTitle(item.raw) }}</span>
            <span v-if="itemSecondaryTitle(item.raw)" class="d-block text-caption text-medium-emphasis">
              {{ itemSecondaryTitle(item.raw) }}
            </span>
          </template>
          <template v-if="itemCollapsedPath(item.raw)" v-slot:subtitle>
            <span class="text-caption text-grey">{{ itemCollapsedPath(item.raw) }}</span>
          </template>
        </v-list-item>
      </template>
      <template v-slot:chip="{ item, props }">
        <v-chip v-bind="props" size="small" class="text-no-wrap">
          <template v-if="selectionHasPath(item.raw)">
            <span class="text-medium-emphasis text-no-wrap">...</span>
            <v-icon :icon="selectionMarkerIcon()" size="14" class="text-medium-emphasis me-1"></v-icon>
          </template>
          <template v-if="selectionShowsParent(item.raw)">
            <span v-if="selectionIsRtl()">{{ selectionLeaf(item.raw) }}</span>
            <span v-else>{{ selectionParent(item.raw) }}</span>
            <v-icon :icon="selectionMarkerIcon()" size="14" class="mx-1"></v-icon>
            <span v-if="selectionIsRtl()">{{ selectionParent(item.raw) }}</span>
            <span v-else>{{ selectionLeaf(item.raw) }}</span>
          </template>
          <template v-else>
            {{ selectionTitle(item.raw) }}
          </template>
        </v-chip>
      </template>
      <template v-if="showCopyIcon" v-slot:append>
        <v-btn icon="mdi-content-copy" variant="plain" @click="copyValue"></v-btn>
      </template>
    </v-autocomplete>
  `,
});
