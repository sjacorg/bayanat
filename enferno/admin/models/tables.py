from enferno.extensions import db

# joint table
bulletin_sources = db.Table(
    "bulletin_sources",
    db.Column("source_id", db.Integer, db.ForeignKey("source.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
    extend_existing=True,
)

# joint table
bulletin_locations = db.Table(
    "bulletin_locations",
    db.Column("location_id", db.Integer, db.ForeignKey("location.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
    extend_existing=True,
)

# joint table
bulletin_labels = db.Table(
    "bulletin_labels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
    extend_existing=True,
)

# joint table
bulletin_verlabels = db.Table(
    "bulletin_verlabels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
    extend_existing=True,
)

# joint table
bulletin_events = db.Table(
    "bulletin_events",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
    extend_existing=True,
)

# joint table
bulletin_roles = db.Table(
    "bulletin_roles",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column("bulletin_id", db.Integer, db.ForeignKey("bulletin.id"), primary_key=True),
    extend_existing=True,
)

# Updated joint table for actor_sources
actor_sources = db.Table(
    "actor_sources",
    db.Column("source_id", db.Integer, db.ForeignKey("source.id"), primary_key=True),
    db.Column(
        "actor_profile_id",
        db.Integer,
        db.ForeignKey("actor_profile.id"),
        primary_key=True,
    ),
    extend_existing=True,
)

# joint table for actor_labels
actor_labels = db.Table(
    "actor_labels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column(
        "actor_profile_id",
        db.Integer,
        db.ForeignKey("actor_profile.id"),
        primary_key=True,
    ),
)

# joint table for actor_verlabels
actor_verlabels = db.Table(
    "actor_verlabels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column(
        "actor_profile_id",
        db.Integer,
        db.ForeignKey("actor_profile.id"),
        primary_key=True,
    ),
    extend_existing=True,
)


# joint table
actor_events = db.Table(
    "actor_events",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
    extend_existing=True,
)

# joint table
actor_roles = db.Table(
    "actor_roles",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
    extend_existing=True,
)

actor_countries = db.Table(
    "actor_countries",
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
    db.Column("country_id", db.Integer, db.ForeignKey("countries.id"), primary_key=True),
    extend_existing=True,
)

actor_ethnographies = db.Table(
    "actor_ethnographies",
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
    db.Column("ethnography_id", db.Integer, db.ForeignKey("ethnographies.id"), primary_key=True),
    extend_existing=True,
)

actor_dialects = db.Table(
    "actor_dialects",
    db.Column("actor_id", db.Integer, db.ForeignKey("actor.id"), primary_key=True),
    db.Column("dialect_id", db.Integer, db.ForeignKey("dialects.id"), primary_key=True),
    extend_existing=True,
)


# joint table
incident_locations = db.Table(
    "incident_locations",
    db.Column("location_id", db.Integer, db.ForeignKey("location.id"), primary_key=True),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
    extend_existing=True,
)

# joint table
incident_labels = db.Table(
    "incident_labels",
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
    extend_existing=True,
)

# joint table
incident_events = db.Table(
    "incident_events",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
    extend_existing=True,
)

# joint table
incident_potential_violations = db.Table(
    "incident_potential_violations",
    db.Column(
        "potentialviolation_id",
        db.Integer,
        db.ForeignKey("potential_violation.id"),
        primary_key=True,
    ),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
    extend_existing=True,
)

# joint table
incident_claimed_violations = db.Table(
    "incident_claimed_violations",
    db.Column(
        "claimedviolation_id", db.Integer, db.ForeignKey("claimed_violation.id"), primary_key=True
    ),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
    extend_existing=True,
)

# joint table
incident_roles = db.Table(
    "incident_roles",
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
    db.Column("incident_id", db.Integer, db.ForeignKey("incident.id"), primary_key=True),
    extend_existing=True,
)
