Vue.component('uni-field', {
  props: {
    caption: String,
    english: String,
    arabic: String,
  },
  data: function () {
    return {
      sw: true,
    };
  },

  mounted: function () {},

  methods: {},
  template: `
     
     <v-card  v-if="english||arabic" outlined class="mx-2 my-1 pa-2 d-flex align-center flex-grow-1" color="grey lighten-5 " > 
     <div v-if="caption" class="caption grey--text mr-2">{{caption}}</div>
      <div class="caption black--text" v-if="sw">{{english}}</div>
        <div class="caption black--text" v-else>{{arabic}} </div>
      <v-btn v-if="arabic"
                      color="grey lighten-2"
                      outlined
                      x-small
                      fab
                      absolute
                      right
                      
                      @click="sw= !sw "
                      class="d-inline swh"
                      
                      
                      ><v-icon>mdi-web</v-icon>
        </v-btn>
        
    </v-card>
    `,
});
