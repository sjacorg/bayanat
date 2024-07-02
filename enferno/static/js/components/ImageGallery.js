const ImageGallery = Vue.defineComponent({
  props: {
    medias: Array,
    enableDelete: Boolean
  },
  emits: ['remove-media', 'thumb-click', 'video-click'],
  mounted() {
    this.prepareImagesForPhotoswipe().then(() => {
      this.initLightbox();
    });
  },

  methods: {
    handleVideo(s3url){
      this.$emit('video-click', s3url)
    },
    handleThumb(s3url){
      this.$emit('thumb-click', s3url)
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
    <div>
      <div class="d-flex flex-wrap" id="lightbox">
        
        <v-slide-group show-arrows>
            <v-slide-group-item v-for="(media,index) in medias" :key="media.id">
              <v-card width="250" height="300" class="mx-3" variant="flat"> 
                
              
          <media-card @ready="updateMediaState" @thumb-click="handleThumb" @video-click="handleVideo" :media="media">
            
              <template v-slot:actions v-if="enableDelete">
              <v-spacer></v-spacer>
              <v-btn size="small" variant="text" icon="mdi-delete-sweep" v-if="!media.main" @click="$emit('remove-media', index)"  color="red">
                
              </v-btn>
            </template>

            
          </media-card>
                </v-card>
            </v-slide-group-item>
        </v-slide-group>
        
      </div>
    </div>
  `,
});