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
    // Field holding the translated title (e.g. 'title_ar' or 'title_tr').
    // When null, a '<itemTitle>_ar' / '<itemTitle>_tr' key on the fetched items
    // is picked up automatically. The user's interface language decides which
    // language renders as the primary text and which as the secondary one.
    itemTranslation: {
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
    isArabic() {
      return window.__lang__ === 'ar';
    },
  },
  methods: {
    translationField(raw) {
      if (this.itemTranslation) return this.itemTranslation;
      if (!raw) return null;
      for (const suffix of ['_ar', '_tr']) {
        const key = this.itemTitle + suffix;
        if (key in raw) return key;
      }
      return null;
    },
    primaryTitle(raw) {
      const field = this.translationField(raw);
      const translated = field ? raw[field] : null;
      if (this.isArabic && translated) return translated;
      return raw[this.itemTitle] || translated || '';
    },
    secondaryTitle(raw) {
      const field = this.translationField(raw);
      const translated = field ? raw[field] : null;
      if (!translated || !raw[this.itemTitle]) return null;
      return this.isArabic ? raw[this.itemTitle] : translated;
    },
    localizedItemTitle(item) {
      if (item == null || typeof item !== 'object') return item;
      return this.primaryTitle(item);
    },
    subtitleText(raw) {
      if (!this.itemSubtitle) return null;
      let text = raw[this.itemSubtitle];
      if (this.isArabic && raw[this.itemSubtitle + '_ar']) {
        text = raw[this.itemSubtitle + '_ar'];
      }
      return this.collapsePath(text);
    },
    collapsePath(text) {
      if (!text) return text;
      const parts = String(text).split(' > ');
      if (parts.length <= 3) return text;
      return [parts[0], '…', parts[parts.length - 1]].join(' > ');
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
      :item-title="localizedItemTitle"
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
      <template v-slot:chip="{ item, props }">
        <v-chip v-bind="props" label style="height: auto;">
          <span class="d-flex flex-column py-1">
            <bdi class="text-body-2">{{ primaryTitle(item.raw) }}</bdi>
            <bdi v-if="secondaryTitle(item.raw)" class="text-caption text-medium-emphasis">{{ secondaryTitle(item.raw) }}</bdi>
          </span>
        </v-chip>
      </template>
      <template v-slot:item="{ item, props }">
        <v-list-item v-bind="props" density="compact">
          <template v-if="multiple" v-slot:prepend="{ isActive }">
            <v-checkbox-btn :model-value="isActive" density="compact" tabindex="-1" style="pointer-events: none;"></v-checkbox-btn>
          </template>
          <template v-slot:title>
            <span class="text-body-2">
              <bdi>{{ primaryTitle(item.raw) }}</bdi><template v-if="secondaryTitle(item.raw)"> · <bdi class="text-caption text-grey">{{ secondaryTitle(item.raw) }}</bdi></template>
            </span>
          </template>
          <template v-if="subtitleText(item.raw)" v-slot:subtitle>
            <span class="text-caption text-grey"><bdi>{{ subtitleText(item.raw) }}</bdi></span>
          </template>
        </v-list-item>
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
