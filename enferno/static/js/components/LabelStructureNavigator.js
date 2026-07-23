const LabelStructureNavigator = Vue.defineComponent({
  props: {
    canManage: {
      type: Boolean,
      default: false,
    },
    translations: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      closeTimer: null,
      error: false,
      loaded: false,
      loading: false,
      menuOpen: false,
      openTimer: null,
      opened: [],
      pinned: false,
      query: '',
      treeItems: [],
    };
  },
  computed: {
    filteredItems() {
      const query = this.query.trim().toLocaleLowerCase();
      if (!query) return this.treeItems;
      return this.filterTree(this.treeItems, query);
    },
  },
  watch: {
    menuOpen(open) {
      if (open) {
        this.loadTree();
      } else {
        this.pinned = false;
      }
    },
    query(value) {
      if (value.trim()) this.opened = this.collectParentIds(this.filteredItems);
    },
  },
  beforeUnmount() {
    this.clearTimers();
  },
  methods: {
    clearTimers() {
      clearTimeout(this.openTimer);
      clearTimeout(this.closeTimer);
    },
    collectParentIds(items) {
      return items.flatMap((item) => [
        ...(item.children?.length ? [item.id] : []),
        ...this.collectParentIds(item.children || []),
      ]);
    },
    filterTree(items, query) {
      return items.reduce((matches, item) => {
        const children = this.filterTree(item.children || [], query);
        const title = `${item.title || ''} ${item.title_ar || ''}`.toLocaleLowerCase();

        if (title.includes(query)) {
          matches.push(item);
        } else if (children.length) {
          matches.push({...item, children});
        }

        return matches;
      }, []);
    },
    holdOpen() {
      this.clearTimers();
    },
    preview() {
      this.clearTimers();
      if (this.menuOpen) return;
      this.openTimer = setTimeout(() => {
        this.menuOpen = true;
      }, 250);
    },
    scheduleClose() {
      clearTimeout(this.closeTimer);
      if (this.pinned) return;
      this.closeTimer = setTimeout(() => {
        this.menuOpen = false;
      }, 300);
    },
    togglePinned() {
      this.clearTimers();
      if (this.menuOpen && this.pinned) {
        this.menuOpen = false;
        return;
      }
      this.pinned = true;
      this.menuOpen = true;
    },
    async loadTree() {
      if (this.loaded || this.loading) return;

      this.error = false;
      this.loading = true;
      try {
        const response = await api.get('/admin/api/labels/tree');
        this.treeItems = response.data.items;
        this.loaded = true;
      } catch (_error) {
        this.error = true;
      } finally {
        this.loading = false;
      }
    },
  },
  template: `
    <v-menu
      v-model="menuOpen"
      :close-on-content-click="false"
      :open-on-click="false"
      location="bottom end"
      offset="8"
    >
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          icon="mdi-file-tree-outline"
          :aria-label="translations.labelStructure"
          :aria-expanded="menuOpen"
          :title="translations.labelStructure"
          @click.stop="togglePinned"
          @focus="preview"
          @mouseenter="preview"
          @mouseleave="scheduleClose"
        ></v-btn>
      </template>

      <v-card
        class="label-structure-panel"
        @focusin="holdOpen"
        @focusout="scheduleClose"
        @mouseenter="holdOpen"
        @mouseleave="scheduleClose"
      >
        <v-card-title class="d-flex align-center ga-2 py-2 pe-2">
          <v-icon icon="mdi-file-tree-outline" size="small"></v-icon>
          <span>{{ translations.labelStructure }}</span>
          <v-chip size="x-small" variant="tonal">{{ translations.readOnly }}</v-chip>
          <v-spacer></v-spacer>
          <v-btn
            :aria-label="translations.close"
            icon="mdi-close"
            size="small"
            variant="text"
            @click="menuOpen = false"
          ></v-btn>
        </v-card-title>

        <v-card-text class="px-3 py-2">
          <v-text-field
            v-model="query"
            :label="translations.search"
            clearable
            density="compact"
            hide-details
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
          ></v-text-field>
        </v-card-text>

        <div class="label-structure-tree">
          <div v-if="loading" class="d-flex justify-center pa-8">
            <v-progress-circular indeterminate></v-progress-circular>
          </div>

          <v-alert v-else-if="error" class="ma-3" type="error" variant="tonal">
            {{ translations.loadError }}
            <template #append>
              <v-btn size="small" variant="text" @click="loadTree">{{ translations.retry }}</v-btn>
            </template>
          </v-alert>

          <div v-else-if="loaded && !filteredItems.length" class="pa-6 text-center text-medium-emphasis">
            {{ translations.noLabels }}
          </div>

          <v-treeview
            v-else
            v-model:opened="opened"
            :items="filteredItems"
            density="compact"
            item-children="children"
            item-title="title"
            item-value="id"
            open-on-click
          >
            <template #title="{ item }">
              <div class="d-flex flex-column label-structure-title">
                <span>{{ item.title }}</span>
                <span v-if="item.title_ar" class="label-structure-title-ar text-medium-emphasis" dir="rtl">{{ item.title_ar }}</span>
              </div>
            </template>
            <template #append="{ item }">
              <div class="d-flex ga-1 ms-2">
                <v-chip v-if="item.for_bulletin" :title="translations.bulletins" size="x-small">B</v-chip>
                <v-chip v-if="item.for_actor" :title="translations.actors" size="x-small">A</v-chip>
                <v-chip v-if="item.for_incident" :title="translations.incidents" size="x-small">I</v-chip>
                <v-chip v-if="item.for_offline" :title="translations.offline" size="x-small">O</v-chip>
              </div>
            </template>
          </v-treeview>
        </div>

        <v-card-actions v-if="canManage" class="border-t-sm">
          <v-spacer></v-spacer>
          <v-btn href="/admin/labels/" prepend-icon="mdi-cog-outline" variant="text">
            {{ translations.manageLabels }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-menu>
  `,
});
