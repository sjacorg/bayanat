const SnapshotDialog = Vue.defineComponent({
    props: ['dialogProps', 'modelValue'],
    emits: ['update:modelValue', 'attachSnapshot'],
    data: () => ({
        translations: window.translations,
        form: {
          title: null,
          title_ar: null,
          category: null,
        }
    }),
    watch: {
      modelValue: {
        immediate: true,
        handler(isOpen) {
          if (isOpen) {
            // Initialize the form when the dialog opens
            this.form.title = null;
            this.form.title_ar = null;
            this.form.category = null;
          }
        }
      }
    },
    template: /*html*/ `
      <v-dialog
          :model-value="modelValue"
          @update:model-value="$emit('update:modelValue', $event)"
          v-bind="dialogProps"
      >
        <v-toolbar color="dark-primary">
          <v-toolbar-title>Snapshot</v-toolbar-title>
          <v-spacer></v-spacer>
  
          <template #append>
            <v-btn @click="$root.attachSnapshot(form)" variant="elevated" class="mx-2">
                Attach snapshot
            </v-btn>
            <v-btn @click="$emit('update:modelValue', false)" icon="mdi-close"></v-btn>
          </template>
        </v-toolbar>

        <v-card>
          <v-card-text>
            <!-- Snapshot preview w/ crop support -->
            <div class="crop mb-4">
              <img id="cropImg" />
            </div>

            <dual-field
              v-model:original="form.title"
              v-model:translation="form.title_ar"
              :label-original="translations.title_"
              :label-translation="translations.titleAr_"
            ></dual-field>
          
              <!-- category -->
              <search-field
                api="/admin/api/mediacategories"
                v-model="form.category"
                :label="translations.mediaCategory_"
                item-title="title"
                item-value="id"
              ></search-field>
          </v-card-text>
        </v-card>
      </v-dialog>
      `,
  });
  