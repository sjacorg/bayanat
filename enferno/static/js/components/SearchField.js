const SearchField =
    {
        props: ['value', 'label', 'multiple', 'itemText', 'itemValue', 'api', 'queryParams', 'disabled'],
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

            emitChange(v) {
                if (v) {
                    this.$emit('change', v);
                    this.searchInput = ''
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
            search: debounce(function () {
                this.loading = true;
                axios.get(this.api, {
                    params: {
                        q: this.searchInput,
                        ...this.queryParams,
                        per_page: 100
                    }
                })
                    .then(response => {
                        this.items = response.data.items;
                    })
                    .catch(error => {
                        console.error("Error fetching data:", error);
                    })
                    .finally(() => {
                        this.loading = false;
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
                    @click:clear="search"
                    :search-input.sync="searchInput"
                    @change="emitChange"
                    v-bind="$attrs"
                    :loading="loading"

            ></v-combobox>
        `
    };

Vue.component('search-field', SearchField);

const LocationSearchField = Vue.extend({
    extends: SearchField,
    methods: {
        search: debounce(function (evt) {
            axios.post(this.api, {
                q: {
                    ...this.queryParams,
                    'title': evt.target.value
                },
                options: {},
            }).then(response => {
                this.items = response.data.items;
            });
        }, 350)
    }
});

Vue.component('location-search-field', LocationSearchField);
