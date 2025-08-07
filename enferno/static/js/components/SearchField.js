const SearchField = Vue.defineComponent({
  props: {
    modelValue: {
      type: [String, Number, Object, Array],
      default: () => [],
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
  data: () => {
    return {
      loading: false,
      items: [],
      searchInput: '',
    };
  },
  created() {
    this.$nextTick(() => {
      //enable copy paste
      let dateInputs = document.querySelectorAll('[type="date"]');

      dateInputs.forEach((el) => {
        // register double click event to change date input to text input and select the value
        el.addEventListener('dblclick', () => {
          el.type = 'text';
          el.select();
        });

        // register the focusout event to reset the input back to a date input field
        el.addEventListener('focusout', () => {
          el.type = 'date';
        });
      });
    });
  },
  watch: {
    modelValue(val) {
      if (this.multiple && Array.isArray(val)) {
        this.searchInput = '';
      } else if (val && typeof val === 'object') {
        this.searchInput = val[this.itemTitle] || '';
      } else {
        this.searchInput = '';
      }
    },
  },
  computed: {
    checkValue() {
      return this.modelValue === '' ? [] : this.modelValue;
    },
  },
  methods: {
    clearValue() {
      this.searchInput = '';
      this.$emit('update:model-value', this.multiple ? [] : null);
    },
    updateValue(val) {
      // Check value against items list from api
      const isValid = (v) =>
        this.items.some(item =>
          this.returnObject
            ? item[this.itemValue] === v?.[this.itemValue]
            : item[this.itemValue] === v
        );

      if (this.multiple) {
        const current = this.modelValue || [];

        // Filter valid new values
        const validNew = (val || []).filter(v => isValid(v));

        if (validNew.length === 0) {
          // No valid new items, keep current selection
          this.$emit('update:model-value', current);
          return;
        }

        // Add only new items that aren't already selected
        const combined = [...current];
        for (const v of validNew) {
          const exists = combined.some(c =>
            this.returnObject
              ? c[this.itemValue] === v[this.itemValue]
              : c === v
          );
          if (!exists) combined.push(v);
        }

        this.$emit(
          'update:model-value',
          this.returnObject ? combined : combined.map(v => v[this.itemValue])
        );
        return;
      }

      // Single mode: emit if valid or null, else keep current
      if (val === null || isValid(val)) {
        this.$emit('update:model-value', this.returnObject ? val : val?.[this.itemValue]);
      } else {
        this.$emit('update:model-value', this.modelValue);
      }
    },
    search: debounce(function () {
      this.loading = true;
      api
        .get(this.api, {
          params: {
            q: this.searchInput,
            ...this.queryParams,
            per_page: 100,
          },
        })
        .then((response) => {
          this.items = response.data.items;
        })
        .catch((error) => {
          console.error('Error fetching data:', error);
        })
        .finally(() => {
          this.loading = false;
        });
    }, 350),
    copyValue() {
      let textToCopy = '';
      if (this.multiple && Array.isArray(this.modelValue)) {
        textToCopy = this.modelValue.map(item => this.returnObject ? item[this.itemTitle] : item).join(', ');
      } else if (this.returnObject && typeof this.modelValue === 'object') {
        textToCopy = this.modelValue[this.itemTitle] || '';
      } else {
        textToCopy = this.modelValue || '';
      }


      navigator.clipboard.writeText(textToCopy).then(() => {
        // hacky but safe way to show a snackbar
        this.$root?.showSnack?.('Copied to clipboard');
        // You might want to show a notification here that the text was copied
        console.log('Copied to clipboard');
      }).catch(err => {
        console.error('Failed to copy: ', err);
      });
    },
  },
  template: `
    <v-combobox
      variant="outlined"
      ref="fld"
      :disabled="disabled"
      :menu-props="{ offsetY: true }"
      :auto-select-first="true"
      :model-value="checkValue"
      @update:model-value="updateValue"
      :hide-no-data="true"
      :no-filter="true"
      :item-color="'secondary'"
      :label="label"
      :items="items"
      :item-title="itemTitle"
      :item-value="itemValue"
      :prepend-inner-icon="'mdi-magnify'"
      :multiple="multiple"
      :chips="true"
      :closable-chips="true"
      :clearable="true"
      @click:input="search"
      @update:focused="search"
      :return-object="returnObject"
      @click:clear="clearValue"
      v-model:search="searchInput"
      @update:search="search"
      v-bind="$attrs"
      :loading="loading"
      :rules="rules"
      
    >
      <template v-if="showCopyIcon" v-slot:append>
        <v-btn icon="mdi-content-copy" variant="plain" @click="copyValue"></v-btn>
      </template>
    </v-combobox>
  `,
});

const LocationSearchField = Vue.defineComponent({
  extends: SearchField,
  methods: {
    search: debounce(function (evt) {
      api
        .post(this.api, {
          q: {
            ...this.queryParams,
            title: this.searchInput,
          },
          options: {},
        })
        .then((response) => {
          this.items = response.data.items;
        });
    }, 350),
  },
});