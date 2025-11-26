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
    showSearch: { type: Boolean, default: true },
    searchLabel: { type: String, default: 'Search labels' },
    disabled: Boolean,
    openAll: { type: Boolean, default: false },
    inline: { type: Boolean, default: false },
    dialogTitle: { type: String, default: 'Select labels' },
    label: { type: String, default: 'Labels' },
    dialogProps: { type: Object },
  },

  emits: ['update:model-value', 'loaded', 'error'],

  data: () => ({
    dialog: false,
    items: [],
    flatItems: [],
    total: 0,
    loading: false,
    error: null,

    search: '',
    opened: [],
    internalSelected: [],

    skipNextSync: false, // prevents overwrite loops
  }),

  watch: {
    modelValue: {
      immediate: true,
      deep: true,
      handler() {
        if (!this.skipNextSync) {
          this.resolveSelectionFromTree();
        }
        this.skipNextSync = false;
      },
    },

    internalSelected: {
      deep: true,
      handler(val) {
        // 👇 THIS FIXES YOUR ISSUE – user selection now propagates
        const output = this.multiple
          ? this.returnObject
            ? val
            : val.map((v) => v.id)
          : this.returnObject
          ? val[0] || null
          : val[0]?.id || null;

        this.skipNextSync = true;
        this.$emit('update:model-value', output);
      },
    },
  },

  mounted() {
    this.fetchTree();
  },

  methods: {
    fetchTree() {
      this.loading = true;
      this.error = null;

      api
        .get(this.api, { params: this.queryParams })
        .then((response) => {
          const data = response.data || {};

          this.items = Array.isArray(data.items) ? data.items : [];
          this.flatItems = this.flattenTree(this.items);
          this.total = data.total || this.items.length;

          if (this.openAll) {
            this.opened = this.flatItems.map((n) => n.id);
          }

          // ✅ restore selection correctly
          this.resolveSelectionFromTree();

          this.$emit('loaded', {
            items: this.items,
            total: this.total,
          });
        })
        .catch((err) => {
          console.error(err);
          this.error = err;
          this.$emit('error', err);
        })
        .finally(() => {
          this.loading = false;
        });
    },

    flattenTree(nodes, acc = []) {
      nodes.forEach((node) => {
        acc.push(node);
        if (Array.isArray(node.children)) {
          this.flattenTree(node.children, acc);
        }
      });
      return acc;
    },

    resolveSelectionFromTree() {
      if (!this.flatItems.length) return;

      const inputIds = this.multiple
        ? Array.isArray(this.modelValue)
          ? this.modelValue.map((v) => (this.returnObject ? v?.id : v))
          : []
        : this.modelValue
        ? [this.returnObject ? this.modelValue?.id : this.modelValue]
        : [];

      const resolved = this.flatItems.filter((node) => inputIds.includes(node.id));

      this.internalSelected = resolved;
    },

    valueComparator(a, b) {
      return (a?.id ?? a) === (b?.id ?? b);
    },
  },

  template: `
  <div class="label-tree-field">

    <!-- INLINE MODE -->
    <template v-if="inline">
      <v-text-field
        v-if="showSearch"
        v-model="search"
        :label="searchLabel"
        prepend-inner-icon="mdi-magnify"
        density="compact"
        hide-details
        clearable
        class="mb-2"
      />

      <v-treeview
        v-model:selected="internalSelected"
        v-model:opened="opened"
        :items="items"
        item-value="id"
        item-title="title"
        :value-comparator="valueComparator"
        :return-object="true"
        :selectable="multiple ? selectable : false"
        :select-strategy="multiple ? selectStrategy : 'single-independent'"
        :activatable="multiple ? false : true"
        :active-strategy="multiple ? undefined : 'single-independent'"
        :open-on-click="openOnClick"
        :search="search"
        :open-all="openAll"
        :disabled="disabled"
        indent-lines
        separate-roots
      />

    </template>

    <!-- DIALOG MODE -->
    <template v-else>
      <v-select
        prepend-inner-icon="mdi-label"
        @click="dialog = true"
        :model-value="modelValue"
        :label="label"
        chips
        multiple
        readonly
      >
        <template #selection>
          <v-chip
            v-for="item in internalSelected"
            :key="item.id"
            size="small"
            class="ma-1"
          >
            {{ item.title }}
          </v-chip>
        </template>
      </v-select>

        <div :class="['position-fixed h-screen right-0 top-0 z-100', { 'pointer-events-none': !dialog }]" :style="$root?.rightDialogProps?.['content-props']?.style">
            <div class="position-relative h-100 w-100">
                <v-dialog v-model="dialog" v-bind="dialogProps || { 'max-width': '880px' }">
                    <v-card elevation="4">
                        <!-- Toolbar -->
                        <v-toolbar color="dark-primary" class="px-4">
                            <div class="w-33">
                                <v-toolbar-title>{{ dialogTitle }}</v-toolbar-title>
                            </div>

                            <v-spacer></v-spacer>

                            <v-text-field
                                class="w-33"
                                v-if="showSearch"
                                v-model="search"
                                :label="searchLabel"
                                prepend-inner-icon="mdi-magnify"
                                density="compact"
                                hide-details
                                clearable
                                variant="solo"
                            />

                            <v-spacer></v-spacer>

                            <div class="w-33 d-flex justify-end">
                                <v-btn icon="mdi-close" @click="dialog = false"></v-btn>
                            </div>
                        </v-toolbar>

                        <v-card class="overflow-y-auto">
                            <v-card-text>
                                <!-- Tree -->
                                <v-treeview
                                    v-model:selected="internalSelected"
                                    v-model:opened="opened"
                                    :items="items"
                                    item-value="id"
                                    item-title="title"
                                    :value-comparator="valueComparator"
                                    :return-object="true"
                                    :selectable="multiple ? selectable : false"
                                    :select-strategy="multiple ? selectStrategy : 'single-independent'"
                                    :activatable="multiple ? false : true"
                                    :active-strategy="multiple ? undefined : 'single-independent'"
                                    :open-on-click="openOnClick"
                                    :search="search"
                                    :open-all="openAll"
                                    :disabled="disabled"
                                    indent-lines
                                    separate-roots
                                >
                                    <template #no-data>
                                        <div
                                            class="text-center py-8 text-medium-emphasis"
                                        >
                                            <v-icon size="40" class="mb-2">mdi-folder-search</v-icon>
                                            <div>No matching labels found</div>
                                            <div class="text-caption">Try adjusting your search</div>
                                        </div>
                                    </template>
                                </v-treeview>
                            </v-card-text>
                        </v-card>

                    </v-card>
                </v-dialog>
            </div>
        </div>
    </template>
  </div>
  `,
});
