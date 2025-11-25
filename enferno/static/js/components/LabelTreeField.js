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
    inline: { type: Boolean, default: true },
    dialogTitle: { type: String, default: 'Select labels' },
    label: { type: String, default: 'Labels' },
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
          this.resolveSelectionFromTree()
        }
        this.skipNextSync = false
      },
    },

    internalSelected: {
      deep: true,
      handler(val) {
        // 👇 THIS FIXES YOUR ISSUE – user selection now propagates
        const output = this.multiple
          ? (this.returnObject ? val : val.map(v => v.id))
          : (this.returnObject ? val[0] || null : val[0]?.id || null)

        this.skipNextSync = true
        this.$emit('update:model-value', output)
      },
    },
  },

  mounted() {
    this.fetchTree()
  },

  methods: {
    fetchTree() {
      this.loading = true
      this.error = null

      api.get(this.api, { params: this.queryParams })
        .then((response) => {
          const data = response.data || {}

          this.items = Array.isArray(data.items) ? data.items : []
          this.flatItems = this.flattenTree(this.items)
          this.total = data.total || this.items.length

          if (this.openAll) {
            this.opened = this.flatItems.map(n => n.id)
          }

          // ✅ restore selection correctly
          this.resolveSelectionFromTree()

          this.$emit('loaded', {
            items: this.items,
            total: this.total,
          })
        })
        .catch((err) => {
          console.error(err)
          this.error = err
          this.$emit('error', err)
        })
        .finally(() => {
          this.loading = false
        })
    },

    flattenTree(nodes, acc = []) {
      nodes.forEach(node => {
        acc.push(node)
        if (Array.isArray(node.children)) {
          this.flattenTree(node.children, acc)
        }
      })
      return acc
    },

    resolveSelectionFromTree() {
      if (!this.flatItems.length) return

      const inputIds = this.multiple
        ? (
            Array.isArray(this.modelValue)
              ? this.modelValue.map(v => this.returnObject ? v?.id : v)
              : []
          )
        : (
            this.modelValue
              ? [this.returnObject ? this.modelValue?.id : this.modelValue]
              : []
          )

      const resolved = this.flatItems.filter(node =>
        inputIds.includes(node.id)
      )

      this.internalSelected = resolved
    },

    valueComparator(a, b) {
      return (a?.id ?? a) === (b?.id ?? b)
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

      <v-dialog v-model="dialog" max-width="800">
        <v-card>

          <v-card-title>{{ dialogTitle }}</v-card-title>

          <v-card-text>

            <v-text-field
              v-if="showSearch"
              v-model="search"
              :label="searchLabel"
              prepend-inner-icon="mdi-magnify"
              density="compact"
              hide-details
              clearable
              class="mb-3"
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
              style="max-height: 400px; overflow-y: auto"
              indent-lines
                separate-roots
            />

          </v-card-text>

          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="dialog = false">
              Done
            </v-btn>
          </v-card-actions>

        </v-card>
      </v-dialog>

    </template>
  </div>
  `,
});
