Vue.component("mp-field", {
    props: {
        title: String,
        field: String,
        type: String,
        i18n: Object

    },
    data: function() {
        return {
            output: null
        }
    },
    methods : {
      formatReporter(rep) {
          let output = '';
          if (rep.name){
              output += this.i18n.name_ + ': ' + rep.name + '<br>';
          }
          if (rep.contact){
              output +=  this.i18n.contact_ +': ' + rep.contact  + '<br>';
          }
          if (rep.relationship){
              output += this.i18n.relationship_ + ': ' + rep.relationship  + '<br>';
          }
          if(output.length){
              output = '<div class="elevation-1 my-3 pa-2 yellow lighten-5">' + output + '</div>';
          }
          return output;

      }
    },
    mounted() {
        this.output = this.field;

        // do some preprocessing for boolean fields
        if (this.field === true) {
            this.output = 'Yes'
        }

        if (this.field === false) {
            this.output = 'No'
        }



        if (this.type == 1){

            if (this.field && this.field.opts) {
            this.output = this.field.opts +  ': ';
            }

            if (this.field && this.field.details) {
            this.output += this.field.details || '-';
            }

        }

        if (this.type==2) {
                let out = ''
            if (this.field && this.field.length){
                for (x of this.field) {
                    out += this.formatReporter(x);


                }
                this.output = out;
            }
        }


    },



    template: `
         <v-sheet v-if="field" class="pa-1 pb-2 mb-2" color="transparent">
        <div class="caption grey--text text--darken-1">{{title}}</div>
        
        <span v-html="output"></span>
        </v-sheet>
    
    `

});
