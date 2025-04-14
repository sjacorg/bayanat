const whisperMixin = {
  data: () => ({
    whisperLanguageCodes: null
  }),
  mounted() {
    if(!window.__TRANSCRIPTION_ENABLED__) {
      return;
    }
    axios.get('/import/api/whisper/languages').then(response => {
      this.whisperLanguageCodes = response.data.languages;
    }).catch(error => {
      console.error(error);
    });
  },
  computed: {
    whisperLanguageOptions() {
      if(!this.whisperLanguageCodes) {
        return [];
      }
      const languages = Object.keys(this.whisperLanguageCodes).map(lang => ({
        title: lang.charAt(0).toUpperCase() + lang.slice(1),
        value: this.whisperLanguageCodes[lang]
      }));
      languages.unshift({title: 'Auto-detect', value: null});
      return languages;
    }
  }
};
