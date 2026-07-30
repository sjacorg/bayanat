const LabelPathUtils = {
  isRtl() {
    const lang = (window.__lang__ || document?.documentElement?.lang || 'en').toLowerCase();
    return lang.startsWith('ar');
  },

  primaryLang() {
    return this.isRtl() ? 'ar' : 'en';
  },

  pathSeparator() {
    return this.isRtl() ? '‹' : '›';
  },

  pathSeparatorForLang(lang = this.primaryLang()) {
    return lang === 'ar' ? '‹' : '›';
  },

  splitPath(path) {
    if (!path || typeof path !== 'string') return [];
    return path.split('>').map(part => part.trim()).filter(Boolean);
  },

  title(label, lang = this.primaryLang()) {
    if (!label) return '';
    if (lang === 'ar') return label.title_ar || label.title || '';
    return label.title || label.title_ar || '';
  },

  secondaryTitle(label) {
    return this.primaryLang() === 'ar' ? (label?.title || '') : (label?.title_ar || '');
  },

  pathSegments(label, lang = this.primaryLang()) {
    if (!label) return [];
    if (lang !== 'ar') return this.splitPath(label.path);

    const arabic = this.splitPath(label.path_ar);
    if (arabic.length) return arabic;
    return this.splitPath(label.path);
  },

  fullPathSegments(label, lang = this.primaryLang()) {
    const parentSegments = this.pathSegments(label, lang);
    const leaf = this.title(label, lang);
    return leaf ? [...parentSegments, leaf] : parentSegments;
  },

  normalizedSegments(segments = []) {
    return segments
      .map(segment => String(segment || '').trim().replace(/\s+/g, ' ').toLocaleLowerCase())
      .filter(Boolean);
  },

  sameSegments(first = [], second = []) {
    const normalizedFirst = this.normalizedSegments(first);
    const normalizedSecond = this.normalizedSegments(second);
    return normalizedFirst.length === normalizedSecond.length
      && normalizedFirst.every((segment, index) => segment === normalizedSecond[index]);
  },

  hasPath(label) {
    return Boolean(this.pathSegments(label, 'en').length || this.pathSegments(label, 'ar').length);
  },

  parentTitle(label, lang = this.primaryLang()) {
    const segments = this.pathSegments(label, lang);
    return segments[segments.length - 1] || '';
  },

  collapsedPath(label, lang = this.primaryLang()) {
    const segments = this.pathSegments(label, lang);
    if (!segments.length) return '';
    const displaySegments = segments.length > 3
      ? [segments[0], '…', segments[segments.length - 1]]
      : segments;
    return displaySegments.join(` ${this.pathSeparatorForLang(lang)} `);
  },

  chipText(label, duplicateLeaves = []) {
    const parts = this.chipParts(label, duplicateLeaves);
    if (!parts.showParent) return parts.leaf;
    return parts.isRtl
      ? `${parts.leaf} ${parts.separator} ${parts.parent}`
      : `${parts.parent} ${parts.separator} ${parts.leaf}`;
  },

  chipParts(label, duplicateLeaves = []) {
    const leaf = this.title(label);
    const parent = this.parentTitle(label);
    const hasPath = this.hasPath(label);
    const showParent = Boolean(hasPath && parent && duplicateLeaves.includes(this.leafKey(label)));
    const isRtl = this.isRtl();
    return {
      hasPath,
      isRtl,
      leaf,
      parent,
      separator: this.pathSeparator(),
      showParent,
      markerIcon: isRtl ? 'mdi-chevron-left' : 'mdi-chevron-right',
    };
  },

  leafKey(label) {
    return this.title(label).trim().toLocaleLowerCase();
  },
};

const LabelPathTrail = Vue.defineComponent({
  props: {
    label: { type: Object, required: true },
    lang: { type: String, default: null },
  },
  computed: {
    isRtl() {
      return (this.lang || LabelPathUtils.primaryLang()) === 'ar';
    },
    segments() {
      return LabelPathUtils.fullPathSegments(this.label, this.lang || LabelPathUtils.primaryLang());
    },
    separatorIcon() {
      return this.isRtl ? 'mdi-chevron-left' : 'mdi-chevron-right';
    },
  },
  template: `
    <span
      v-if="segments.length"
      class="d-inline-flex align-center flex-wrap ga-1 text-body-2"
      :dir="isRtl ? 'rtl' : 'ltr'"
    >
      <template v-for="(segment, index) in segments" :key="index">
        <span :class="index < segments.length - 1 ? 'text-medium-emphasis' : 'font-weight-bold text-high-emphasis'">
          {{ segment }}
        </span>
        <v-icon
          v-if="index < segments.length - 1"
          :icon="separatorIcon"
          size="16"
          class="text-medium-emphasis"
        ></v-icon>
      </template>
    </span>
  `,
});

