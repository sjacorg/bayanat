Vue.component("mix-iii", {
    props: {
        title: String,
        value: [],
        items: [],
        i18n: {}

    },
    data: function () {
        return {
            reporters: []
        }
    },

    watch: {
        value: function (val) {
            this.reporters = val || [];
        },
        reporters: {
            handler: 'refresh',
            deep: true
        }

    },

    mounted: function () {


    },


    methods: {

        addReporter(){

          this.reporters.push({})
        },
        removeMe(i){
        this.reporters.splice(i, 1);
        },
        refresh() {
            this.$emit('input', this.reporters);

        }
    },
    template:
        `
    <v-card class="pa-3 elevation-1" color="yellow lighten-4">


    <v-card-title class="subtitle-2">{{ i18n.reportingPersons_ }} <v-spacer></v-spacer> 
    <v-btn small @click="addReporter" color="primary lighten-1" class="elevation-0" fab><v-icon>mdi-plus</v-icon></v-btn></v-card-title> 

      <v-card-text>
      
      <v-card class="my-3" color="fifth lighten-1" v-for="r, i in reporters" :key="i">
      <v-card-title> <v-spacer></v-spacer> <v-btn @click="removeMe(i)" small fab text color="primary"><v-icon>mdi-close</v-icon></v-btn></v-card-title>
      <v-card-text>
      <v-text-field :label="i18n.name_" v-model="reporters[i].name" ></v-text-field>
      <v-textarea rows="1" :label="i18n.contactInfo_" v-model="reporters[i].contact"></v-textarea>
      <v-textarea rows="1" :label="i18n.relationship_"  v-model="reporters[i].relationship"></v-textarea>

      </v-card-text>
          
    </v-card>
     
      
        </v-card-text>
        
    </v-card>

    `,
});
