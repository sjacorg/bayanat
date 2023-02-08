Vue.component("mp-field", {
    props: {
        title: String,
        field: String,
        type: Number,
        i18n: Object

    },
    data: function () {
        return {
            output: ''
        }
    },
    methods: {
        formatReporter(rep) {
            let output = '';
            if (rep.name) {
                output += this.i18n.name_ + ': ' + rep.name + '<br>';
            }
            if (rep.contact) {
                output += this.i18n.contact_ + ': ' + rep.contact + '<br>';
            }
            if (rep.relationship) {
                output += this.i18n.relationship_ + ': ' + rep.relationship + '<br>';
            }
            if (output.length) {
                output = '<div class="elevation-1 my-3 pa-2 yellow lighten-5">' + output + '</div>';
            }
            return output;

        },

        formatOutput() {
            // format the display this field based on its type


            // do some preprocessing for boolean fields
            if (this.field === true) {
                this.output = 'Yes'
                return;
            }

            if (this.field === false) {
                this.output = 'No'
                return;
            }


            if (this.type === 1) {

                // type 1 =  options + details
                if (this.field?.opts) {

                    this.output = this.field.opts + ': ';
                }

                if (this.field?.details) {
                    this.output += this.field.details || '-';
                }
                return

            }

            if (this.type === 2) {
                // type 2 = Reporters : list of objects
                let out = ''
                if (this.field?.length) {
                    for (const x of this.field) {
                        out += this.formatReporter(x);
                    }
                    this.output = out;
                    return
                }
                return '-'
            }
            // final case : simple field

            this.output = this.field;


        }


    },
    computed: {
        show() {

            if (this.type == 1) {
                if (this.field) {
                    return true
                }
                return false;
            } else {
                if (this.field && this.field.length && Object.keys(this.field[0]).length) {
                    return true;
                }
                return false;

            }


        }
    },
    mounted() {
        this.formatOutput();


    },


    template: `
      <v-sheet v-if="show" class="pa-1 pb-2 mb-2" color="transparent">

      <div class="caption grey--text text--darken-1">{{ title }}</div>

      <span v-html="output"></span>
      </v-sheet>

    `

});
