const whisperMixin = {
  data: () => ({
    whisperLanguageCodes: null
  }),
  mounted() {
    api.get('/import/api/whisper/languages').then(response => {
      this.whisperLanguageCodes = response.data.languages;
    }).catch(error => {
      console.error(error);
    });
  },
  computed: {
    whisperLanguageOptions() {
      const languages = Object.keys(this.whisperLanguageCodes).map(lang => ({
        title: lang.charAt(0).toUpperCase() + lang.slice(1),
        value: this.whisperLanguageCodes[lang]
      }));
      languages.unshift({title: 'Auto-detect', value: null});
      return languages;
    }
  }
};
