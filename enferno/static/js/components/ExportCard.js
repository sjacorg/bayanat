const ExportCard = Vue.defineComponent({
  props: ['exp', 'close', 'adminMode'],

  watch: {
    exp: function (val, old) {},
  },
  filters: {
    capitalize(value) {
      if (!value) return '';
      value = value.toString();
      return value.charAt(0).toUpperCase() + value.slice(1);
    },
  },

  mounted() {
    this.exp.expires_on = this.formatDate(this.exp.expires_on, { iso: true, forceZ: true });

    this.loadExportItems();
  },

  methods: {
    formatDate: formatDate,
    loadExportItems() {
      const q = [{ ids: this.exp.items }];

      axios
        .post(`/admin/api/bulletins/?page=${this.page}&per_page=${this.per_page}`, { q: q })
        .then((res) => {
          this.items = [...this.items, ...res.data.items];
          this.showLoadMore = this.per_page * this.page < res.data.total;
          this.page += 1;
        });
    },

    showApprove(item) {
      return item.status === 'Pending' || item.status === 'Failed';
    },

    showReject(item) {
      return !(item.status === 'Rejected' || item.status === 'Expired');
    },

    showChangeExpiry(item) {
      return item.status === 'Approved';
    },

    changeExpiry() {
      this.expiryFieldDisabled = false;
    },
  },

  data: function () {
    return {
      formatDateOptions: { forceZ: true },
      translations: window.translations,
      expiryFieldDisabled: true,
      showLoadMore: false,
      per_page: 5,
      page: 1,
      items: [],
    };
  },

  template: `
    <v-card class="mx-auto pa-3">
      <v-card class="mx-2">
        <v-card-text>

          <!-- Export ID chip -->
          <v-chip size="small" label color="primary" class="mx-2">
            {{ translations.id_ }} #{{ exp.id }}
          </v-chip>

          <!-- Table chip -->
          <v-chip size="small" label color="primary" class="mx-2">
            {{ exp.table.toUpperCase() }}
          </v-chip>

          <!-- File format chip -->
          <v-tooltip location="top" :text="translations.exportFormat_ + ': ' + exp.file_format">
            <template #activator="{props}">
              <v-avatar density="compact" v-bind="props" color="primary" class="mx-2" label>
                <v-icon size="small" center v-if="exp.file_format === 'json'">mdi-code-json</v-icon>
                <v-icon size="small" center v-if="exp.file_format === 'pdf'">mdi-file-pdf-box</v-icon>
                <v-icon size="small" center v-if="exp.file_format === 'csv'">mdi-file-delimited-outline</v-icon>
              </v-avatar>
            </template>
          </v-tooltip>

          <!-- Media chip -->
          <v-tooltip location="bottom" :text="translations.includeMedia_ + ': ' + exp.include_media">
            <template #activator="{props}">
              <v-avatar density="compact" v-bind="props" class="mx-2" size="small" label>
                <v-icon size="small" center v-if="exp.include_media">mdi-paperclip-check</v-icon>
                <v-icon size="small" center v-if="!exp.include_media">mdi-paperclip-off</v-icon>
              </v-avatar>
            </template>
          </v-tooltip>
        </v-card-text>

        <!-- Requester chip -->
        
        <v-chip prepend-icon="mdi-account-circle-outline" label class="pa-2 mx-2 my-2">
          {{ exp.requester.name }}
        </v-chip>
        
        <!-- Approver chip -->
        <v-chip prepend-icon="mdi-account-circle-outline" label class="pa-2 mx-2 my-2" v-if="exp.approver">
          {{ exp.approver.name }}
        </v-chip>

        <!-- Status chip -->
        <v-tooltip location="bottom" :text="translations.status_">
          <template #activator="{props}">
            <v-chip v-bind="props" class="mx-2 my-2" size="small" label prepend-icon="mdi-delta">
              {{ exp.status }}
            </v-chip>
          </template>
        </v-tooltip>
      </v-card>

      <!-- Dates fields -->
      <div class="d-flex">
        <uni-field :caption="translations.requestedOn_" :english="formatDate(exp.created_at, formatDateOptions)"></uni-field>
        <uni-field :caption="translations.expiresOn_" :english="formatDate(exp.expires_on, formatDateOptions)"></uni-field>
      </div>

      <!-- Admin actions cards -->
      <v-card class="mx-2" v-if="adminMode">
        <v-toolbar density="compact">
          <v-toolbar-title class="text-subtitle-2"> {{ translations.adminActions_ }}</v-toolbar-title>
        </v-toolbar>
        <v-card-text>


          <!-- Approve button -->
          <v-btn
              v-if="showApprove(exp)"
              :disabled="exp.complete"
              class="ml-2"
              @click.stop="$emit('approve', exp.id)"
              size="small"
              color="primary"
              prepend-icon="mdi-check"
          >

            {{ translations.approve_ }}
          </v-btn>

          <!-- Reject button -->
          <v-btn
              v-if="showReject(exp)"
              class="ml-2"
              @click.stop="$emit('reject', exp.id)"
              size="small"
              prepend-icon="mdi-close"
              color="error">

            <span v-if="exp.status=='Approved'">{{ translations.expireNow_ }}</span>
            <span v-else>{{ translations.reject_ }}</span>

          </v-btn>

          <!-- Change expiry date button -->
          <v-btn
              v-if="expiryFieldDisabled && showChangeExpiry(exp)"
              :disabled="exp.expired"
              class="ml-2"
              @click="changeExpiry"
              size="small"
              prepend-icon="mdi-calendar-edit"
              color="primary">
            {{ translations.changeExpiry_ }}
          </v-btn>

          <!-- Set expiry date button -->
          <v-btn
              v-if="!expiryFieldDisabled && showChangeExpiry(exp)"
              :disabled="exp.expired"
              class="ml-2"
              @click.stop="$emit('change', exp.id, exp.expires_on)"
              size="small"
              prepend-icon="mdi-calendar-edit"
              color="primary">
            {{ translations.setExpiry_ }}
          </v-btn>

        </v-card-text>

        <v-card-item>
          <!-- Expiry date text field -->
          <v-text-field
              v-if="!expiryFieldDisabled && showChangeExpiry(exp)"
              type="datetime-local"
              label="{{ translations.exportExpiry_ }}"
              v-model="exp.expires_on"
          >
          </v-text-field>
        </v-card-item>
      </v-card>

      <!-- Refs -->
      <v-card v-if="exp.tags && exp.tags.length" class="ma-2 pa-2 d-flex align-center flex-grow-1">
        <div class="text-subtitle-2 mr-2">{{ translations.tags_ }}</div>
        <v-chip size="x-small" v-for="t in exp.tags" class="caption  mx-1">{{ t }}</v-chip>
      </v-card>

      <!-- Comment -->
      <uni-field :caption="translations.comments_" :english="exp.comment"></uni-field>

      <!-- Related Bulletins -->
      <v-card class="ma-2" v-if="items">
        <v-card-text v-if="exp.table == 'bulletin'">
          <div class="pa-2 text-subtitle-2 ">{{ translations.relatedBulletins_ }}</div>
          <bulletin-result  v-for="item in items" :bulletin="item"></bulletin-result>
        </v-card-text>

        <v-card-text v-if="exp.table == 'actor'">
          <div class="pa-2 text-subtitle-2 ">{{ translations.relatedActors_ }}</div>
          <actor-result  v-for="item in items" :actor="item"></actor-result>
        </v-card-text>


        <v-card-text v-if="exp.table == 'incident'">
          <div class="pa-2 text-subtitle-2 ">{{ translations.relatedIncidents_ }}</div>
          <incident-result  v-for="item in items" :incident="item"></incident-result>
        </v-card-text>


        <v-card-actions>
          <v-btn
              size="small"
              class="ma-auto caption"
              elevation="0"
              @click="loadExportItems"
              v-if="showLoadMore"
              append-icon="mdi-chevron-down"
          >
            {{ translations.loadMore_ }}
          </v-btn>
        </v-card-actions>
      </v-card>

    </v-card>
  `,
});
