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
        <v-card  hover class="ma-2" v-if="!incident.restricted">
          <v-toolbar density="compact" class="d-flex px-2">
            <v-chip size="small" variant="flat" color="primary">{{ translations.id_ }} {{ incident.id }}</v-chip>
            
          </v-toolbar>
          
          <v-card-title class="text-wrap text-break">
            <v-row>
              <v-col><uni-field disable-spacing :caption="translations.title_" :english="incident.title"></uni-field></v-col>
            </v-row>
          </v-card-title>
          <v-divider></v-divider>
          <slot name="header"></slot>
            
            
          <v-card-actions class="justify-end">
            <slot name="actions"></slot>
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  @click.capture="$root.previewItem('/admin/api/incident/'+incident.id+'?mode=3')"
                  color="secondary"
                  variant="outlined"
                  icon="mdi-magnify-expand"
                  size="small"
                ></v-btn>
              </template>
              {{ translations.preview_ }}
            </v-tooltip>
            <v-tooltip v-if="showHide" location="bottom">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  @click="hide=true"
                  color="secondary"
                  variant="outlined"
                  icon="mdi-minus"
                  size="small"
                ></v-btn>
              </template>
              {{ translations.hideFromResults_ }}
            </v-tooltip>
          </v-card-actions>
        </v-card>
        <v-card disabled elevation="0" v-else class="restricted">

          <v-card-text>{{ incident.id }} - {{ translations.restricted_ }}</v-card-text>

        </v-card>
      </template>
    `,
});
