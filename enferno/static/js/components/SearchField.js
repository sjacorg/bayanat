Vue.component('search-field',
    {
        props: ['value', 'label', 'multiple', 'itemText', 'itemValue', 'api', 'queryParams','disabled'],
        data: () => {
            return {
                loading: false,
                items: [],
                searchInput: ''
            }
        },
        mounted() {

            //enable copy paste 
            let dateInputs = document.querySelectorAll('[type="date"]');

            dateInputs.forEach(el => {
                // register double click event to change date input to text input and select the value
                el.addEventListener('dblclick', () => {
                    el.type = "text";
                    el.select();
                });

                // register the focusout event to reset the input back to a date input field
                el.addEventListener('focusout', () => {
                    el.type = "date";
                });
            });

        },


        methods: {

            emitChange(v){
                if(v){
                    this.$emit('change', v)
                }
                


            },


            updateValue(val) {
                // remove free input value in cases of multiple value component and single value component
                if (this.multiple) {

                    this.$emit('input', val.filter(x => x.id))
                } else {


                    if (val && !val.hasOwnProperty('id')) {
                        this.$refs.fld.reset();

                    } else {

                        this.$emit('input', val)
                    }
                }


            },
            search:
                debounce(function (evt) {
                    const qp = this.queryParams || '';
                    axios
                        .get(`${this.api}?q=${evt.target.value}${qp}&per_page=100`)
                        .then(response => {
                            this.items = response.data.items;
                        });
                }, 350)
            ,

        },
        template: `
            <v-combobox
                    :disabled="disabled"
                    menu-props="auto"
                    auto-select-first
                    v-bind:value="value"
                    @input="updateValue"
                    ref="fld"
                    hide-no-data
                    no-filter
                    item-color="secondary"
                    :label="label"
                    :items="items"
                    :item-text="itemText"
                    :item-value="itemValue"
                    prepend-inner-icon="mdi-magnify"
                    :multiple="multiple"
                    small-chips
                    :deletable-chips="true"
                    clearable
                    @input.native="search"
                    @focus="search"
                    return-object
                    :search-input.sync="searchInput"
                    @change="emitChange"

                    :loading="loading"

            ></v-combobox>
        `
    })