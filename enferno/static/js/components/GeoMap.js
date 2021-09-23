Vue.component("geo-map", {
    props: {
        title: String,
        value: {

        },

        mapHeight: {
            default: 300
        },
        mapZoom: {
            default: 10
        },


    },
    data: function () {

        return {
            lat: (this.value && this.value.lat) || geoMapDefaultCenter.lat,
            lng: (this.value && this.value.lng) || geoMapDefaultCenter.lng
            ,
            location: null


        }
    },


    watch: {

        value(val){


            if (val && val.lat && val.lng){

                this.lat = val.lat;
                this.lng = val.lng;

            }

        },


        lat: {
            handler: 'broadcast',

        },
        lng: {
            handler: 'broadcast'
        }


    },

    mounted(){
         setTimeout(()=>{
            this.$refs.map.mapObject.invalidateSize();

        },500)
        this.broadcast();
    },


    methods: {
        setMarker(evt){
            this.lat = evt.latlng.lat;
            this.lng = evt.latlng.lng;

        },


         updateLocation(point){
             this.lat = point.lat;
             this.lng = point.lng;


      },
        broadcast() {

            this.$emit('input',{lat:this.lat, lng: this.lng});

        }
    },
    template:
            `
      <v-card class="pa-2" elevation="0">
      
      <v-card-text>
        <h3 class=" mb-5">{{ title }}</h3>
        <div class="d-flex" style="column-gap: 20px;">
          <v-text-field dense   type="number" min="-90" max="90" label="Latitude" v-model="lat"></v-text-field>
          <v-text-field  dense   type="number" min="-180" max="180" label="Longitude" v-model="lng"></v-text-field>
        </div>
      
     
        <l-map @click="setMarker"  class="mt-4" ref="map" v-if="lat && lng" :zoom="mapZoom" :style="'border-radius: 8px;resize: vertical;height:'+ mapHeight + 'px'" :center="[lat,lng]">
          <l-tile-layer :url="mapsApiEndpoint"></l-tile-layer>
          <l-marker @update:latLng="updateLocation" :lat-lng="[lat,lng]" draggable="true"></l-marker>
        </l-map>

      </v-card-text>

      </v-card>

    `,
});
