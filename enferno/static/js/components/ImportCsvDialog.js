const ImportCsvDialog = Vue.defineComponent({
    props: {
        endpoint: {
            type: String,
            required: true
        }
    },
    emits: ['import'],
    data: () => {
      return {
        validationRules: validationRules,
        translations: window.translations,
        dialog: false,
        csvFile: null,
      };
    },
    methods: {
        importCSV() {
            const reqData = new FormData();
            reqData.append('csv', this.csvFile)
            api.post(this.endpoint, reqData).then(response => {
                this.$emit('import')
                this.$root.showSnack(response.data);
                this.close();
            })
        },
        validateImportCSV() {
            this.$refs.csvForm.validate().then(({ valid }) => {
                if (valid) {
                    this.importCSV();
                } else {
                    this.$root.showSnack(this.translations.pleaseReviewFormForErrors_)
                    scrollToFirstError()
                }
            });
        },
        close() {
            this.dialog = false;
            this.csvFile = null;
        }
    },
    template: `
        <v-dialog v-model="dialog" width="500" @after-leave="close()">
            <template v-slot:activator="{ props }">
                <v-btn
                        color="secondary"
                        variant="elevated"
                        class="ma-2"
                        v-bind="props">
                    {{ translations.importCsv_ }}
                </v-btn>
            </template>

            <v-form ref="csvForm" @submit.prevent="validateImportCSV">
                <v-card>
                    <v-card-title>
                        <span class="headline">{{ translations.importCsv_ }}</span>
                    </v-card-title>

                    <v-card-text>
                        <v-file-input v-model="csvFile" show-size accept=".csv" :rules="[validationRules.required()]">
                            <template v-slot:label>{{ translations.selectCsvFile_ }} <Asterisk /></template>
                        </v-file-input>
                    </v-card-text>

                    <v-card-actions>
                        <v-spacer></v-spacer>
                        <v-btn @click="close()">{{ translations.cancel_ }}</v-btn>
                        <v-btn color="primary" variant="flat" type="submit">{{ translations.save_ }}</v-btn>
                    </v-card-actions>
                </v-card>
            </v-form>
        </v-dialog>
      `,
  });
  