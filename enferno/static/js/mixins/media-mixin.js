// fix issue with vuetify combobox (remvoe ability to create new items that don't exist in the list)

let mediaMixin = {

  data:  {

    mediaDialog: false,

    // search and relate media dialog vars
    relateMediaLoader: true,
    relateMediaTerm: "",
    relateMediaResults: [],
    selectedRelatedMedia: [],
    relateMediaDialog: false,

    medias: [],
    mediaCats: mediaCats,


    //media edit / create item
    editedMediaIndex: -1,
    editedMedia: {
      title: ""
    },

    defaultMedia: {
      title: "",
      files: [],
      category: "Generic"
    },

    mediaTitle__: true,

    //disable btn initially, enable after upload is successful
    upMediaBtnDisabled: true,
    videoDialog: false,
      playerOptions: {},
      videoMeta: {},
      screenshots: [],
      //hold different cropper attributes
      cropper: {
        canvas: null,
        tool:null,
        active: false
      },

  },

    methods: {



       viewImage(item) {

        viewer.show(item);
      },

      crop() {
         if(this.cropper.active){
            document.querySelector('.croppr-container').remove();
            this.cropper.active = false;
            return
         };

        let video = this.$el.querySelector('#player video');

        this.cropper.canvas = document.createElement('canvas');
        this.cropper.canvas.width = this.videoMeta.width;
        this.cropper.canvas.height = this.videoMeta.height;
        let context = this.cropper.canvas.getContext('2d');
        context.fillRect(0, 0, this.cropper.canvas.width, this.cropper.canvas.height);
        context.drawImage(video, 0, 0, this.cropper.canvas.width, this.cropper.canvas.height);
        let img = document.querySelector('#cropImg')
        if (!img){
          img = new Image();
          img.id = 'cropImg';

          this.$el.querySelector('.crop').prepend(img)
        }
        img.src = this.cropper.canvas.toDataURL('image/jpeg');
        this.cropper.tool = new Croppr(img);
        this.cropper.active = true;


      },

      attachCrop(){


        let crop = this.cropper.tool.getValue();
        let img = this.$el.querySelector('.croppr-image');

        let id = this.screenshots.length;
        let video = this.$el.querySelector('#player video');
        let wr = this.videoMeta.width/img.width;
        let hr = this.videoMeta.height/img.height;

        let media = {
          width : crop.width,
          height: crop.height,
          time: Math.round(video.currentTime*10)/10,
          fileType: 'image/jpeg',
          filename: video.src.getFilename(),
          ready: false,
          overlay: false,
          sw: true
        };


        this.screenshots.push(media);
        // wait until data binding is in effect
        this.$nextTick(() => {
        let canvas = this.$el.querySelector('.canvas'+id);
        canvas.width = media.width;
        canvas.height = media.height;
        // calculate ration based on widht/height

        let context = canvas.getContext('2d');
        context.fillRect(0, 0, media.width, media.height);
        context.drawImage(img, crop.x, crop.y, media.width, media.height,0,0, media.width, media.height);

        //clear source image

        this.$el.querySelector('.croppr-container').remove();
        this.cropper.active = false;

      });
    }

      ,


      snapshot (){
        let id = this.screenshots.length;
        let video = this.$el.querySelector('#player video');
        video.pause()

        let media = {

          width : this.videoMeta.width,
          height: this.videoMeta.height,
          time: Math.round(video.currentTime*10)/10,
          fileType: 'image/jpeg',
          filename: video.src.getFilename(),
          ready: false,
          overlay: false,
          sw: true
        };

        this.screenshots.push(media);
        // wait until data binding is in effect
        this.$nextTick(() => {

        let canvas = this.$el.querySelector('.canvas'+id);

        canvas.width = media.width;
        canvas.height = media.height;
        let context = canvas.getContext('2d');
        context.fillRect(0, 0, media.width, media.height);
        context.drawImage(video, 0, 0, media.width, media.height);



      });



      },
      removeSnapshot(e,index) {


        //this.screenshots.splice(index,1);
        this.screenshots[index].deleted = true;
        // force Vue to re-render the UI
        this.$forceUpdate();

      }
    ,

      uploadSnapshot(e,index){
        let media = this.screenshots[index];
          media.overlay = true;
          let canvas = this.$el.querySelector('#screenshots .canvas'+index);
          let dataUrl = canvas.toDataURL("image/jpeg");
          let blob = dataUriToBlob(dataUrl);
          let data = new FormData();
          data.append('media',blob,media.filename)

           axios.post("/admin/api/media/upload/", data,{
            headers: { "content-type": false }
           }).then(response => {
             const serverId = response.data;
              //this.showSnack(response.data);
              media.filename = serverId.filename;
              media.etag = serverId.etag;
              media.overlay = false;
              media.ready = true;

              //this.refresh(this.options);
            });



      },

      attachSnapshots(){

         // get screenshots excluding deleted onces
        let final = this.screenshots.filter(x=> !x.deleted);

        for (const scr of final){
          //check uploaded ones
          if (scr.ready) {

            let item = {};
            item.title = scr.title;
            item.title_ar = scr.title_ar;
            item.fileType = scr.fileType;
            item.filename = scr.filename;
            item.etag = scr.etag;
            item.time = scr.time;
            this.editedItem.medias.push(item);

          }
        }

        this.closeVideo();
      }

      ,


      viewPlayer(s3url) {

        //open video player
        this.videoDialog = true;
        this.screenshots = [];
        this.$nextTick(()=>{
          let pp = document.querySelector('#pp');

          //cleanup pip or existing video
          let ep = pp.querySelector('#player');
          if (ep) {
            videojs(ep).dispose();
          };

          pp.insertAdjacentHTML('afterbegin','<video id="player" controls class="video-js vjs-default-skin vjs-big-play-centered" crossorigin="anonymous" width="620" height="360" preload="auto" ></video>')
          let video = this.$el.querySelector('video');

          videojs(video,{
            playbackRates: VIDEO_RATES
          },function(){
            this.src(s3url);

          });
          video.addEventListener('loadedmetadata',  ()=> {
            this.videoMeta.filename = video.src.getFilename() + '.jpg';
            this.videoMeta.time = video.currentTime;
            this.videoMeta.width = video.videoWidth;
            this.videoMeta.height = video.videoHeight;
          });

        });







      },

      closeVideo() {
        //dispose player
        let player = this.$el.querySelector('#player video');
        //videojs(player).dispose();
        player.pause();



        this.videoDialog = false;
      },




       addMedia(media, item, index) {
        this.editedMedia = Object.assign({}, this.defaultMedia);
        //console.log(this.editedEvent);
        //enable below to activate edit mode
        //this.editedMediaIndex = index;

        //reset dual fields display to english
        this.mediaTitle__ = true;

        this.mediaDialog = true;
        //this.locations = this.editedItem.locations;
      },

      removeMedia: function(evt, index) {
        if (confirm("Are you sure?")) {
          this.editedItem.medias.splice(index, 1);
        }
      },

      closeMedia() {
        this.editedMedia.files = [];
        this.mediaDialog = false;
        setTimeout(() => {
          this.editedMedia = Object.assign({}, this.defaultMedia);

          this.editedMediaIndex = -1;
        }, 300);
      },

      attachFilepondMedia() {

        if (this.editedMediaIndex > -1) {
          //unused : editing existing media item
          Object.assign(
            this.editedItem.medias[this.editedMediaIndex],
            this.editedMedia
          );
        } else {
          //console.log(this.editedItem);
          //push files from editedMedia to to edited item medias
          for (const file of this.editedMedia.files) {
            let item = {};
            const serverId = JSON.parse(file.serverId);
            item.title = this.editedMedia.title;
            item.fileType = file.fileType;
            item.filename = serverId.filename;
            item.etag = serverId.etag;
            this.editedItem.medias.push(item);
          }
        }
        this.closeMedia();
      },

      onFileUploaded(error, file) {
          if (!error){
            this.upMediaBtnDisabled = false;
          }


      },

      searchRelatedMedia() {
        // reset all selected media
        this.selectedRelatedMedia = [];

        this.relateMediaDialog = true;
        let searchTerm = this.relateMediaTerm || "";

        axios.get(`/admin/api/medias/?q=${searchTerm}`).then(response => {
          let results = response.data.items;
          // filter already existing items
          for (const item of this.editedItem.medias) {
            results.removeById(item.id);
          }

          this.relateMediaResults = results;
          this.relateMediaLoader = false;
        });
      },

      relateMedia(evt, media) {
        // get list of existing attached medias
        let e = this.editedItem.medias.map(x => x.id);

        if (!e.includes(media.id)) {
          this.editedItem.medias.push(media);
          this.relateMediaResults.removeById(media.id);
        }
      }



    }
  }
  