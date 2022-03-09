<p align="center">
  <a href="https://bayanat.org" target="_blank">
    <img alt="Bayanat" width="250" src="enferno/static/img/bayanat-h-v2.svg">
  </a>
</p>

Bayanat is an open source data management solution for processing huge amounts of data relevant to human rights abuses and war crimes, developed and maintained by Syrian talents at the [Syria Justice and Accountability Centre](https://syriaaccountability.org/) (SJAC). You can watch this [video](https://www.youtube.com/watch?v=thCkihoXAk0) for a quick introduction into Bayanat.

Installation and Documentation
------------------------------
Installation guidelines and user manual are available at [docs.bayanat.org](https://docs.bayanat.org/).

Localization
------------
Bayanat currently has translations for the following lanaguages:
- Arabic
- Ukrainian

You can help by translating Bayanat to your language. `messages.pot` file is the translation template for Bayanat.

Live Demo
---------
You can access a demo instance of Bayanat on [demo.bayanat.org](https://demo.bayanat.org/). You can use the following credentials to log in:

- `demo@bayanat.org`/`demo` for [Data Analyst](https://docs.bayanat.org/en/users-groups#data-analyst-da) access level.
- `admin@bayanat.org`/`admin` for [Administrator](https://docs.bayanat.org/en/users-groups#administrator) access level. 

Please note:
- This server will be reset every 15 minutes. Feel free to make changes to items in the database.
- Upload feature is disabled on this server to prevent abuse.
- Please avoid changing the passwords or setting up two factor authentication as this will deny other users access to the server until it's reset.

Updates
-------
The main purpose of this project is to support the work of SJAC's [Data Analysis team](https://syriaaccountability.org/what-we-do/) as well as partner organizations currently using Bayanat. SJAC is looking for additional resources in order to develop extra features and tools that make it easier for other human rights organizations and activists to use Bayanat and load existing data.

Stable releases will be pushed to this repository every few weeks and critical updates will be pushed sooner.

In most cases updates can be implemented by pulling the new code and restarting the services. However, in some cases where changes to the database have been introduced, migrations might be needed. We'll provide [instructions](https://github.com/sjacorg/bayanat/releases) to carry out those migrations if they are required.

It's critical to understand that, in all cases, **backups must be taken before pulling any new updates**. For production environments with important data, it's advised to use two backup methods with at least one taking daily backups.

Support
-------
You can use [Issues](https://github.com/sjacorg/bayanat/issues) in this repository to report bugs in Bayanat.

Donate
-------
If you like our work please consider making a donation at [donate.syriaaccountability.org](https://donate.syriaaccountability.org/).

License
-------------
This system is distributed WITHOUT ANY WARRANTY under the GNU Affero General Public License v3.0.
