Vue.component("bulletin-result", {
  props: ['bulletin','hidden','showHide', 'i18n'],

  template: `
    <v-card outlined class="ma-2"  v-if="!hidden">     
        <v-card-title class="d-flex">
            <v-chip label small color="gv darken-2" dark>{{ i18n.id_ }} {{bulletin.id}} </v-chip>
            <v-chip :href="bulletin.source_link" target="_blank" color="lime darken-3" class="white--text ml-1"  label small ># {{bulletin.originid}}</v-chip>
            <v-spacer></v-spacer>
            <v-chip v-if="bulletin.publish_date" small color="grey lighten-4">{{bulletin.publish_date}}</v-chip>
        </v-card-title>
        <slot name="header"></slot>            
        <v-card-text>
            
          <div class="subtitle-2 black--text mb-1 mt-2" >
            {{bulletin.title}}
          </div>
          <div v-html="bulletin.description" class="caption">
          </div>
          <v-divider class="my-2"></v-divider>
          <div class="caption">{{ i18n.locations_ }}</div>
          <v-chip-group
             column
          >
        <v-chip small color="grey lighten-4" v-for="location in bulletin.locations" :key="location">
          {{ location.full_string }}
        </v-chip>
      </v-chip-group>


      <div class="caption mt-2">{{ i18n.sources_ }}</div>
          <v-chip-group
             column
          >
        <v-chip small color="grey lighten-4" v-for="source in bulletin.sources" :key="source">
          {{ source.title }}
        </v-chip>
      </v-chip-group>
          
        </v-card-text>
        <v-card-actions>
            <slot name="actions"></slot>  
            <v-btn v-if="showHide" @click="hidden=true" small depressed  color="grey lighten-4"> {{ i18n.hide_ }}</v-btn>
          <v-btn @click.capture="$root.previewItem('/admin/api/bulletin/'+bulletin.id+'?mode=3')" text small icon color="gv darken-1" ><v-icon>mdi-eye</v-icon></v-btn>
        </v-card-actions>
      </v-card >
    `
});
