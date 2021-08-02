Vue.component('preview-card', {
    props: ['item', 'value', 'i18n'],
    watch: {
        value(val) {
            this.preview = val;
        },
        preview(val) {

            this.$emit('input', val)
        }
    },
    mounted() {

    },
    data: function () {
        return {
            preview: this.preview || false,
        };
    },

    template:
            `
        <v-dialog overlay="false" max-width="1000" v-model="preview">

            <v-card v-if="preview" outlined>
                <v-toolbar>
                    <v-spacer></v-spacer>
                    <v-btn outlined color="grey darken-2" @click.stop.prevent="$root.preview = false" x-small right
                           top="10" fab>
                        <v-icon>mdi-close</v-icon>
                    </v-btn>

                </v-toolbar>


                <bulletin-card :i18n="i18n" v-if="item && item.class=='Bulletin'" :close="false"
                               :bulletin="item"></bulletin-card>
                <actor-card :i18n="i18n" v-if="item && item.class=='Actor'" :close="false" :actor="item"></actor-card>
                <incident-card :i18n="i18n" v-if="item && item.class=='Incident'" :close="false"
                               :incident="item"></incident-card>

            </v-card>


        </v-dialog>

    `
})