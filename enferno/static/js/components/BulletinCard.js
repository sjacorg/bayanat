const BulletinCard = Vue.defineComponent({
  props: ['bulletin', 'close', 'thumb-click', 'active', 'log', 'diff', 'showEdit'],
  emits: ['edit', 'close'],
  watch: {
    bulletin: function (val, old) {
      this.$nextTick(() => {
        requestAnimationFrame(() => {
          this.mapLocations = aggregateBulletinLocations(this.bulletin);
        });
      });
      // Reset scroll for new bulletin
      this.$nextTick(() => {
        const el = this.$el?.querySelector('.bd-body');
        if (el) el.scrollTop = 0;
      });
    },
  },

  mounted() {
    this.$root.fetchDynamicFields({ entityType: 'bulletin' })

    if (this.bulletin?.id) {
      this.$nextTick(() => {
        requestAnimationFrame(() => {
          this.mapLocations = aggregateBulletinLocations(this.bulletin);
        });
      });
    }

    // Load collapsed sections from localStorage
    try {
      const saved = localStorage.getItem('bd-collapsed');
      if (saved) this.collapsed = JSON.parse(saved);
    } catch (e) {}
  },

  methods: {
    translate_status(status) {
      return translate_status(status);
    },

    showReview(bulletin) {
      return bulletin.status === 'Peer Reviewed' && bulletin.review;
    },

    logAllowed() {
      return this.$root.currentUser.view_simple_history && this.log;
    },

    diffAllowed() {
      return this.$root.currentUser.view_full_history && this.diff;
    },

    editAllowed() {
      if (typeof this.$root.editAllowed === 'function') {
        return this.$root.editAllowed(this.bulletin) && this.showEdit;
      }
      return false;
    },

    loadRevisions() {
      this.hloading = true;
      axios
        .get(`/admin/api/bulletinhistory/${this.bulletin.id}`)
        .then((response) => {
          this.revisions = response.data.items;
        })
        .catch((error) => {
          if (error.response) {
            console.log(error?.response?.data);
          }
        })
        .finally(() => {
          this.hloading = false;
        });
    },

    viewThumb(s3url) {
      this.$emit('thumb-click', s3url);
    },

    showDiff(e, index) {
      this.diffDialog = true;
      const dp = this.$jsondiffpatch.create({
        arrays: { detectMove: true },
        objectHash: function (obj, index) {
          return obj.name || obj.id || obj._id || '$$index:' + index;
        },
      });
      const delta = dp.diff(this.revisions[index + 1].data, this.revisions[index].data);
      if (!delta) {
        this.diffResult = 'Both items are Identical :)';
      } else {
        this.diffResult = this.$htmlFormatter.format(delta);
      }
    },

    onBodyScroll(e) {
      this.updateActiveSection(e.target);
    },

    updateActiveSection(container) {
      const sections = container.querySelectorAll('[data-section]');
      let active = '';
      for (const section of sections) {
        if (section.offsetTop - container.scrollTop < 120) {
          active = section.dataset.section;
        }
      }
      this.activeSection = active;
    },

    scrollToSection(key) {
      const el = this.$el.querySelector(`[data-section="${key}"]`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    },

    // Collapsible sections
    toggleSection(key) {
      this.collapsed[key] = !this.collapsed[key];
      try {
        localStorage.setItem('bd-collapsed', JSON.stringify(this.collapsed));
      } catch (e) {}
    },

    isSectionCollapsed(key) {
      return !!this.collapsed[key];
    },

    // Copy to clipboard
    copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        this.copyFeedback = true;
        setTimeout(() => { this.copyFeedback = false; }, 1500);
      });
    },

    // Section nav items (computed dynamically based on what's visible)
    navSections() {
      const b = this.bulletin;
      const sections = [];
      if (b.title || b.title_ar || b.sjac_title || b.sjac_title_ar) sections.push({ key: 'titles', icon: 'mdi-format-title', label: this.translations.title_ || 'Titles' });
      if (b.sources?.length || b.labels?.length || b.verLabels?.length) sections.push({ key: 'classification', icon: 'mdi-tag-multiple', label: this.translations.sources_ || 'Classification' });
      if (b.medias?.length) sections.push({ key: 'media', icon: 'mdi-image-multiple', label: this.translations.media_ || 'Media' });
      if (b.description) sections.push({ key: 'description', icon: 'mdi-text-box-outline', label: this.translations.description_ || 'Description' });
      sections.push({ key: 'spatial', icon: 'mdi-map-marker', label: this.translations.locations_ || 'Map' });
      if (b.events?.length) sections.push({ key: 'events', icon: 'mdi-calendar-alert', label: this.translations.events_ || 'Events' });
      if (b.bulletin_relations?.length || b.actor_relations?.length || b.incident_relations?.length) sections.push({ key: 'relations', icon: 'mdi-link-variant', label: 'Relations' });
      if (b.publish_date || b.documentation_date) sections.push({ key: 'dates', icon: 'mdi-calendar', label: 'Dates' });
      return sections;
    },
  },

  data: function () {
    return {
      translations: window.translations,
      diffResult: '',
      diffDialog: false,
      revisions: null,
      show: false,
      hloading: false,
      mapLocations: [],
      lightbox: null,
      mediasReady: 0,
      // UX enhancements
      collapsed: {},
      activeSection: '',
      copyFeedback: false,
    };
  },

  template: `

    <v-card class="rounded-0 bulletin-drawer">
      <!-- Sticky header -->
      <div class="bd-header" >
        <v-toolbar class="d-flex px-2 ga-2">
          <v-chip size="small" class="bd-copyable" @click="copyToClipboard(String(bulletin.id))">
            {{ translations.id_ }} {{ bulletin.id }}
            <v-icon size="x-small" class="ml-1 bd-copy-icon">mdi-content-copy</v-icon>
          </v-chip>

          <v-tooltip v-if="bulletin.originid" location="bottom">
              <template v-slot:activator="{ props }">
                  <v-chip
                      v-bind="props"
                      prepend-icon="mdi-identifier"
                      :href="bulletin.source_link"
                      target="_blank"
                      label
                      append-icon="mdi-open-in-new"
                      class="ml-1">
                      {{ bulletin.originid }}
                  </v-chip>
              </template>
              {{ translations.originid_ }}
          </v-tooltip>

          <v-btn variant="tonal" size="small" prepend-icon="mdi-pencil" v-if="editAllowed()" class="ml-2"
                 @click="$emit('edit',bulletin)">
            {{ translations.edit_ }}
          </v-btn>

          <v-btn size="small" class="ml-2" variant="tonal" prepend-icon="mdi-graph-outline"
                 @click.stop="$root.$refs.viz.visualize(bulletin)">
            {{ translations.visualize_ }}
          </v-btn>

          <template #append>
            <v-btn variant="text" icon="mdi-close" v-if="close" @click="$emit('close',$event.target.value)">
          </v-btn>
          </template>
        </v-toolbar>

        <div v-if="bulletin.assigned_to || bulletin.status" class="d-flex pa-0 ga-2" style="border-top: 1px solid #eaeaea">
          <div class="pa-2" v-if="bulletin.assigned_to">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-chip variant="text" v-bind="props" prepend-icon="mdi-account-circle-outline">
                  {{ bulletin.assigned_to['name'] }}
                </v-chip>
              </template>
              {{ translations.assignedUser_ }}
            </v-tooltip>
          </div>
          <v-divider v-if="bulletin.assigned_to" vertical></v-divider>
          <div class="pa-2" v-if="bulletin.status">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-chip variant="text" v-bind="props" prepend-icon="mdi-delta" class="mx-1">
                  {{ bulletin.status }}
                </v-chip>
              </template>
              {{ translations.workflowStatus_ }}
            </v-tooltip>
          </div>
        </div>
      </div>

      <!-- Copy feedback toast -->
      <transition name="bd-toast">
        <div v-if="copyFeedback" class="bd-toast">Copied!</div>
      </transition>

      <!-- Section nav dots -->
      <div class="bd-nav" v-if="navSections().length > 2">
        <v-tooltip v-for="s in navSections()" :key="s.key" location="left">
          <template v-slot:activator="{ props }">
            <button v-bind="props" class="bd-nav-dot" :class="{ 'bd-nav-dot--active': activeSection === s.key }" @click="scrollToSection(s.key)">
              <v-icon size="x-small">{{ s.icon }}</v-icon>
            </button>
          </template>
          {{ s.label }}
        </v-tooltip>
      </div>

      <!-- Scrollable body -->
      <div class="bd-body" @scroll="onBodyScroll">

      <!-- Metadata strips -->
      <div v-if="bulletin.roles?.length" class="bd-meta-strip">
        <v-icon color="blue-darken-3" size="small">mdi-lock</v-icon>
        <span class="bd-meta-label">{{ translations.accessRoles_ }}</span>
        <v-chip label size="small" v-for="role in bulletin.roles" :color="role.color" class="bd-chip">{{ role.name }}</v-chip>
      </div>

      <div v-if="bulletin.tags?.length" class="bd-meta-strip">
        <v-icon color="primary" size="small">mdi-tag-outline</v-icon>
        <span class="bd-meta-label">{{ translations.ref_ }}</span>
        <v-chip size="small" v-for="e in bulletin.tags" class="bd-chip">{{ e }}</v-chip>
      </div>

      <div v-if="bulletin.source_link && bulletin.source_link !== 'NA'" class="bd-meta-strip">
        <v-icon size="small">mdi-link-variant</v-icon>
        <span class="bd-meta-label">{{ translations.sourceLink_ }}</span>
        <a :href="bulletin.source_link" target="_blank" class="text-caption" style="color: #666; text-decoration: none;">
          {{ bulletin.source_link }}
          <v-icon size="x-small" class="ml-1">mdi-open-in-new</v-icon>
        </a>
      </div>

      <!-- Titles -->
      <div v-if="bulletin.title || bulletin.title_ar || bulletin.sjac_title || bulletin.sjac_title_ar" data-section="titles" class="bd-content-block">
        <div class="bd-section-label bd-collapsible" @click="toggleSection('titles')">
          <v-icon size="x-small">mdi-format-title</v-icon>{{ translations.title_ || 'Titles' }}
          <v-icon size="x-small" class="bd-collapse-icon">{{ isSectionCollapsed('titles') ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
        </div>
        <div v-show="!isSectionCollapsed('titles')">
          <div v-if="bulletin.title || bulletin.title_ar">
            <uni-field :caption="translations.originalTitle_" :english="bulletin.title" :arabic="bulletin.title_ar"></uni-field>
          </div>
          <div v-if="bulletin.sjac_title || bulletin.sjac_title_ar">
            <uni-field :caption="translations.title_" :english="bulletin.sjac_title" :arabic="bulletin.sjac_title_ar"></uni-field>
          </div>
        </div>
      </div>

      <!-- Classification zone -->
      <div v-if="bulletin.sources?.length || bulletin.labels?.length || bulletin.verLabels?.length" data-section="classification" class="bd-content-block">
        <div class="bd-section-label bd-collapsible" @click="toggleSection('classification')">
          <v-icon size="x-small">mdi-tag-multiple</v-icon>{{ translations.sources_ }}

          <v-icon size="x-small" class="bd-collapse-icon">{{ isSectionCollapsed('classification') ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
        </div>
        <div v-show="!isSectionCollapsed('classification')">
          <div v-if="bulletin.sources?.length" class="mb-3">
            <div class="bd-section-sublabel">{{ translations.sources_ }}</div>
            <div class="flex-chips">
              <v-chip size="small" class="flex-chip bd-chip" v-for="source in bulletin.sources" :key="source.id">{{ source.title }}</v-chip>
            </div>
          </div>
          <div v-if="bulletin.labels?.length" class="mb-3">
            <div class="bd-section-sublabel">{{ translations.labels_ }}</div>
            <div class="flex-chips">
              <v-chip label size="small" class="flex-chip bd-chip" v-for="label in bulletin.labels" :key="label.id">{{ label.title }}</v-chip>
            </div>
          </div>
          <div v-if="bulletin.verLabels?.length">
            <div class="bd-section-sublabel">{{ translations.verifiedLabels_ }}</div>
            <div class="flex-chips">
              <v-chip label size="small" class="flex-chip bd-chip" v-for="vlabel in bulletin.verLabels" :key="vlabel.id">{{ vlabel.title }}</v-chip>
            </div>
          </div>
        </div>
      </div>

      <!-- Media -->
      <div v-if="bulletin.medias && bulletin.medias.length" data-section="media" class="bd-content-block">
        <div class="bd-section-label bd-collapsible" @click="toggleSection('media')">
          <v-icon size="x-small">mdi-image-multiple</v-icon>{{ translations.media_ }}

          <v-icon size="x-small" class="bd-collapse-icon">{{ isSectionCollapsed('media') ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
        </div>
        <div v-show="!isSectionCollapsed('media')">
          <inline-media-renderer
            renderer-id="bulletin-card"
            :media="$root.expandedByRenderer?.['bulletin-card']?.media"
            :media-type="$root.expandedByRenderer?.['bulletin-card']?.mediaType"
            @ready="$root.onMediaRendererReady"
            @fullscreen="$root.handleFullscreen('bulletin-card')"
            @close="$root.closeExpandedMedia('bulletin-card')"
          ></inline-media-renderer>
          <media-grid prioritize-videos :medias="bulletin.medias" @media-click="$root.handleExpandedMedia({ rendererId: 'bulletin-card', ...$event })"></media-grid>
        </div>
      </div>

      <!-- Description -->
      <div v-if="bulletin.description" data-section="description" class="bd-content-block">
        <div class="bd-section-label bd-collapsible" @click="toggleSection('description')">
          <v-icon size="x-small">mdi-text-box-outline</v-icon>{{ translations.description_ }}
          <v-icon size="x-small" class="bd-collapse-icon">{{ isSectionCollapsed('description') ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
        </div>
        <div v-show="!isSectionCollapsed('description')" class="text-body-2">
          <read-more><div v-html="bulletin.description"></div></read-more>
        </div>
      </div>

      <!-- Spatial zone -->
      <div data-section="spatial" class="bd-content-block">
        <div class="bd-section-label bd-collapsible" @click="toggleSection('spatial')">
          <v-icon size="x-small">mdi-map-marker-multiple</v-icon>{{ translations.locations_ }}

          <v-icon size="x-small" class="bd-collapse-icon">{{ isSectionCollapsed('spatial') ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
        </div>
        <div v-show="!isSectionCollapsed('spatial')">
          <div v-if="bulletin.locations?.length" style="margin-bottom: 12px">
            <div class="flex-chips">
              <v-chip label size="small" prepend-icon="mdi-map-marker" class="flex-chip bd-chip" v-for="location in bulletin.locations" :key="location.id">{{ location.full_string }}</v-chip>
            </div>
          </div>
          <div style="border-radius: 6px; overflow: hidden">
            <global-map v-model="mapLocations"></global-map>
          </div>
        </div>
      </div>

      <!-- Events -->
      <div v-if="bulletin.events?.length" data-section="events" class="bd-content-block">
        <div class="bd-section-label bd-collapsible" @click="toggleSection('events')">
          <v-icon size="x-small">mdi-calendar-alert</v-icon>{{ translations.events_ }}

          <v-icon size="x-small" class="bd-collapse-icon">{{ isSectionCollapsed('events') ? 'mdi-chevron-down' : 'mdi-chevron-up' }}</v-icon>
        </div>
        <div v-show="!isSectionCollapsed('events')">
          <event-card v-for="(event, index) in bulletin.events" :number="index+1" :key="event.id" :event="event"></event-card>
        </div>
      </div>

      <!-- Relations -->
      <div data-section="relations" class="bd-relations">
        <related-bulletins-card v-if="bulletin" :entity="bulletin" :relationInfo="$root.btobInfo"></related-bulletins-card>
        <related-actors-card v-if="bulletin" :entity="bulletin" :relationInfo="$root.atobInfo"></related-actors-card>
        <related-incidents-card v-if="bulletin" :entity="bulletin" :relationInfo="$root.itobInfo"></related-incidents-card>
      </div>

      <!-- Dates -->
      <div v-if="bulletin.publish_date || bulletin.documentation_date" data-section="dates" class="bd-date-strip">
        <div v-if="bulletin.publish_date">
          <div class="bd-section-label" style="margin-bottom: 2px"><v-icon size="x-small">mdi-calendar-check</v-icon>{{ translations.publishDate_ }}</div>
          <div class="bd-date-value">{{ $root.formatDate(bulletin.publish_date) }}</div>
        </div>
        <div v-if="bulletin.documentation_date">
          <div class="bd-section-label" style="margin-bottom: 2px"><v-icon size="x-small">mdi-file-document-edit-outline</v-icon>{{ translations.documentationDate_ }}</div>
          <div class="bd-date-value">{{ $root.formatDate(bulletin.documentation_date) }}</div>
        </div>
      </div>

      <!-- Dynamic fields -->
      <template v-for="field in $root.cardDynamicFields('bulletin')">
        <template v-if="$root.isFieldActive(field) && !['title','sjac_title','description','global_map','sources','events_section','labels','ver_labels','locations','related_bulletins','related_actors','related_incidents','publish_date','documentation_date'].includes(field.name)">
          <div v-if="Array.isArray(bulletin?.[field.name]) && $root.isFieldActiveAndHasContent(field, field.name, bulletin?.[field.name])" class="bd-section">
            <div class="bd-section-label">{{ field.title }}</div>
            <div class="flex-chips">
              <v-chip label size="small" class="flex-chip bd-chip" v-for="value in bulletin?.[field.name]" :key="value">
                {{ $root.findFieldOptionByValue(field, value)?.label ?? value }}
              </v-chip>
            </div>
          </div>
          <div v-else-if="field.field_type === 'datetime' && $root.isFieldActiveAndHasContent(field, field.name, bulletin?.[field.name])" class="bd-section">
            <uni-field :caption="field.title" :english="$root.formatDate(bulletin?.[field.name])"></uni-field>
          </div>
          <div v-else-if="$root.isFieldActiveAndHasContent(field, field.name, bulletin?.[field.name])" class="bd-section">
            <uni-field :caption="field.title" :english="$root.findFieldOptionByValue(field, bulletin?.[field.name])?.label ?? bulletin?.[field.name]"></uni-field>
          </div>
        </template>
      </template>

      <!-- Review -->
      <v-card v-if="showReview(bulletin)" variant="outlined" elevation="0" class="ma-3" color="teal-lighten-2">
        <v-card-text>
          <div class="px-1">{{ translations.review_ }}</div>
          <read-more>
            <div v-html="bulletin.review" class="pa-1 my-2 grey--text text--darken-2">
            </div>
          </read-more>
          <v-chip class="mt-4" color="primary">{{ bulletin.review_action }}</v-chip>
        </v-card-text>
      </v-card>

      <!-- Log -->
      <v-card v-if="logAllowed()" variant="flat">
        <v-toolbar density="compact">
          <v-toolbar-title>
          <v-btn variant="plain" class="text-subtitle-2" append-icon="mdi-history" :loading="hloading"
                 @click="loadRevisions">
            {{ translations.logHistory_ }}

          </v-btn>
            </v-toolbar-title>
        </v-toolbar>

        <v-card-text>
          <template v-for="(revision,index) in revisions">
            <v-sheet class="my-1 pa-3  align-center d-flex">
              <span class="caption"><read-more class="mb-2">{{ revision.data['comments'] }}</read-more>
                <v-chip label size="small"
                >{{ translate_status(revision.data.status) }}</v-chip> -
                {{ $root.formatDate(revision.created_at, $root.dateFormats.standardDatetime, $root.dateOptions.local) }}
                - {{ translations.by_ }} {{ revision.user.username }}</span>
              <v-spacer></v-spacer>

              <v-btn icon="mdi-vector-difference" v-if="diffAllowed()" v-show="index!=revisions.length-1"
                     @click="showDiff($event,index)"
                     class="mx-1" variant="flat" size="small"
              >

              </v-btn>

            </v-sheet>

          </template>

        </v-card-text>

      </v-card>

      </div><!-- end bd-body -->

      <v-dialog
          v-model="diffDialog"
          max-width="770px"
      >
        <v-card class="diff-dialog-content pa-5">
          <v-card-text>
            <div v-html="diffResult">
            </div>
          </v-card-text>
        </v-card>

      </v-dialog>
    </v-card>


  `,
});
