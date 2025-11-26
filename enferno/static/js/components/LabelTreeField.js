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
    openAll: { type: Boolean, default: false },
    dialogTitle: { type: String, default: window.translations.selectLabels_ },
    label: { type: String, default: window.translations.labels_ },
    dialogProps: { type: Object },
  },

  emits: ['update:model-value', 'loaded', 'error'],

  data() {
    return {
      translations: window.translations,
      dialog: false,

      // Tree data
      items: [],
      flatItems: [],
      total: 0,

      loading: false,
      error: null,

      // Controls which tree nodes are expanded
      opened: [],

      // Currently committed selection (what parent sees)
      internalSelected: [],

      // Temporary selection used in UI before clicking Save
      draftSelected: [],

      // Ensures we only fetch once
      hasLoaded: false,
    };
  },

  watch: {
    // When parent changes modelValue, re-sync internal state
    modelValue: {
      immediate: true,
      deep: true,
      handler() {
        this.restoreSelectionFromModel();
      },
    },

    // Reset draft state when dialog is closed
    dialog(val) {
        if (val) {
            // Dialog opened → lazy load tree
            this.fetchTreeOnce();
        } else {
            // Dialog closed → discard unsaved changes
            this.draftSelected = [...this.internalSelected];
        }
    },
  },

  methods: {
    fetchTreeOnce() {
        if (this.hasLoaded) return;
        this.hasLoaded = true;
        this.fetchTree();
    },
    async fetchTree() {
      this.loading = true;
      this.error = null;

      try {
        const response = await api.get(this.api, {
          params: this.queryParams,
        });

        const data = response.data || {};

        this.items = Array.isArray(data.items) ? data.items : [];

        // Flatten for fast ID lookup when resolving selection
        this.flatItems = this.flattenTree(this.items);

        this.total = data.total || this.items.length;

        // Optionally expand all nodes
        if (this.openAll) {
          this.opened = this.flatItems.map((n) => n.id);
        }

        // Try to match incoming modelValue to fetched tree items
        this.restoreSelectionFromModel();

        this.$emit('loaded', {
          items: this.items,
          total: this.total,
        });
      } catch (err) {
        console.error(err);
        this.error = err;
        this.$emit('error', err);
      } finally {
        this.loading = false;
      }
    },

    // Turns nested tree structure into a flat list for easy searching
    flattenTree(nodes, acc = []) {
      for (const node of nodes) {
        acc.push(node);
        if (Array.isArray(node.children)) {
          this.flattenTree(node.children, acc);
        }
      }
      return acc;
    },

    // Syncs internal selection from v-model
    restoreSelectionFromModel() {
        // Normalize incoming value to an array
        const raw = this.multiple
            ? Array.isArray(this.modelValue) ? this.modelValue : []
            : this.modelValue ? [this.modelValue] : [];

        // If tree not loaded yet, fallback to raw modelValue
        if (!this.flatItems.length) {
            if (this.returnObject) {
            // Use raw objects directly (so select displays something)
            this.internalSelected = raw;
            this.draftSelected = [...raw];
            } else {
            // If only IDs were passed, we can't resolve titles yet
            // So show empty until fetch happens
            this.internalSelected = [];
            this.draftSelected = [];
            }
            return;
        }

        // Normalize to ids
        const ids = raw.map(v => this.returnObject ? v?.id : v);

        // Resolve against tree
        const resolved = this.flatItems.filter(node => ids.includes(node.id));

        this.internalSelected = resolved;
        this.draftSelected = [...resolved];
        },

    // Saves draft selection into modelValue
    commitSelection() {
      // Convert internal format into parent format
      const val = this.multiple
        ? this.returnObject
          ? this.draftSelected
          : this.draftSelected.map(v => v.id)
        : this.returnObject
          ? this.draftSelected[0] || null
          : this.draftSelected[0]?.id || null;

      // Persist change
      this.internalSelected = [...this.draftSelected];
      this.$emit('update:model-value', val);

      this.dialog = false;
    },

    // Ensures treeview compares objects by ID
    valueComparator(a, b) {
      return (a?.id ?? a) === (b?.id ?? b);
    },

    copyValue() {
        const textToCopy = this.internalSelected
            .map(item => {
            if (this.returnObject) return item?.title ?? '';
            return item ?? '';
            })
            .join(', ');

        navigator.clipboard.writeText(textToCopy)
            .then(() => {
              this.$root.showSnack(this.translations.copiedToClipboard_);
            })
            .catch(err => {
              console.error('Clipboard error:', err);
              this.$root.showSnack(this.translations.failedToCopyToClipboard_);
            });
        },
  },

  template: `
  <div class="label-tree-field">
    <!-- DIALOG MODE -->
    <!-- Read-only preview of committed selection -->
    <v-select
      prepend-inner-icon="mdi-magnify"
      @click="dialog = true"
      :model-value="internalSelected"
      :label="label"
      chips
      multiple
      readonly
    >
      <template v-if="showCopyIcon" v-slot:append>
          <v-btn icon="mdi-content-copy" variant="plain" @click.stop="copyValue"></v-btn>
      </template>
    </v-select>

    <!-- Floating right-side dialog -->
    <div 
      :class="['position-fixed h-screen right-0 top-0 z-100', { 'pointer-events-none': !dialog }]" 
      :style="$root?.rightDialogProps?.['content-props']?.style"
    >
      <div class="position-relative h-100 w-100">
        <v-dialog v-model="dialog" v-bind="dialogProps || { 'max-width': '880px' }">
          <v-card elevation="4">

            <!-- Toolbar -->
            <v-toolbar color="dark-primary" class="px-4">
              <v-toolbar-title>{{ dialogTitle }}</v-toolbar-title>
              <v-spacer></v-spacer>

              <!-- Save changes from draftSelected -->
              <v-btn
                v-if="!disabled && items.length"
                variant="elevated"
                class="mx-2"
                @click="commitSelection"
              >
                {{ translations.save_ }}
              </v-btn>

              <!-- Close without saving -->
              <v-btn
                icon="mdi-close"
                @click="dialog = false"
              ></v-btn>
            </v-toolbar>

            <v-card class="overflow-y-auto">
              <v-card-text>
                <!-- Empty state: no data from API -->
                <div
                  v-if="!items.length && !loading"
                  class="text-center py-8 text-medium-emphasis"
                >
                  <v-icon size="40" class="mb-2">mdi-folder-outline</v-icon>
                  <div class="text-body-2 font-weight-medium">
                    {{ translations.noLabelsAvailable_ }}
                  </div>
                  <div class="text-caption">
                    {{ translations.thereAreNoLabelsToDisplayYet_ }}
                  </div>
                </div>


                <!-- Tree -->
                <v-treeview
                  v-model:selected="draftSelected"
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
                  :open-all="openAll"
                  :disabled="disabled"
                  indent-lines
                  separate-roots
                />
              </v-card-text>
            </v-card>
          </v-card>
        </v-dialog>
      </div>
    </div>
  </div>
  `,
});
