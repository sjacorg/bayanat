import pandas as pd

from enferno.admin.models import ClaimedViolation, Eventtype, LocationAdminLevel, LocationType, PotentialViolation, \
    AtobInfo, BtobInfo, AtoaInfo, ItobInfo, ItoaInfo, ItoiInfo, Country, Ethnography, MediaCategory, GeoLocationType
from enferno.extensions import db
from enferno.user.models import Role


def generate_user_roles():
    '''
    Generates standard user roles.
    '''
    # create admin role if it doesn't exist
    r = Role.query.filter_by(name='Admin').first()
    if not r:
        role = Role()
        role.name = 'Admin'
        role.description = 'System Role'
        role.save()

    # create DA role, if not exists
    r = Role.query.filter_by(name='DA').first()
    if not r:
        role = Role()
        role.name = 'DA'
        role.description = 'System Role'
        role.save()

    # create MOD role, if not exists
    r = Role.query.filter_by(name='Mod').first()
    if not r:
        role = Role()
        role.name = 'Mod'
        role.description = 'System Role'
        role.save()


def import_default_data():
    '''
    Imports SJAC data from data dir.
    '''
    items = [(Eventtype, 'enferno/data/eventtypes.csv'),
             (PotentialViolation, 'enferno/data/potential_violation.csv'),
             (ClaimedViolation, 'enferno/data/claimed_violation.csv'),
             (AtobInfo, 'enferno/data/atob_info.csv'),
             (BtobInfo, 'enferno/data/atob_info.csv'),
             (AtoaInfo, 'enferno/data/atoa_info.csv'),
             (ItobInfo, 'enferno/data/itob_info.csv'),
             (ItoaInfo, 'enferno/data/itoa_info.csv'),
             (ItoiInfo, 'enferno/data/itoi_info.csv'),
             (Country, 'enferno/data/countries.csv'),
             (Ethnography, 'enferno/data/ethnographies.csv'),
             (MediaCategory, 'enferno/data/media_categories.csv'),
             (GeoLocationType, 'enferno/data/geo_location_types.csv')]
             
    for model, path in items:
        import_csv_to_table(model, path)


def create_default_location_data():
    '''
    Generates default required location data.
    '''
    if not LocationAdminLevel.query.all():
        db.session.add(LocationAdminLevel(code=1, title='Governorate'))
        db.session.add(LocationAdminLevel(code=2, title='District'))
        db.session.add(LocationAdminLevel(code=3, title='Subdistrict'))
        db.session.add(LocationAdminLevel(code=4, title='Community'))
        db.session.add(LocationAdminLevel(code=5, title='Neighbourhood'))
        db.session.commit()

    if not LocationType.query.all():
        db.session.add(LocationType(title='Administrative Location'))
        db.session.add(LocationType(title='Point of Interest'))
        db.session.commit()


def import_csv_to_table(model, csv_file_path):
    """
    Imports CSV data into a database model.
    """
    df = pd.read_csv(csv_file_path, parse_dates=True, na_filter=False)

    # Remove the 'deleted' column from DataFrame if it exists
    df.drop(columns=['deleted'], errors='ignore', inplace=True)

    # Skip if model table already contains data
    if db.session.query(model).first():
        print(f"{model.__name__} table already populated.")
        return

    # Add each row as a record in the model table
    for _, row in df.iterrows():
        data = {col: row[col] for col in row.index if hasattr(model, col)}
        db.session.add(model(**data))

    db.session.commit()
    print(f"Data imported into {model.__name__}.")