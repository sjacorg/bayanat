import { defineConfig } from "vitepress";

export default defineConfig({
  title: "Bayanat",
  description:
    "Open source platform for processing human rights violations and war crimes data",

  head: [["link", { rel: "icon", href: "/favicon.ico" }]],

  themeConfig: {
    logo: "/logo.svg",

    nav: [
      { text: "Guide", link: "/guide/what-is-bayanat" },
      { text: "Deployment", link: "/deployment/installation" },
      { text: "Methodology", link: "/methodology/analysis" },
      { text: "Security", link: "/security/threat-model" },
      {
        text: "v3.0.0",
        link: "https://github.com/sjacorg/bayanat/releases",
      },
    ],

    sidebar: {
      "/guide/": [
        {
          text: "Introduction",
          items: [
            { text: "What is Bayanat?", link: "/guide/what-is-bayanat" },
          ],
        },
        {
          text: "Core Concepts",
          items: [
            { text: "Bulletins", link: "/guide/bulletins" },
            { text: "Actors", link: "/guide/actors" },
            { text: "Incidents", link: "/guide/incidents" },
            { text: "Events", link: "/guide/events" },
            { text: "Sources", link: "/guide/sources" },
            { text: "Locations", link: "/guide/locations" },
            { text: "Labels", link: "/guide/labels" },
          ],
        },
        {
          text: "Features",
          items: [
            { text: "Workflow", link: "/guide/workflow" },
            { text: "Search", link: "/guide/search" },
            { text: "Permissions", link: "/guide/permissions" },
            { text: "Access Control", link: "/guide/access-control" },
            { text: "Revision History", link: "/guide/revision-history" },
            { text: "Activity Monitor", link: "/guide/activity" },
            { text: "Data Export", link: "/guide/data-export" },
            { text: "Video Deduplication", link: "/guide/deduplication" },
            { text: "OCR & Text Extraction", link: "/guide/ocr" },
            { text: "Data Import", link: "/guide/data-import" },
            { text: "Bulk Operations", link: "/guide/bulk-operations" },
            { text: "Media Management", link: "/guide/media" },
            { text: "Notifications", link: "/guide/notifications" },
            { text: "Dynamic Fields", link: "/guide/dynamic-fields" },
          ],
        },
      ],
      "/deployment/": [
        {
          text: "Deployment",
          items: [
            { text: "Installation", link: "/deployment/installation" },
            { text: "Configuration", link: "/deployment/configuration" },
            { text: "Docker", link: "/deployment/docker" },
            { text: "Backups", link: "/deployment/backups" },
          ],
        },
      ],
      "/methodology/": [
        {
          text: "Methodology",
          items: [
            { text: "Analysis", link: "/methodology/analysis" },
            { text: "Missing Persons", link: "/methodology/missing-persons" },
            { text: "Verified Labels", link: "/methodology/verified-labels" },
            {
              text: "Unverified Labels",
              link: "/methodology/unverified-labels",
            },
          ],
        },
      ],
      "/security/": [
        {
          text: "Security",
          items: [
            { text: "Threat Model", link: "/security/threat-model" },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: "github", link: "https://github.com/sjacorg/bayanat" },
    ],

    search: {
      provider: "local",
    },

    editLink: {
      pattern: "https://github.com/sjacorg/bayanat/edit/main/docs/:path",
      text: "Edit this page on GitHub",
    },

    footer: {
      message:
        "Released under the AGPL-3.0 License. Developed by the Syria Justice and Accountability Centre.",
    },
  },
});
