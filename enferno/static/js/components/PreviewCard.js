const PreviewCard = Vue.defineComponent({
  props: ['item', 'modelValue', 'dialogProps'],
  watch: {
    modelValue(val) {
      this.preview = val;
    },
    preview(val) {
      this.$emit('update:modelValue', val);
    },
  },
  data: function () {
    return {
      translations: window.translations,
      preview: this.modelValue || false,
    };
  },
  template: `
    <v-dialog v-model="preview" v-bind="dialogProps || { 'max-width': '900px' }">
      <v-card>
        <v-toolbar color="dark-primary">
          <v-toolbar-title>{{ translations.preview_ }}</v-toolbar-title>
          <v-spacer></v-spacer>

          <template #append>
            <v-btn icon="mdi-close" @click="$root.preview = false"></v-btn>
          </template>
        </v-toolbar>
        
        <v-card-text class="overflow-y-auto">
          <bulletin-card v-if="item && item.class === 'bulletin'" :close="false" :bulletin="item"></bulletin-card>
          <actor-card v-if="item && item.class === 'actor'" :close="false" :actor="item"></actor-card>
          <incident-card v-if="item && item.class === 'incident'" :close="false" :incident="item"></incident-card>
        </v-card-text>        
      </v-card>
    </v-dialog>
  `,
});
window.PreviewCard = PreviewCard;
