const SearchField = Vue.defineComponent({
  props: {
    modelValue: {
      type: [String, Number, Object, Array],
      default: null,
    },
    label: String,
    multiple: Boolean,
    itemTitle: String,
    itemValue: String,
    api: String,
    queryParams: {
      type: Object,
      default: () => ({}),
    },
    filterItems: {
      type: Function,
      default: null,
    },
    disabled: Boolean,
    returnObject: {
      type: Boolean,
      default: true,
    },
    rules: {
      type: Array,
      default: () => [(v) => true],
    },
    showCopyIcon: {
      type: Boolean,
      default: false,
    },
    itemSubtitle: {
      type: String,
      default: null,
    },
    retainSearch: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['update:model-value'],
  data: () => ({
    loading: false,
    items: [],
    searchQuery: '',
    _justSelected: false,
  }),
  computed: {
    filteredItems() {
      if (typeof this.filterItems === 'function') {
        return this.filterItems(this.items);
      }
      return this.items;
    },
    hasLabelPathSupport() {
      return Boolean(window.LabelPathUtils);
    },
    supportsLabelPaths() {
      return this.hasLabelPathSupport
        && this.api === '/admin/api/labels/'
        && this.itemSubtitle === 'path';
    },
    selectedDuplicateLeaves() {
      if (!this.supportsLabelPaths) return [];
      const selectedItems = Array.isArray(this.modelValue)
        ? this.modelValue
        : [this.modelValue].filter(Boolean);
      const counts = {};
      selectedItems.forEach(item => {
        if (!this.isLabelPathItem(item)) return;
        const key = window.LabelPathUtils.leafKey(item);
        if (key) counts[key] = (counts[key] || 0) + 1;
      });
      return Object.keys(counts).filter(key => counts[key] > 1);
    },
  },
  methods: {
    isLabelPathItem(item) {
      return this.supportsLabelPaths && (item?.path || item?.path_ar || item?.path_tr || item?.title_ar || item?.title_tr);
    },
    itemPrimaryTitle(item) {
      if (this.isLabelPathItem(item)) {
        return window.LabelPathUtils.title(item);
      }
      return item?.[this.itemTitle] || '';
    },
    itemSecondaryTitle(item) {
      if (!this.isLabelPathItem(item)) return '';
      return window.LabelPathUtils.secondaryTitle(item);
    },
    itemCollapsedPath(item) {
      if (this.isLabelPathItem(item)) {
        return window.LabelPathUtils.collapsedPath(item);
      }
      return this.itemSubtitle ? item?.[this.itemSubtitle] : '';
    },
    selectionTitle(item) {
      if (this.isLabelPathItem(item)) {
        return window.LabelPathUtils.title(item);
      }
      return item?.[this.itemTitle] || item || '';
    },
    selectionHasPath(item) {
      return this.isLabelPathItem(item) && window.LabelPathUtils.hasPath(item);
    },
    selectionMarkerIcon() {
      return window.LabelPathUtils?.isRtl() ? 'mdi-chevron-left' : 'mdi-chevron-right';
    },
    selectionIsRtl() {
      return Boolean(window.LabelPathUtils?.isRtl());
    },
    selectionLeaf(item) {
      return this.isLabelPathItem(item) ? window.LabelPathUtils.title(item) : this.selectionTitle(item);
    },
    selectionParent(item) {
      return this.isLabelPathItem(item) ? window.LabelPathUtils.parentTitle(item) : '';
    },
    selectionShowsParent(item) {
      return this.selectionHasPath(item)
        && this.selectionParent(item)
        && (
          window.LabelPathUtils.isGenericLeaf(item)
          || this.selectedDuplicateLeaves.includes(window.LabelPathUtils.leafKey(item))
        );
    },
    startSearch(search) {
      this.loading = true;
      this.debouncedSearch(search);
    },
    debouncedSearch: debounce(function (search) {
      api
        .get(this.api, {
          params: {
            q: search,
            ...this.queryParams,
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
    _mergeSelected(fetchedItems) {
      if (!this.multiple || !Array.isArray(this.modelValue) || !this.modelValue.length) {
        return fetchedItems;
      }
      const fetchedIds = new Set(fetchedItems.map(i => this.returnObject ? i[this.itemValue] : i));
      const missing = this.modelValue.filter(v => {
        const key = this.returnObject ? v[this.itemValue] : v;
        return !fetchedIds.has(key);
      });
      return [...missing, ...fetchedItems];
    },
    onSelect(val) {
      if (this.retainSearch) {
        this._justSelected = true;
      }
      this.$emit('update:model-value', val);

      // Refocus the input after selection so user can keep typing
      if (this.multiple) {
        this.$refs.autocomplete.focus()
      }
    },
    copyValue() {
      let textToCopy = '';
      if (this.multiple && Array.isArray(this.modelValue)) {
        textToCopy = this.modelValue
          .map(item => this.returnObject ? item[this.itemTitle] : item)
          .join(', ');
      } else if (this.returnObject && typeof this.modelValue === 'object') {
        textToCopy = this.modelValue?.[this.itemTitle] || '';
      } else {
        textToCopy = this.modelValue || '';
      }

      navigator.clipboard.writeText(textToCopy).then(() => {
        this.$root?.showSnack?.('Copied to clipboard');
      }).catch(console.error);
    },
    onFocused(focused) {
      if (focused) this.startSearch(this.searchQuery)
      else this.loading = false
    }
  },
  watch: {
    searchQuery(val) {
      // After selection with retainSearch, search clears automatically.
      // Skip the refetch so results stay visible for picking more items.
      if (this.retainSearch && this._justSelected && !val) {
        this._justSelected = false;
        this.loading = false;
        return;
      }
      this._justSelected = false;
      this.startSearch(val);
    }
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
      <template v-if="itemSubtitle || supportsLabelPaths" v-slot:item="{ item, props }">
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
      <template v-if="supportsLabelPaths" v-slot:chip="{ item, props }">
        <v-chip v-bind="props" size="small" class="text-no-wrap">
          <template v-if="selectionHasPath(item.raw)">
            <span class="text-medium-emphasis text-no-wrap">…</span>
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

const LocationSearchField = Vue.defineComponent({
  extends: SearchField,
  methods: {
    debouncedSearch: debounce(function (search) {
      this.loading = true;
      api
        .post(this.api, {
          q: {
            ...this.queryParams,
            title: search,
          },
          options: {},
        })
        .then((response) => {
          this.items = this._mergeSelected(response.data.items);
        }).finally(() => {
          this.loading = false;
        });
    }, 350),
  },
});
