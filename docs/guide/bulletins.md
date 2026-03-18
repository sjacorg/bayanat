# Bulletins

A Bulletin is one piece of documentation that provides information about a specific event. Bulletins could be from almost any type of content, such as videos, audio, pictures, documents, interviews, reports, text files, etc.

## Fields

### ID

An internal ID unique to every Bulletin.

### Origin ID

The ID of the Bulletin in the source. Read-only field that can be added when loading data into the system. Hyperlinked with the source link.

### Title

Bilingual field for the original title of the Bulletin in the source.

### SJAC Title

Bilingual field for a second title provided by the user, useful when the original title doesn't accurately describe the content.

### Ref

Internal reference numbers or codes.

### Sources

Links the Bulletin to one or more sources. A Bulletin normally comes from one source, but multiple sources are supported (e.g., the uploader and the host website of a video).

### Description

Full description of the Bulletin and notes from the user.

### Locations

Locations related to the Bulletin (e.g., where an incident took place).

### Labels and Verified Labels

Tags about the content of the Bulletin.

### Related Bulletins

Link to other Bulletins using pre-set roles:

- **Part of a series**: Items in a single documentation medium (e.g., sequential videos, pages of a document)
- **Same person**: A person appears in both Bulletins
- **Same object**: An object appears in both (e.g., a building, statue)
- **Duplicate**: Same source/content
- **Other**: No specific relationship type

### Related Actors

Link to Actors with pre-set roles:

- **Injured Party**: Actor is an injured party of a violation
- **Alleged Perpetrator**: Actor is an alleged perpetrator
- **Witness**: Actor is a witness
- **Appeared**: Actor appears in the Bulletin
- **Participant**: Actor is involved but the action is not a violation

### Related Incidents

Link to Incidents. Currently uses a single "Default" relationship.

### Media

View, upload, and link media files. The video player has built-in screenshot functionality.

### Events

Add one or more time and location entries from the information contained in the Bulletin.

### Source Link

URL to the original source. Validates the entry. "Not Available" checkbox for offline sources. "Private" option for unreachable URLs. Required unless "Not Available" is checked.

### Publish Date

Date and time of publishing.

### Documentation Date

Date and time the information was documented.

### Comment

Required with every update to describe the nature of the change.
