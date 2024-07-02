const IncidentResult = Vue.defineComponent({
  props: ['incident', 'hidden', 'showHide', 'i18n'],

  data: () => {
    return {
      hide: this.hidden || false,
    }
  },

  template: `
      <template v-if="!hide">
        <v-card  hover class="ma-2" v-if="!incident.restricted">
          <v-toolbar density="compact" class="d-flex px-2">
            <v-chip size="small" variant="flat" color="primary">{{ i18n.id_ }} {{ incident.id }}</v-chip>
            
          </v-toolbar>
          
          <v-card-title class="text-subtitle-2">{{incident.title}}</v-card-title>
            <v-divider></v-divider>
          <slot name="header"></slot>
            
            
          <v-card-actions class="justify-end">
            <slot name="actions"></slot>
            <v-btn v-if="showHide" @click="hide=true" size="small" > {{ i18n.hide_ }}</v-btn>
            <v-btn icon="mdi-eye" size="small" color="primary"
                   @click.capture="$root.previewItem('/admin/api/incident/'+incident.id+'?mode=3')">
            </v-btn>
          </v-card-actions>
        </v-card>
        <v-card disabled elevation="0" v-else class="restricted">

          <v-card-text>{{ incident.id }} - {{ i18n.restricted_ }}</v-card-text>

        </v-card>
      </template>
    `,
});
