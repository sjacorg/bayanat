Vue.component('pop-date-field', {
    props: ['value', 'label'],

    data: function() {
        return {
            menu: false,
            date: this.value,
            id: null,

        }
    },
    created() {
        this.id = 'date' + this._uid;

        this.$emit('input', this.value);



    }
    ,
    watch: {
        date: function (val) {

            this.$emit('input', val);
        },
        value: function (val, old) {


            if (val != old) {
                this.date = val;
            }

        }

    },


    template: `


        <v-menu
                v-model="menu"
                ref="menu"
                transition="scale-transition"
                offset-y
                max-width="290px"
                min-width="290px"
                :close-on-content-click="false"
        >
            <template v-slot:activator="{ on, attrs }">
                <v-text-field
                        
                        @click:prepend="menu=true"
                        dense
                        type="date"
                        min="1900-01-01" max="2040-01-01"
                        v-model="date"
                        v-bind="attrs"
                        :label="label"
                        persistent-hint
                        prepend-icon="mdi-calendar"
                        clearable
                        @click:clear="date = null"
                ></v-text-field>
            </template>


            <v-date-picker
                    scrollable
                    no-title
                    v-model="date"
                    @input="menu = false"
            >
                <v-spacer></v-spacer>

            </v-date-picker>
        </v-menu>




    `
})