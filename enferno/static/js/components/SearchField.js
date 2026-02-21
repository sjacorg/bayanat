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
  methods: {
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
      :disabled="disabled"
      :menu-props="{ offsetY: true }"
      :auto-select-first="false"
      :model-value="modelValue"
      @update:model-value="onSelect"
      v-model:search="searchQuery"
      @update:focused="onFocused"
      hide-no-data
      no-filter
      item-color="secondary"
      :label="label"
      :items="items"
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
      <template v-if="itemSubtitle" v-slot:item="{ item, props }">
        <v-list-item v-bind="props" density="compact">
          <template v-if="multiple" v-slot:prepend="{ isActive }">
            <v-checkbox-btn :model-value="isActive" density="compact" tabindex="-1" style="pointer-events: none;"></v-checkbox-btn>
          </template>
          <template v-slot:title>
            <span class="text-body-2">{{ item.raw[itemTitle] }}</span>
          </template>
          <template v-if="item.raw[itemSubtitle]" v-slot:subtitle>
            <span class="text-caption text-grey">{{ item.raw[itemSubtitle] }}</span>
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
