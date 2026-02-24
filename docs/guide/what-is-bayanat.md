# What is Bayanat?

[Bayanat](https://bayanat.org/) is the second generation of SJAC's [open-source](https://github.com/sjacorg/bayanat) web data management application. SJAC had been using the first generation, Corroborator, since 2014. In late 2019, SJAC decided to rewrite the application from scratch using the Flask Python microframework. SJAC used its own six years of first-hand experience in collecting, preserving, processing, and sharing documentation of human rights violations to build Bayanat.

The main purpose of Bayanat is to attack the challenge of big data in human rights documentation head-on. SJAC has developed an analytical methodology based on international humanitarian and human rights law. Events are cataloged according to specific IHL violations. This allows the most relevant evidence to be identified at a keystroke, enabling a variety of transitional justice efforts. Despite its main focus on human rights documentation, Bayanat can be utilized to research any other topic.

## Key Features

- Clear and consistent user interface with a focus on performance and efficiency
- User management and permissions system with multiple levels of access
- Detailed revision history for each item, with snapshots for each edit
- Activity monitoring to track all logins and changes
- Powerful custom search and filtering with simple and complex queries
- Simple data management to facilitate processing large datasets

## Security

Bayanat employs industry best practices: safe HTML generation, sanitized inputs, hashed/salted passwords, encrypted communication. User permissions are applied on both the front and back end.

## Database Components

There are three main components:

- **Bulletins**: Single pieces of documentation (videos, images, documents, interviews, reports, etc.)
- **Actors**: Persons or entities involved in events (alleged perpetrators, witnesses, injured parties, etc.)
- **Incidents**: Where Actors and Bulletins related to the same event are bundled and analyzed

Supporting components include [Events](/guide/events), [Sources](/guide/sources), [Locations](/guide/locations), and [Labels](/guide/labels).

## License

Bayanat is released under the [AGPL-3.0 License](https://github.com/sjacorg/bayanat/blob/main/LICENSE). The methodology and documentation content are available under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
