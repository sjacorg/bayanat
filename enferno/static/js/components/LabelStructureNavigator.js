const PANEL_WIDTH = 390;

const LabelStructureNavigator = Vue.defineComponent({
  props: {
    canManage: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    const saved = JSON.parse(localStorage.getItem('labelTreePos') || 'null');
    return {
      translations: window.labelTreeTranslations,
      open: localStorage.getItem('labelTreeOpen') === '1',
      x: saved?.x ?? 24,
      y: saved?.y ?? Math.max(72, window.innerHeight - 640),
      dragOffset: null,
      error: false,
      loaded: false,
      loading: false,
      opened: JSON.parse(localStorage.getItem('labelTreeOpened') || '[]'),
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
    open(open) {
      localStorage.setItem('labelTreeOpen', open ? '1' : '0');
      if (open) {
        this.clampToViewport();
        this.loadTree();
      }
    },
    opened(ids) {
      localStorage.setItem('labelTreeOpened', JSON.stringify(ids));
    },
    query(value) {
      if (value.trim()) this.opened = this.collectParentIds(this.filteredItems);
    },
  },
  mounted() {
    window.addEventListener('resize', this.clampToViewport);
    if (this.open) {
      this.clampToViewport();
      this.loadTree();
    }
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.clampToViewport);
    this.stopDrag();
  },
  methods: {
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
    isAssignable(item) {
      return Boolean(
        item.for_bulletin || item.for_actor || item.for_incident || item.for_offline,
      );
    },
    // not assignable + has children = a grouping node; without children it is a
    // retired label that still carries historical tags
    itemIcon(item) {
      if (this.isAssignable(item)) return 'mdi-label';
      return item.children?.length ? 'mdi-folder-outline' : 'mdi-label-off-outline';
    },
    itemIconHint(item) {
      if (this.isAssignable(item)) return '';
      return item.children?.length ? this.translations.groupingOnly : this.translations.retired;
    },
    // keep at least a corner of the panel on screen after drags and window resizes
    clampToViewport() {
      const edge = 80;
      this.x = Math.min(Math.max(this.x, edge - PANEL_WIDTH), window.innerWidth - edge);
      this.y = Math.min(Math.max(this.y, 0), window.innerHeight - 48);
    },
    startDrag(event) {
      this.dragOffset = {x: event.clientX - this.x, y: event.clientY - this.y};
      window.addEventListener('pointermove', this.onDrag);
      window.addEventListener('pointerup', this.stopDrag);
    },
    onDrag(event) {
      this.x = event.clientX - this.dragOffset.x;
      this.y = event.clientY - this.dragOffset.y;
      this.clampToViewport();
    },
    stopDrag() {
      window.removeEventListener('pointermove', this.onDrag);
      window.removeEventListener('pointerup', this.stopDrag);
      if (this.dragOffset) {
        localStorage.setItem('labelTreePos', JSON.stringify({x: this.x, y: this.y}));
        this.dragOffset = null;
      }
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
    <teleport to="body">
      <v-btn
        class="label-structure-fab"
        :aria-label="translations.labelStructure"
        :aria-expanded="open"
        color="primary"
        :title="translations.labelStructure"
        :icon="open ? 'mdi-close' : 'mdi-file-tree-outline'"
        variant="elevated"
        rounded="circle"
        size="large"
        @click="open = !open"
      ></v-btn>

      <v-card
        v-if="open"
        class="label-structure-panel label-structure-dock"
        :style="{left: x + 'px', top: y + 'px'}"
        elevation="12"
      >
        <v-card-title
          class="d-flex align-center ga-2 py-2 pe-2 label-structure-handle"
          @pointerdown.prevent="startDrag"
        >
          <v-icon icon="mdi-drag-horizontal-variant" size="small"></v-icon>
          <span>{{ translations.labelStructure }}</span>
          <v-chip size="x-small" variant="tonal">{{ translations.readOnly }}</v-chip>
          <v-spacer></v-spacer>
          <v-btn
            :aria-label="translations.close"
            icon="mdi-close"
            size="small"
            variant="text"
            @click="open = false"
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
            <template #prepend="{ item }">
              <v-icon :icon="itemIcon(item)" :title="itemIconHint(item)" size="small"></v-icon>
            </template>
            <template #title="{ item }">
              <div class="d-flex flex-column label-structure-title">
                <span :class="{'text-medium-emphasis': !isAssignable(item)}">{{ item.title }}</span>
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
    </teleport>
  `,
});
