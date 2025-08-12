const UserCard = Vue.defineComponent({
  props: ['user', 'closable'],
  emits: ['close', 'edit', 'resetPassword', 'revoke2fa', 'logoutAll'],
  watch: {
    user: function (val, old) {
      this.resetSessions();
      this.fetchSessions();
    },
  },
  computed: {
    permissions() {
      return [
        {
          value: this.user.view_usernames,
          label: this.user.view_usernames ? this.translations.canViewUsernames_ : this.translations.cannotViewUsernames_
        },
        {
          value: this.user.view_simple_history,
          label: this.user.view_simple_history ? this.translations.canViewSimpleHistory_ : this.translations.cannotViewSimpleHistory_
        },
        {
          value: this.user.view_full_history,
          label: this.user.view_full_history ? this.translations.canViewFullHistory_ : this.translations.cannotViewFullHistory_
        },
        {
          value: this.user.can_edit_locations,
          label: this.user.can_edit_locations ? this.translations.canEditLocations_ : this.translations.cannotEditLocations_
        },
        {
          value: this.user.can_export,
          label: this.user.can_export ? this.translations.canExport_ : this.translations.cannotExport_
        },
        {
          value: this.user.can_self_assign,
          label: this.user.can_self_assign ? this.translations.canSelfAssign_ : this.translations.cannotSelfAssign_
        }
      ];
    }
  },
  mounted() {
    this.fetchSessions();
  },

  methods: {
    resetSessions() {
      this.sessions = [];
      this.page = 1;
      this.more = true;
    },

    fetchSessions(page = this.page, perPage = this.perPage) {
      if (!this.more) return;

      axios
        .get(`/admin/api/user/${this.user.id}/sessions`, {
          params: {
            page: page,
            per_page: perPage,
          },
        })
        .then((response) => {
          if (response.data.items.length) {
            this.sessions = this.sessions.concat(response.data.items);
            this.page++;
            this.more = response.data.more;
          } else {
            this.more = false;
          }
        })
        .catch((err) => {
          if (err.response && err.response.status === 401) {
            alert(this.translations.loggedOut_);
            window.location.href = '/login'; // Redirect to login page
          } else {
            console.error('Error fetching sessions', err);
          }
        });
    },

    logoutSession(id) {
      if (window.confirm(this.translations.logoutSessionConfirmation_)) {
        axios
          .delete('/admin/api/session/logout', {
            data: {
              sessid: id,
            },
          })
          .then((response) => {
            console.log('Logged out session');
            if (response.data.redirect) {
              // Perform the redirection to the root path
              window.location.href = '/';
            } else {
              this.resetSessions();
              this.fetchSessions();
            }
          })
          .catch((err) => {
            console.error('Error logging out session', err);
          });
      }
    },
  },

  data: function () {
    return {
      translations: window.translations,
      show: false,
      sessions: [],
      page: 1,
      perPage: 5,
      more: true,
    };
  },

  template: `
      <v-card class="mx-auto">
        <v-sheet class="px-6 py-4 d-flex align-center">
          <v-toolbar-title>
            <div class="d-flex flex-wrap ga-2 align-center">
              {{ user.name }}
  
              <v-chip prepend-icon="mdi-identifier" color="primary">
                {{ user.id }}
              </v-chip>
  
              <v-chip prepend-icon="mdi-account-circle-outline" color="primary">
                {{ user.username }}
              </v-chip>
  
              <v-chip v-if="user.email" prepend-icon="mdi-email" color="primary">
                {{ user.email }}
              </v-chip>
  
              <v-btn
                variant="tonal"
                size="small"
                prepend-icon="mdi-pencil"
                @click="$emit('edit', user)"
              >
                {{ translations.edit_ }}
              </v-btn>
  
              <v-tooltip
                location="bottom"
                :disabled="!user.force_reset"
                :text="translations.passwordResetAlreadyRequested_"
              >
                <template #activator="{props}">
                  <div v-bind="props">
                    <v-btn
                      :disabled="user.force_reset != null"
                      variant="tonal"
                      size="small"
                      prepend-icon="mdi-lock-reset"
                      @click="$emit('resetPassword', user)"
                    >
                      {{ translations.forcePasswordReset_ }}
                    </v-btn>
                  </div>
                </template>
              </v-tooltip>
              
              <v-chip
                v-if="user.force_reset"
                color="error"
                variant="tonal"
                label
                prepend-icon="mdi-exclamation"
              >
                {{ translations.passwordResetRequested_ }}
              </v-chip>
            </div>
          </v-toolbar-title>

          <v-btn v-if="closable" size="small" variant="flat" icon="mdi-close" @click="$emit('close')"></v-btn>
        </v-sheet>
        <v-divider></v-divider>


        <v-card variant="flat" class="mt-3 pa-3">

          <v-label class="ml-3">
            {{ translations.userPermissions_ }}
          </v-label>
          <v-card-text>

            <v-chip
              v-for="(permission, index) in permissions"
              :key="index"
              class="ma-2"
              :color="permission.value ? 'primary' : 'error'"
              :prepend-icon="permission.value ? 'mdi-checkbox-marked-circle' : 'mdi-close-circle'">
              {{ permission.label }}
            </v-chip>
          </v-card-text>
        </v-card>

        <v-divider></v-divider>
        
         <v-card variant="flat" class="mt-3 pa-3">

          <div class="d-flex align-center">
            <v-label class="ml-3">
              {{ translations.userTwoFactorMethods_ }}
            </v-label>

            <v-btn
              v-if="user.two_factor_devices && user.two_factor_devices.length > 0"
              @click.stop="$emit('revoke2fa', user.id)"
              variant="tonal"
              color="warning"
              size="small"
              prepend-icon="mdi-lock-remove"
              class="ml-2"
            >
              {{ translations.revoke2fa_ }}
            </v-btn>
          </div>

          <v-card-text class="d-flex ga-3">

            <v-chip
              v-for="device in user.two_factor_devices"
              :key="device.id"
              :prepend-icon="device.type === 'authenticator' ? 'mdi-lock-clock' : 'mdi-usb-flash-drive'"
              color="primary"
            >
              {{ device.name }}
            </v-chip>

            <v-chip
              v-if="user.two_factor_devices.length == 0"
              prepend-icon="mdi-lock-open-alert"
              color="error"
              label
            >
              {{ translations.noTwoFactorMethods_ }}
            </v-chip>


          </v-card-text>
        </v-card>

        <v-divider></v-divider>

        <v-card class="mt-2" variant="flat">

          <v-card-text>
            <div class="d-flex align-center">
              <v-label class="ml-3">{{ translations.userSessions_ }}</v-label>
              <v-btn
                @click.stop="$emit('logoutAll', user.id)"
                variant="tonal"
                size="small"
                prepend-icon="mdi-logout"
                color="error"
                class="ml-2"
              >
                {{ translations.logoutAllSessions_ }}
              </v-btn>
            </div>

            <v-table fluid>
              <thead>
              <tr>
                <th class="text-left">{{ translations.session_ }}</th>
                <th class="text-left">{{ translations.ip_ }}</th>
                <th class="text-left">{{ translations.userAgent_ }}</th>
                <th class="text-left">{{ translations.started_ }}</th>
                <th class="text-left">{{ translations.logOffThisDevice_ }}</th>
              </tr>
              </thead>
              <tbody>
              <tr v-for="session in sessions"
                  
                  :class="session.active ? 'bg-yellow-lighten-5':'' ">
                <td>
                  
                  <v-tooltip v-if="session.details?._fresh">
                    <template #activator="{ props }">
                      <v-icon v-bind="props" color="green">
                        mdi-circle
                      </v-icon>
                    </template>
                    {{ translations.active_ }}
                  </v-tooltip>

                  <v-tooltip v-else>
                    <template #activator="{ props }">
                      <v-icon color="grey-darken-5" v-bind="props">mdi-circle</v-icon>
                    </template>
                    {{ translations.inactive_ }}
                  </v-tooltip>


                </td>
                <td>
                  <v-chip label>{{ session.ip_address }}</v-chip>
                </td>
                <td class="text-caption">
                  {{ session.meta.device }}
                </td>
                <td class="text-caption">{{ $root.formatDate(session.created_at, { local: true }) }}</td>
                <td>
                  <v-btn icon="mdi-logout" variant="plain" v-if="session.details?._fresh"
                         @click.once="logoutSession(session.id)" :disabled="!session.is_active"
                         color="error">

                  </v-btn>
                </td>
              </tr>
              </tbody>
            </v-table>
          </v-card-text>
          <v-card-text class="text-center">
            <v-btn icon="mdi-dots-horizontal" variant="plain" v-if="more" fab small @click="fetchSessions(page, perPage)"></v-btn>
          </v-card-text>
        </v-card>
      </v-card>
    `,
});
