const TinymceEditor = Vue.defineComponent({
  async beforeCreate() {
    // Load TinyMCE dependencies if not already loaded
    if (typeof tinymce === 'undefined') {
      await loadAsset('/static/js/tinymce/js/tinymce/tinymce.min.js');
    }
    if (typeof Editor === 'undefined') {
      const Editor = await loadComponent('/static/js/tinymce-vue.min.js');
      console.log(Editor)

      window.app.component('Editor', Editor)
    }
  },
  
  template: `<Editor v-bind="$props" />`,
});

window.TinymceEditor = TinymceEditor;