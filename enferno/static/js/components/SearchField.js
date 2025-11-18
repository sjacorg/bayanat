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
  },
  emits: ['update:model-value'],
  data: () => ({
    loading: false,
    items: [],
    searchQuery: '',
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
          this.items = response.data.items;
        })
        .catch(console.error)
        .finally(() => {
          this.loading = false;
        });
    }, 350),
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
    searchQuery(nextSearchQuery) {
      this.startSearch(nextSearchQuery)
    }
  },
  template: `
    <v-autocomplete
      :disabled="disabled"
      :menu-props="{ offsetY: true }"
      :auto-select-first="true"
      :model-value="modelValue"
      @update:model-value="$emit('update:model-value', $event)"
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
          this.items = response.data.items;
        }).finally(() => {
          this.loading = false;
        });
    }, 350),
  },
});