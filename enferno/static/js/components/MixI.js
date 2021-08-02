Vue.component("mix-i", {
    props: {
        title: String,
        value: {},
        i18n: {}
    },
    data: function () {
        return {
            mix: {}
        };
    },

    watch: {
        value: function (val) {
            if (val) {
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
      <v-radio-group v-model="mix.opts"  >
      <v-radio value="Yes" :label="i18n.yes_"></v-radio>
      <v-radio value="No" :label="i18n.no_"></v-radio>
      <v-radio value="Unknown" :label="i18n.unknown_"></v-radio>
      
        </v-radio-group>
        </div>
      <div class="flex-grow-1 ml-2">
      <v-textarea rows="1" :label="i18n.details_" v-model="mix.details" > </v-textarea>
      
        </div>
      
        </v-card-text>
        
    </v-card>

    `,
});
