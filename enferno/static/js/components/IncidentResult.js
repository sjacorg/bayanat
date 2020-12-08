Vue.component("incident-result", {
  props: ['incident','hidden','showHide'],
  template: `
    <v-card outlined class="ma-2" v-if="!hidden"  >     
        
        <v-card-title class="d-flex">
          <v-chip label small color="gv darken-2" dark>ID: {{incident.id}} </v-chip>
          <v-spacer></v-spacer>
        </v-card-title>
        <slot name="header"></slot>            
        <v-card-text>
            
          <div class="subtitle-2 black--text mb-1 mt-2" >
            {{incident.title}}
          </div>
          <div v-html="incident.description" class="caption">
          </div>
          
                 
          
        </v-card-text>
        <v-card-actions>
            <slot name="actions"></slot>   
            <v-btn v-if="showHide" @click="hidden=true" small depressed  color="grey lighten-4">Hide</v-btn>
          <v-btn text small icon color="gv darken-1" @click.stop="$root.previewItem('/admin/api/incident/'+incident.id)"><v-icon>mdi-eye</v-icon></v-btn>
        </v-card-actions>
      </v-card >
    `
});