const LabelPathChip = Vue.defineComponent({
  components: { LabelPathTrail },
  props: {
    label: { type: Object, required: true },
    duplicateLeaves: { type: Array, default: () => [] },
  },
  data: () => ({
    menu: false,
    translations: window.translations,
  }),
  computed: {
    hasPath() {
      return LabelPathUtils.hasPath(this.label);
    },
    markerIcon() {
      return this.chipParts.markerIcon;
    },
    chipText() {
      return LabelPathUtils.chipText(this.label, this.duplicateLeaves);
    },
    chipParts() {
      return LabelPathUtils.chipParts(this.label, this.duplicateLeaves);
    },
    primaryLang() {
      return LabelPathUtils.primaryLang();
    },
    secondaryLang() {
      return this.primaryLang === 'ar' ? 'en' : 'ar';
    },
    pathRows() {
      const rows = [];
      const primarySegments = LabelPathUtils.fullPathSegments(this.label, this.primaryLang);
      const secondarySegments = LabelPathUtils.fullPathSegments(this.label, this.secondaryLang);
      if (primarySegments.length) {
        rows.push({
          lang: this.primaryLang,
        });
      }
      if (secondarySegments.length && !LabelPathUtils.sameSegments(primarySegments, secondarySegments)) {
        rows.push({
          lang: this.secondaryLang,
        });
      }
      return rows;
    },
  },
  template: `
    <v-menu
      v-if="hasPath"
      v-model="menu"
      location="bottom start"
      offset="6"
      :close-on-content-click="false"
    >
      <template #activator="{ props }">
        <v-chip
          v-bind="props"
          label
          size="small"
          color="primary"
          variant="tonal"
          class="flex-chip"
          tabindex="0"
          @keydown.enter.prevent="menu = true"
          @keydown.space.prevent="menu = true"
          @keydown.esc.prevent="menu = false"
        >
          <span class="text-primary font-weight-medium text-no-wrap">…</span>
          <v-icon :icon="markerIcon" size="14" color="primary" class="me-1"></v-icon>
          <template v-if="chipParts.showParent">
            <span v-if="chipParts.isRtl">{{ chipParts.leaf }}</span>
            <span v-else>{{ chipParts.parent }}</span>
            <v-icon :icon="markerIcon" size="14" color="primary" class="mx-1"></v-icon>
            <span v-if="chipParts.isRtl">{{ chipParts.parent }}</span>
            <span v-else>{{ chipParts.leaf }}</span>
          </template>
          <span v-else>{{ chipParts.leaf }}</span>
        </v-chip>
      </template>
      <v-card
        class="border rounded-lg"
        elevation="8"
        width="420"
        max-width="calc(100vw - 32px)"
        @keydown.esc.prevent="menu = false"
      >
        <v-card-text class="pa-3">
          <div class="text-overline font-weight-bold text-medium-emphasis mb-2">
            {{ translations.labelPath_ }}
          </div>
          <div
            v-for="(row, index) in pathRows"
            :key="row.lang"
            :class="{ 'mt-3': index > 0 }"
            :dir="row.lang === 'ar' ? 'rtl' : 'ltr'"
          >
            <label-path-trail :label="label" :lang="row.lang"></label-path-trail>
          </div>
        </v-card-text>
      </v-card>
    </v-menu>
    <v-chip
      v-else
      label
      size="small"
      color="primary"
      variant="tonal"
      class="flex-chip"
      :ripple="false"
    >
      {{ chipText }}
    </v-chip>
  `,
});

const LabelPathList = Vue.defineComponent({
  components: { LabelPathChip, LabelPathTrail },
  props: {
    labels: { type: Array, default: () => [] },
    limit: { type: Number, default: 6 },
  },
  data: () => ({
    expanded: false,
    translations: window.translations,
  }),
  computed: {
    visibleLabels() {
      return this.expanded ? this.labels : this.labels.slice(0, this.limit);
    },
    hiddenCount() {
      return Math.max(this.labels.length - this.limit, 0);
    },
    moreLabel() {
      return this.translations.moreLabels_(this.hiddenCount);
    },
    duplicateLeaves() {
      const counts = {};
      this.labels.forEach(label => {
        const key = LabelPathUtils.leafKey(label);
        if (key) counts[key] = (counts[key] || 0) + 1;
      });
      return Object.keys(counts).filter(key => counts[key] > 1);
    },
  },
  watch: {
    labels() {
      this.expanded = false;
    },
  },
  template: `
    <div>
      <div class="flex-chips label-path-list">
        <label-path-chip
          v-for="label in visibleLabels"
          :key="label.id || label.title"
          :label="label"
          :duplicate-leaves="duplicateLeaves"
        ></label-path-chip>
        <v-chip
          v-if="!expanded && hiddenCount"
          label
          size="small"
          variant="outlined"
          class="flex-chip text-medium-emphasis"
          style="border-style: dashed;"
          tabindex="0"
          @click="expanded = true"
          @keydown.enter.prevent="expanded = true"
          @keydown.space.prevent="expanded = true"
        >
          {{ moreLabel }}
        </v-chip>
      </div>
    </div>
  `,
});

window.LabelPathUtils = LabelPathUtils;
