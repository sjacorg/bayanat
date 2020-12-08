Vue.component("media-card", {
  props: {
      media: {}, 
  },
  data: function() {
    return {
      s3url : '', 
    };
  },
  mounted(){
    this.init()
  },



  methods: {
    init (){
      axios.get(`/admin/api/media/${this.media.filename}`).then(response => {
      console.log('media path set', response.data)
        this.s3url = response.data;
        this.media.s3url = response.data;

  });
    },

    
   
    mediaType(mediaItem) {
      if (['image/jpeg','image/png','image/gif'].includes(mediaItem.fileType)) {
        return 'image'
      }
      else if (['video/webm','video/mp4'].includes(mediaItem.fileType)){
      return 'video'
      }
      else {
        return 'unknown'
      }
    },
  },
  template: `

  
     <!--  Image Media Card -->
     <v-card :disabled="!s3url" class="media-card" v-if="mediaType(media) == 'image'">
      <v-img
        
        @click="$emit('thumb-click', s3url)"
        class="white--text align-end media-img"
        height="100px"
        :src="s3url"
        
      >
      <template v-slot:placeholder>
        <v-row
          class="fill-height ma-0"
          align-center justify-center
          
        >
          <v-progress-circular indeterminate color="grey lighten-5"></v-progress-circular>
        </v-row>
      </template>
      </v-img>

      <div class="caption pa-1">
        {{media.title || '&nbsp;'}}  <span v-if="media.time">({{ media.time}})</span>
      </div> 
       <v-chip x-small label class="caption pa-1 " color="yellow lighten-5 grey--text" >
        {{media.etag}} 
       </v-chip>
      <v-card-text class="pa-2 d-flex"> 
        <slot name="actions"></slot>
      </v-card-text>
      
      
    </v-card>
    
    <!-- Video Media Card  -->
    <v-card :disabled="!s3url"   class="media-card" v-else-if="mediaType(media) == 'video'">
      <v-avatar
        tile
        class="black media-vid"
        width="100%"
        height="140px"
        @click="$emit('video-click',s3url)"
      >
        <v-icon size="52" color="#666">mdi-play-circle-outline</v-icon>
      </v-avatar>
      <div class="caption pa-2">
        {{media.title}}  
      </div>
      
      <v-chip x-small label class="caption pa-1 " color="yellow lighten-5 grey--text" >
        {{media.etag}}
      </v-chip>
      <v-card-text class="pa-2 d-flex"> 
        <slot name="actions"></slot>
      </v-card-text>
    </v-card>



  


    
    
        


    `
});
