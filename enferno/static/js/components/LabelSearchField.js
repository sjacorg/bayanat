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
    selectionParts(item = null) {
      if (!this.isLabelPathItem(item)) {
        return {
          hasPath: false,
          isRtl: Boolean(window.LabelPathUtils?.isRtl()),
          leaf: item?.title || item || '',
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
        <!-- One-item loop keeps selectionParts readable and avoids recalculating it in this slot. -->
        <template v-for="parts in [selectionParts(item.raw)]">
          <v-chip v-bind="props" size="small" class="text-no-wrap">
            <template v-if="parts.hasPath">
              <span class="text-medium-emphasis text-no-wrap">...</span>
              <v-icon :icon="parts.markerIcon" size="14" class="text-medium-emphasis me-1"></v-icon>
            </template>
            <template v-if="parts.showParent">
              <span v-if="parts.isRtl">{{ parts.leaf }}</span>
              <span v-else>{{ parts.parent }}</span>
              <v-icon :icon="parts.markerIcon" size="14" class="mx-1"></v-icon>
              <span v-if="parts.isRtl">{{ parts.parent }}</span>
              <span v-else>{{ parts.leaf }}</span>
            </template>
            <template v-else>
              {{ parts.leaf }}
            </template>
          </v-chip>
        </template>
      </template>
      <template v-if="showCopyIcon" v-slot:append>
        <v-btn icon="mdi-content-copy" variant="plain" @click="copyValue"></v-btn>
      </template>
    </v-autocomplete>
  `,
});
