Vue.component('image-gallery', {
  props: {
    medias: Array,
    enableDelete: Boolean
  },

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
      if (this.mediasReady == this.medias.length && this.mediasReady > 0) {
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
        <div class="pa-1" style="width: 50%" v-for="(media,index) in medias" :key="media.id">
          <media-card @ready="updateMediaState" @thumb-click="handleThumb" @video-click="handleVideo" :media="media">
            
              <template v-slot:actions v-if="enableDelete">
              <v-spacer></v-spacer>
              <v-btn v-if="!media.main" @click="$emit('remove-media', index)" x-small depressed fab outlined color="red lighten-1">
                <v-icon>mdi-delete-sweep</v-icon>
              </v-btn>
            </template>

            
          </media-card>
        </div>
      </div>
    </div>
  `,
});