const LabelTreeField = Vue.defineComponent({
  props: {
    modelValue: { type: [Array, Object, null], default: null },
    multiple: { type: Boolean, default: true },
    api: { type: String, default: '/admin/api/labels/tree' },
    queryParams: { type: Object, default: () => ({}) },

    selectable: { type: Boolean, default: true },
    selectStrategy: { type: String, default: 'independent' },
    returnObject: { type: Boolean, default: true },
    activatable: { type: Boolean, default: false },
    openOnClick: { type: Boolean, default: true },

    showCopyIcon: { type: Boolean, default: false },
    disabled: Boolean,
    label: { type: String, default: window.translations.labels_ },
  },

  emits: ['update:model-value'],

  data() {
    return {
      translations: window.translations,
      expand: false,
      loading: false,
      fetchedOnce: false,
      search: '',

      items: [],
      flatItems: [],
      internalSelected: [],
    };
  },

  computed: {
    displayedItems() {
      // ✅ Use loaded tree if available
      if (this.items.length) return this.items;

      // ✅ Otherwise fallback to selected items as a simple tree
      if (this.internalSelected.length) {
        return this.internalSelected.map(item => ({
          ...item,
          children: [],
        }));
      }

      // ✅ Fallback empty
      return [];
    }
  },

  watch: {
    modelValue: {
      immediate: true,
      deep: true,
      handler() {
        this.restoreSelectionFromModel();
      },
    },
  },

  methods: {
    async fetchTreeOnce() {
      this.loading = true;

      try {
        const response = await api.get(this.api, {
          params: this.queryParams,
        });

        const data = response.data || {};
        this.items = Array.isArray(data.items) ? data.items : [];

        this.flatItems = this.flattenTree(this.items);
        this.restoreSelectionFromModel();

        this.fetchedOnce = true;
      } catch (err) {
        console.error(err);
      } finally {
        this.loading = false;
      }
    },

    flattenTree(nodes, acc = []) {
      for (const node of nodes) {
        acc.push(node);
        if (Array.isArray(node.children)) {
          this.flattenTree(node.children, acc);
        }
      }
      return acc;
    },

    restoreSelectionFromModel() {
      const raw = this.multiple
        ? Array.isArray(this.modelValue) ? this.modelValue : []
        : this.modelValue ? [this.modelValue] : [];

      // If tree isn't loaded yet, use raw objects directly
      if (!this.items.length && this.returnObject) {
        this.internalSelected = raw;
        return;
      }

      const ids = raw.map(v => this.returnObject ? v?.id : v);

      // ✅ Preserve original modelValue order
      this.internalSelected = ids
        .map(id => this.flatItems.find(node => node.id === id))
        .filter(Boolean); // remove missing ones
    },

    emitSelection(val) {
      const value = this.multiple
        ? this.returnObject ? val : val.map(v => v.id)
        : this.returnObject ? val[0] || null : val[0]?.id || null;

      this.internalSelected = [...val];
      this.$emit('update:model-value', value);
    },

    async toggleExpansionPanel() {
      if (!this.fetchedOnce) this.fetchTreeOnce(); // don't await, let UI render
      this.expand = !this.expand;
    },

    removeChip(item) {
      const updated = this.internalSelected.filter(
        selected => selected.id !== item.id
      );

      this.emitSelection(updated);
    },

    copyValue() {
      const text = this.internalSelected
        .map(item => this.returnObject ? item?.title ?? '' : item ?? '')
        .join(', ');

      navigator.clipboard.writeText(text)
        .then(() => this.$root.showSnack(this.translations.copiedToClipboard_))
        .catch(() => this.$root.showSnack(this.translations.failedToCopyToClipboard_));
    },
  },

  template: `
  <div class="label-tree-field">

    <!-- Trigger Select -->
    <v-select
      :model-value="internalSelected"
      :label="label"
      chips
      :multiple="multiple"
      hide-details
      :loading="loading"
      :disabled="disabled"
      :menu-icon="expand ? 'mdi-menu-up' : 'mdi-menu-down'"
      @click="toggleExpansionPanel"
      :class="[{ 'input--open': expand }]"
      hide-no-data
    >
      <!-- Custom chip -->
      <template #chip="{ item, props }">
        <v-chip
          v-bind="props"
          closable
          @click:close="removeChip(item.raw)"
        >
          {{ item.raw?.title }}
        </v-chip>
      </template>

      <template v-if="showCopyIcon" #append>
        <v-btn
          icon="mdi-content-copy"
          variant="plain"
          @click.stop="copyValue"
        />
      </template>
    </v-select>

    <!-- Expand Panel -->
    <v-expand-transition>
      <v-card
        v-show="expand"
        variant="outlined"
        rounded="md"
        class="border-sm max-h-[440px] overflow-y-auto"
        :style="{ width: showCopyIcon ? 'calc(100% - 64px)' : '100%' }"
      >
        <v-card-text>

          <!-- Search Input -->
          <v-text-field
            v-model="search"
            :label="translations.search_"
            variant="outlined"
            density="comfortable"
            clearable
            prepend-inner-icon="mdi-magnify"
            class="mb-3"
            hide-details
          />

          <!-- Tree -->
          <v-treeview
            v-if="displayedItems.length"
            class="text-medium-emphasis"
            density="compact"
            v-model:selected="internalSelected"
            :items="displayedItems"
            item-value="id"
            item-title="title"
            return-object
            :search="search"
            :filter="(item, search) => item.title.toLowerCase().includes(search.toLowerCase())"

            :selectable="multiple ? selectable : false"
            :select-strategy="multiple ? selectStrategy : 'single-independent'"
            selected-color="blue"
            :activatable="multiple ? false : true"
            :active-strategy="multiple ? undefined : 'single-independent'"
            :open-on-click="openOnClick"
            :disabled="disabled"

            indent-lines
            separate-roots

            @update:selected="emitSelection"
          />

          <!-- Optional: Fallback Empty -->
          <div
            v-else
            class="text-medium-emphasis text-center py-6"
          >
            {{ translations.noLabelsAvailable_ }}
          </div>

        </v-card-text>
      </v-card>
    </v-expand-transition>

  </div>
  `,
});
