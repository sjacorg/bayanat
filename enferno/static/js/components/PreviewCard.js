const PreviewCard = Vue.defineComponent({
  props: ['item', 'modelValue'],
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
      preview: this.modelValue || false,
    };
  },
  template: `
    <v-dialog max-width="900"  v-model="preview">
      <v-sheet v-if="preview" class="mt-2" >
        <v-toolbar class="header-fixed">
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" @click.stop.prevent="$root.preview = false" x-small right top="10" fab>
          </v-btn>
        </v-toolbar>
        

        <bulletin-card v-if="item && item.class === 'bulletin'" :close="false" :bulletin="item"></bulletin-card>
        <actor-card v-if="item && item.class === 'actor'" :close="false" :actor="item"></actor-card>
        <incident-card v-if="item && item.class === 'incident'" :close="false" :incident="item"></incident-card>
      </v-sheet>
    </v-dialog>
  `,
});