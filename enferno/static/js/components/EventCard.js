Vue.component('event-card',{
    props : ['event'],

    template : `

    <v-card height="100%" class="event-card mb-2 mt-1" flat elevation="0" outlined>
        <v-card-text>
          <v-tooltip top v-if="event.estimated">
            <template v-slot:activator="{ on }">
              <v-icon v-on="on" color="orange lighten-4"
                >mdi-information</v-icon
              >
            </template>
            <span>Estimated</span>
          </v-tooltip>  
          <v-chip
            absolute
            top right mt-3
        v-if="event.eventtype"
        
        color="teal lighten-5"
        x-small
        >{{event.eventtype.title}}</v-chip>

        <span class="caption black--text">{{event.title}}</span>
          <v-sheet class="pa-3 my-2 caption" v-if="event.comments">
            {{event.comments}}
            
          </v-sheet>
      
      
      

        <v-spacer></v-spacer>
    
      <v-chip color="grey lighten-4" small v-if="event.location && event.location.full_string" label>
      <v-icon x-small left>mdi-map-marker </v-icon>
      <span class="caption font-italic">{{event.location.full_string}}</span>
      </v-chip>
    
      
      <div v-if="event.from_date||event.to_date">
        <v-divider class="my-2"></v-divider>
      <v-icon small left>mdi-calendar</v-icon>
      <span class="mr-1 caption" v-if="event.from_date">
        {{event.from_date}}
      </span>
      <span class="caption" v-if="event.to_date">
        -> {{event.to_date}}
      </span>
      </div>
    </v-card-text>
    
     
    
  </v-card>


    `





})