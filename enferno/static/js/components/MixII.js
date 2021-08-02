Vue.component("mix-ii", {
    props: {
        title: String,
        multiple: Boolean,
        value: {},
        items: [],
        i18n: {}
    },
    data: function () {
        return {
            mix: {}
        };
    },

    watch: {
        value: function (val) {
            if (val){
            this.mix = val;
            }

        },
        mix: {
            handler: 'refresh',
            deep: true
        }

    },

    mounted: function () {


    },

    methods: {
        refresh() {
            this.$emit('input', this.mix);

        }
    },
    template:
        `
<v-card class="pa-3 elevation-1" color="yellow lighten-4">
    <v-card-title class="subtitle-2">{{title}}</v-card-title> 

      <v-card-text>
      <div>
      <v-select v-model="mix.opts" :items="items" :multiple="this.multiple">
        
        </v-select>
        </div>
      <div class="flex-grow-1 ml-2">
      <v-textarea rows="2" :label="i18n.details_" v-model="mix.details" > </v-textarea>
      
        </div>
      
        </v-card-text>
        
    </v-card>

    `,
});
