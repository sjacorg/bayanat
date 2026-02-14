const IncidentResult = Vue.defineComponent({
  props: ['incident', 'hidden', 'showHide'],

  data: () => {
    return {
      translations: window.translations,
      hide: this.hidden || false,
    }
  },

  template: `
      <template v-if="!hide">
        <v-card hover class="ma-2" v-if="!incident.restricted">
          <v-toolbar density="compact" class="d-flex px-2">
            <v-chip size="small" variant="flat" color="primary">{{ translations.id_ }} {{ incident.id }}</v-chip>
            <v-spacer></v-spacer>
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  @click.capture="$root.previewItem('/admin/api/incident/'+incident.id+'?mode=3')"
                  variant="text"
                  icon="mdi-magnify-expand"
                  size="x-small"
                ></v-btn>
              </template>
              {{ translations.preview_ }}
            </v-tooltip>
            <v-tooltip v-if="showHide" location="bottom">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  @click="hide=true"
                  variant="text"
                  icon="mdi-minus"
                  size="x-small"
                ></v-btn>
              </template>
              {{ translations.hideFromResults_ }}
            </v-tooltip>
          </v-toolbar>

          <v-card-title class="text-wrap text-break pt-0">
            <uni-field class="pa-0" disable-spacing :english="incident.title" :arabic="incident.title_ar"></uni-field>
          </v-card-title>
          <v-divider></v-divider>
          <slot name="header"></slot>

          <slot name="actions"></slot>
        </v-card>
        <v-card disabled elevation="0" v-else class="restricted">
          <v-card-text>{{ incident.id }} - {{ translations.restricted_ }}</v-card-text>
        </v-card>
      </template>
    `,
});
