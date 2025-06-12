const ImageGallery = Vue.defineComponent({
  props: {
    medias: Array,
    enableDelete: Boolean,
    prioritizeVideos: Boolean
  },
  emits: ['remove-media', 'thumb-click', 'video-click', 'audio-click', 'expand-media'],
  mounted() {
    this.prepareImagesForPhotoswipe().then(() => {
      this.initLightbox();
    });
  },
  computed: {
    sortedMedia() {
      if (this.prioritizeVideos) return this.sortMediaByFileType(this.medias);

      return this.medias;
    }
  },
  methods: {
    handleVideo(media){
      this.$emit('video-click', media)
    },
    sortMediaByFileType(mediaList) {
      if (!mediaList) return [];
      // Sort media list by fileType (video first)
      const sortedMediaList = mediaList.sort((a, b) => {
        if (a?.fileType?.includes('video')) return -1; // Video should come first
        if (b?.fileType?.includes('video')) return 1; // Then images
        return 0; // Leave unchanged if neither is a video
      });

      return sortedMediaList;
    },
    handleAudio(media){
      this.$emit('audio-click', media)
    },

    updateMediaState() {
       this.mediasReady += 1;
      if (this.mediasReady === this.medias.length && this.mediasReady > 0) {
        this.prepareImagesForPhotoswipe().then((res) => {
          this.initLightbox();
        });
      }
    },

    prepareImagesForPhotoswipe() {
       // Get the <a> tags from the image gallery
      const imagesList = document.querySelectorAll('#lightbox a');
      const promisesList = [];

      imagesList.forEach((element) => {
        const promise = new Promise(function (resolve) {
          let image = new Image();
          image.src = element.getAttribute('href');
          image.onload = () => {
            element.dataset.pswpWidth = image.width;
            element.dataset.pswpHeight = image.height;
            resolve(); // Resolve the promise only if the image has been loaded
          };
          image.onerror = () => {
            resolve();
          };
        });
        promisesList.push(promise);
      });

      // Use .then() to handle the promise resolution
      return Promise.all(promisesList);
    },

    initLightbox() {
      this.lightbox = new PhotoSwipeLightbox({
        gallery: '#lightbox',
        children: 'a',
        pswpModule: PhotoSwipe,
        wheelToZoom: true,
        arrowKeys: true,
      });

      this.lightbox.init();
    },
  },

  data: function () {
    return {
      lightbox: null,
      mediasReady: 0,
    };
  },

  template: `
    
      <div id="lightbox">
        
        <v-sheet class="media-grid">
            
                
              <v-sheet  v-for="(media,index) in sortedMedia" :key="media.id">
                <media-card @ready="updateMediaState" @video-click="handleVideo" @audio-click="handleAudio" :media="media">
                  <template v-slot:top-actions="{ media, mediaType }">
                    <slot name="top-actions" :media="media" :mediaType="mediaType"></slot>
                  </template>
                  <template v-slot:actions v-if="enableDelete">
                    <v-divider></v-divider>
                    <v-card-actions class="justify-end d-flex">
                      <v-btn size="small" variant="text" icon="mdi-delete-sweep" v-if="!media.main" @click="$emit('remove-media', index)"  color="red"></v-btn>    
                    </v-card-actions>
                  </template>
           
                </media-card>
              </v-sheet>
            
        </v-sheet>
        
      </div>
    
  `,
});