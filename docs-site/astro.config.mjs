import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://docs.jambot.app',
  integrations: [
    starlight({
      title: 'JamBot',
      logo: {
        src: './src/assets/jambot_icon.png',
      },
      social: {
        github: 'https://github.com/asachs01/jambot',
      },
      customCss: [
        './src/styles/custom.css',
      ],
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Introduction', link: '/' },
            { label: 'Quick Start', link: '/getting-started/quick-start/' },
          ],
        },
        {
          label: 'Setup',
          items: [
            { label: 'Discord Setup', link: '/setup/discord/' },
            { label: 'Spotify Setup', link: '/setup/spotify/' },
            { label: 'Configuration', link: '/setup/configuration/' },
          ],
        },
        {
          label: 'Guides',
          items: [
            { label: 'Admin Guide', link: '/guides/admin-guide/' },
            { label: 'Deployment', link: '/guides/deployment/' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'Troubleshooting', link: '/reference/troubleshooting/' },
            { label: 'Changelog', link: '/reference/changelog/' },
          ],
        },
      ],
      head: [
        {
          tag: 'link',
          attrs: {
            rel: 'icon',
            href: '/jambot_icon.png',
            type: 'image/png',
          },
        },
      ],
    }),
  ],
});
