from enferno.extensions import db
from enferno.admin.models import ClaimedViolation, Eventtype, LocationAdminLevel, LocationType, PotentialViolation
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


def import_data():
    '''
    Imports SJAC data from data dir.
    '''
    data_path = 'enferno/data/'
    from werkzeug.datastructures import FileStorage

    # Eventtypes
    if not Eventtype.query.count():
        f = data_path + 'eventtypes.csv'
        fs = FileStorage(open(f, 'rb'))
        Eventtype.import_csv(fs)

    # potential violations
    if not PotentialViolation.query.count():
        f = data_path + 'potential_violation.csv'
        fs = FileStorage(open(f, 'rb'))
        PotentialViolation.import_csv(fs)

    # claimed violations
    if not ClaimedViolation.query.count():
        f = data_path + 'claimed_violation.csv'
        fs = FileStorage(open(f, 'rb'))
        ClaimedViolation.import_csv(fs)

def create_default_location_data():
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