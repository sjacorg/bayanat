Vue.component('search-field-single',
    {
        props: ['value', 'label', 'itemText', 'itemValue', 'api','queryParams', 'returnObject','disabled'],
        data: () => {
            return {
                loading: false,
                items: [],
                model: ''
            }
        },
        watch : {
            value : function(val){
                this.model = val;

            }
        },

        methods: {
            updateValue(){

            this.value = this.model;
            this.$emit('input',this.value)
            },
            search:
                debounce(function (evt) {
                    const qp = this.queryParams || '';
                    axios
                        .get(`${this.api}?q=${evt.target.value}${qp}`)
                        .then(response => {
                            this.items = response.data.items;
                        });
                }, 350)
            ,

        },
        template: `
            <v-autocomplete
                    v-bind:value="value"
                    @input="updateValue"
                    hide-no-data
                    no-filter
                    item-color="secondary"
                    :label="label"
                    v-model="model"
                    :items="items"
                    :item-text="itemText"
                    :item-value="itemValue"
                    prepend-inner-icon="mdi-magnify"
                    :disabled="disabled"
                    
                    small-chips
                    clearable
                    @input.native="search"
                    @focus="search"
                    :return-object="returnObject"
                    :loading="loading"
            ></v-autocomplete>
        `
    })