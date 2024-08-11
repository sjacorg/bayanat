const EventCard = Vue.defineComponent({
    props : ['event', 'number'],

  template: `

    <v-card hover min-width="300px" height="100%" class="event-card pa-3 mb-2 mt-1">
      <v-card-text class="align-center ga-2">
        
        
        <v-chip
            
            v-if="event.eventtype"
            color="teal"
            size="small"
            class="mr-2"
        >{{ event.eventtype?.title }}
        </v-chip>


        <v-chip variant="text"
                :append-icon=" event.estimated? 'mdi-information': ''"
                class="text-subtitle-2 ">{{ event.title }}</v-chip>
        
        
        <v-avatar  class="text-caption float-end" size="small" variant="tonal">{{ number }}
        </v-avatar>

      </v-card-text>
      <v-card-text class="text-caption">

        <div v-if="event.comments">
          {{ event.comments }}
        </div>


        <v-spacer></v-spacer>

        <v-chip prepend-icon="mdi-map-marker" color="grey-darken-1" class="my-2"  v-if="event.location?.full_string"
                label>
          
          {{ event.location.full_string }}
        </v-chip>


        <div v-if="event.from_date||event.to_date">
          <v-divider class="my-2"></v-divider>
          
          <v-chip prepend-icon="mdi-calendar" label variant="text"  class="mr-1 text-caption" v-if="event.from_date">
        {{ event.from_date }}
      </v-chip>
          <span class="caption" v-if="event.to_date">
        -> {{ event.to_date }}
      </span>
        </div>
      </v-card-text>

      <slot name="actions"></slot>


    </v-card>


  `,
});
