Vue.component('event-card',{
    props : ['event', 'number'],

    template : `

    <v-card height="100%" class="event-card mb-2 mt-1"  elevation="0" outlined>
        <v-card-text class="py-2 ">
          <v-avatar size="18" class="caption" color="grey lighten-4 float-right" outlined>{{number}}</v-avatar>
          
          
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
            top right 
        v-if="event.eventtype"
        
        color="teal lighten-5"
        x-small
        >{{event.eventtype.title}}</v-chip>
          

        <span class="subtitle-2 black--text">{{event.title}}</span>
          
          </v-card-text>
        <v-card-text class="caption">
                    
           <div  v-if="event.comments">
            {{event.comments}}
           </div>
          
      
      
      

        <v-spacer></v-spacer>
    
      <v-chip class="my-2" color="grey lighten-4" small v-if="event.location && event.location.full_string" label>
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

    <slot name="actions"></slot>   
     
    
  </v-card>


    `





})