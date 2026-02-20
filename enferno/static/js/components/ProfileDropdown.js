const ProfileDropdown = Vue.defineComponent({
  props: {
    email: {
      type: String,
      default: ''
    },
    username: {
      type: String,
      default: ''
    },
    name: {
      type: String,
      default: ''
    }
  },
  data: () => {
    return {
      translations: window.translations,
    };
  },
  computed: {
    userInitials() {
      const safeName = (this.name || '').trim()
      const safeEmail = (this.email || '').trim()
      const safeUsername = (this.username || '').trim()

      // 1) Name-based initials
      if (safeName) {
        return safeName
          .split(/\s+/)
          .filter(Boolean)
          .map(p => p[0])
          .join('')
          .toUpperCase()
          .substring(0, 2)
      }

      // 2) Username fallback
      if (safeUsername) {
        return safeUsername.charAt(0).toUpperCase()
      }

      // 3) Email fallback
      if (safeEmail && safeEmail !== 'None') {
        return safeEmail.charAt(0).toUpperCase()
      }

      // 4) Absolute fallback
      return '?'
    },
    tooltipText() {
      const safeEmail = (this.email || '').trim()
      const username = (this.username || '').trim()
      if (!safeEmail || safeEmail === 'None') return username;
      return safeEmail;
    }
  },

  template: /* html */ `
    <v-menu :close-on-content-click="false">
      <template v-slot:activator="{ props: menu }">
        <v-tooltip location="top">
          <template v-slot:activator="{ props: tooltip }">
            <v-btn icon v-bind="{ ...menu, ...tooltip }">
              <v-avatar color="white" size="small" class="border">
                <span class="text-subtitle-2 text-primary">{{ userInitials }}</span>
              </v-avatar>
            </v-btn>
          </template>
          <span>{{ tooltipText }}</span>
        </v-tooltip>
      </template>
      <v-card variant="flat" width="225">
        <v-container class="d-flex ga-3 align-center">
          <v-avatar color="primary" variant="teal" class="border">
            <span class="text-h5 text-primary">{{ userInitials }}</span>
          </v-avatar>
          <span class="text-subtitle-2 text-truncate">{{ name || username }}</span>
        </v-container>

        <v-divider></v-divider>

        <v-list density="compact" nav>
            <v-list-subheader>Theme</v-list-subheader>

            <v-radio-group class="ml-5" hide-details v-model="$root.settings.dark" @update:model-value="$root.saveSettings" row>
                <v-radio :value="0" true-icon="mdi-check-circle">
                    <template #label>
                        <v-icon size="small" class="mr-2">mdi-weather-sunny</v-icon>
                        <span class="text-body-2">Light</span>
                    </template>
                </v-radio>
                <v-radio :value="1" true-icon="mdi-check-circle">
                    <template #label>
                        <v-icon size="small" class="mr-2">mdi-weather-night</v-icon>
                        <span class="text-body-2">Dark</span>
                    </template>
                </v-radio>
            </v-radio-group>
        </v-list>

        <v-divider></v-divider>
        
        <v-list density="compact" nav class="text-body-2">
            <v-list-subheader>My Security</v-list-subheader>
            <v-list-item class="ml-5" href="/change">Change Password</v-list-item>
            <v-list-item class="ml-5" href="/tf-setup">2FA Authentication</v-list-item>
            <v-list-item class="ml-5" href="/mf-recovery-codes">Recovery Codes</v-list-item>
            <v-list-item class="ml-5" href="/wan-register">Security Keys</v-list-item>
        </v-list>
        
        <v-divider></v-divider>

        <v-list density="compact" nav class="text-body-2">
          <v-list-item href="https://docs.bayanat.org/" target="_blank">User Guides <v-icon size="x-small">mdi-open-in-new</v-icon></v-list-item>
          <v-list-item href="https://community.bayanat.org/" target="_blank">Support <v-icon size="x-small">mdi-open-in-new</v-icon></v-list-item>
          <v-list-item href="https://github.com/sjacorg/bayanat/issues/new?assignees=&labels=&projects=&template=bug_report.md&title=" target="_blank">Report a Bug <v-icon size="x-small">mdi-open-in-new</v-icon></v-list-item>
        </v-list>
      </v-card>
    </v-menu>
  `,
});