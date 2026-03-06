# Actors

Actors are items of documentation about persons or bodies of interest that can be related to other Actors, Bulletins, or Incidents, usually coming from a single source.

## Fields

### ID

An internal ID unique to every Actor.

### Origin ID

The ID of the Actor from the source. Read-only, hyperlinked with the source link.

### Names

Individual fields for full, first, middle/father's, mother's, and last name, as well as nicknames.

### Description

Full description of the Actor and notes from the user.

### Sources

The source from which the information was obtained. Usually one source per Actor. Information from different sources can be added as separate Actors and linked with a "Same Person" relationship.

### Labels and Verified Labels

Tags about the information contained in the Actor profile.

### Sex / Minor/Adult

### Status

Civilian status with pre-set options: Civilian, Non-Civilian, Unknown, Police, Other Security Forces. These statuses are tailored to the Syrian conflict but can be changed.

### Actor Type

Person or body (entity).

### Date of Birth / Place of Birth / Place of Origin / Place of Residence

### Events

Time and location entries about the Actor's life events. These events power the [Map Visualization](/guide/map-visualization) feature, which renders actor movement patterns across locations.

### Occupation / Position / Spoken Dialects / Family Status / Ethnographic Information / Nationality / National ID Number

## Relationships

### Related Actors

#### Person Relationships

- **Same Person**: Same real person, potentially from different sources
- **Duplicate**: Exact same item from the same source (should be removed)
- **Parent / Child / Sibling / Family member**
- **Superior Officer / Subordinate Officer**
- **Member**: Person belongs to a body Actor

#### Body Relationships

- **Unit / Subunit**: Hierarchical body relationships
- **Group**: Person Actor that belongs to this body
- **Alleged Perpetrator**: This Actor is responsible for an incident involving the related Actor

#### Generic

- **Duplicate / Other**

Relationships can be added with three levels of certainty.

### Related Bulletins

Same roles as Bulletin-to-Actor: Injured Party, Alleged Perpetrator, Witness, Appeared, Participant.

### Related Incidents

Same roles as Related Bulletins.

### Related Media

Upload and link media files (pictures of a person, logos for a body). Videos and documents should be added as related Bulletins instead.

### Source Link / Publish Date / Documentation Date / Comment

Same as Bulletin fields.
