const notificationMixin = {
  components: {
    'NotificationsList': NotificationsList,
  },
  computed: {
    hasUnreadNotifications() {
      return Boolean(this.unreadNotificationsCount)
    },
  },
  data: () => ({
    // notifications drawer
    isImportantNotificationsDialogVisible: false,
    isInitialLoadingNotifications: false,
    isMarkingAsReadImportantNotifications: false,
    isLoadingMoreNotifications: false,
    isNotificationsDrawerVisible: false,
    isNotificationsDialogFullscreen: false,
    isNotificationsDialogVisible: false,
    unreadNotificationsCount: 0,
    importantNotifications: [],
    notifications: null,
    totalNotifications: 0,
    hasMoreNotifications: false,
    currentNotificationTab: 'all',
    notificationsPagination: {
      page: 1,
      per_page: 10,
    },
    notificationIntervalId: null
  }),

  async mounted() {
    this.refetchNotifications();

    this.notificationIntervalId = setInterval(this.refetchNotifications, 60_000);
  },
  beforeUnmount() {
    clearInterval(this.notificationIntervalId);
  },

  methods: {
    async markAsReadImportantNotifications() {
      // TODO: Mark as read important notifications
      this.isMarkingAsReadImportantNotifications = true;
      await Promise.all(this.importantNotifications.map(async notification => {
        await this.readNotification(notification)
      }))
      this.isMarkingAsReadImportantNotifications = false;
      this.isImportantNotificationsDialogVisible = false;
    },
    toggleNotificationsDialog() {
      // Toggle the notifications dialog
      this.isNotificationsDialogVisible = !this.isNotificationsDialogVisible;

      // Close the settings dialog if the notifications dialog is open
      if (this.isNotificationsDialogVisible) {
        this.settingsDrawer = false;
        this.isNotificationsDrawerVisible = false;

        // Load notifications if not already loaded
        if (!this.notifications) {
          this.loadNotifications({ page: 1 });
        }
      }
    },
    toggleNotificationsDrawer() {
      // Toggle the notifications drawer
      this.isNotificationsDrawerVisible = !this.isNotificationsDrawerVisible;

      // Close the settings drawer if the notifications drawer is open
      if (this.isNotificationsDrawerVisible) {
        this.settingsDrawer = false;

        // Load notifications if not already loaded
        if (!this.notifications) {
          this.loadNotifications({ page: 1 });
        }
      }
    },
    async loadImportantNotifications() {
      try {
        if (this.isImportantNotificationsDialogVisible) return;

        // Construct query parameters
        const response = await axios.get(`/admin/api/notifications?is_urgent=true&status=unread`);

        if (response?.data?.items?.length) {
          this.importantNotifications = response.data.items
          this.isImportantNotificationsDialogVisible = true;
        }

        return response
      } catch (error) {
        const errorMessage = error?.response?.data?.message || error.message || "Failed to load notifications";
        this.showSnack(errorMessage);
      }
    },
    async loadNotifications(options) {
      // Prevent concurrent loading or invalid state
      if (this.isLoadingMoreNotifications || this.isInitialLoadingNotifications) return;

      try {
        // Set appropriate loading state
        if (options?.page === 1) {
          this.isInitialLoadingNotifications = true;
          this.notificationsPagination = {
            page: 1,
            per_page: 10,
          };
        } else {
          this.isLoadingMoreNotifications = true;
        }

        const nextOptions = { ...this.notificationsPagination, ...options }

        if (this.currentNotificationTab !== 'all') {
          nextOptions.status = this.currentNotificationTab;
        }

        // Construct query parameters
        const queryParams = new URLSearchParams(nextOptions);
        const response = await axios.get(`/admin/api/notifications?${queryParams.toString()}`);

        if (!response?.data) return

        if (options?.page === 1) {
          this.notifications = [];
          this.hasMoreNotifications = false;
        }

        // Destructure response data
        const { items: nextNotifications = [], total, hasMore, unreadCount = 0, hasUnreadUrgentNotifications = false } = response?.data || {};

        this.unreadNotificationsCount = unreadCount
        if (hasUnreadUrgentNotifications) {
          this.loadImportantNotifications()
        }

        // Update state
        this.notifications = [...(this.notifications || []), ...nextNotifications];
        if (this.currentNotificationTab === 'all') {
          this.totalNotifications = total || 0;
        }
        this.hasMoreNotifications = Boolean(hasMore);

        // Increment page if more notifications are available
        if (this.hasMoreNotifications) {
          this.notificationsPagination = {
            ...this.notificationsPagination,
            page: (this.notificationsPagination.page || 1) + 1,
          };
        }
      } catch (error) {
        const errorMessage = error?.response?.data?.message || error.message || "Failed to load notifications";
        this.showSnack(errorMessage);
      } finally {
        // Reset loading states
        this.isInitialLoadingNotifications = false;
        this.isLoadingMoreNotifications = false;
      }
    },
    async readNotification(nextNotification) {
      // Validate the notification object and its status
      if (!nextNotification?.id || nextNotification?.read_status) return;

      // Find the matching important notification
      const matchingImportantNotification = this.importantNotifications?.find(
        notification => notification.id === nextNotification.id
      );
      // Find the matching notification
      const matchingNotification = this.notifications?.find(
        notification => notification.id === nextNotification.id
      );

      // Update the read status if the notification is found
      if (matchingImportantNotification) matchingImportantNotification.read_status = true;
      if (matchingNotification) matchingNotification.read_status = true;

      if (matchingNotification || matchingImportantNotification) {
        this.decrementNotificationsCount()
      }

      const notificationId = nextNotification.id
      await axios.post(`/admin/api/notifications/${notificationId}/read`)
    },
    async fetchUnreadNotificationCount() {
      const response = await axios.get('/admin/api/notifications/unread/count');

      if (!response?.data) return

      this.unreadNotificationsCount = response?.data?.unread_count ?? 0;
      if (Boolean(response?.data?.has_unread_urgent_notifications)) {
        await this.loadImportantNotifications()
      }
    },
    async refetchNotifications() {
      this.fetchUnreadNotificationCount();

      if (!this.notifications) return;
      this.loadNotifications({ page: 1 });
    },
    decrementNotificationsCount() {
      if (this.unreadNotificationsCount > 0) {
        this.unreadNotificationsCount -= 1;
      }
    }
  },
  watch: {
    currentNotificationTab() {
      this.loadNotifications({ page: 1 });
    }
  },
};
