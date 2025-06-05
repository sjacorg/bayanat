#!/usr/bin/env python3
"""
Comprehensive Database Population Script with Mixed Arabic/English Data

This script creates realistic test data for the Bayanat database using Faker:
- Secondary entities: Labels, Sources, Locations (Arabic titles)
- Main entities: Bulletins (mixed Arabic/English), Actors, Incidents  
- Relationships between entities with proper probability indices

Usage: python populate_comprehensive.py
"""

import random
import os
from datetime import datetime, timedelta
from faker import Faker
import sys
import argparse

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enferno.app import create_app
from enferno.extensions import db
from enferno.admin.models import (
    Label, Source, Location, Bulletin, Actor, Incident,
    Btob, Atob, Itob, Atoa, Itoi,
    Country, LocationType, LocationAdminLevel
)
from enferno.user.models import User

# Initialize Faker with only Arabic and English locales
fake_ar = Faker('ar_SA')
fake_en = Faker('en_US')
fake = fake_en  # Default to English

def create_app_context():
    """Create application context"""
    app = create_app()
    return app.app_context()

def get_random_user():
    """Get a random user from the database"""
    users = User.query.all()
    return random.choice(users) if users else None

def generate_arabic_description_with_html():
    """Generate complex Arabic descriptions with HTML content"""
    templates = [
        # Template 1: Incident report with table
        f"""<div style="direction: rtl; font-family: Tahoma;">
        <h2 style="color: #8B0000;">{fake_ar.sentence(nb_words=random.randint(4, 8))}</h2>
        
        <p>{fake_ar.text(max_nb_chars=300)}</p>
        
        <table border="1" style="width: 100%; border-collapse: collapse;">
        <tr style="background-color: #f5f5f5;">
            <th>التاريخ</th>
            <th>عدد الضحايا</th>
            <th>المكان</th>
        </tr>
        <tr>
            <td>{fake_ar.date()}</td>
            <td>{random.randint(5, 50)}</td>
            <td>{fake_ar.city()}</td>
        </tr>
        <tr>
            <td>{fake_ar.date()}</td>
            <td>{random.randint(10, 80)}</td>
            <td>{fake_ar.city()}</td>
        </tr>
        </table>
        
        <blockquote style="border-right: 3px solid #dc3545; padding: 10px;">
        "{fake_ar.text(max_nb_chars=150)}"
        </blockquote>
        </div>""",
        
        # Template 2: Statistical report
        f"""<article style="direction: rtl;">
        <h1 style="color: #2c3e50;">{fake_ar.sentence(nb_words=random.randint(3, 6))}</h1>
        
        <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px;">
        <h3>🔢 الإحصائيات الرئيسية</h3>
        <ul>
        <li>العدد الإجمالي: <strong>{random.randint(100, 5000)}</strong></li>
        <li>النساء: <strong>{random.randint(30, 60)}%</strong></li>
        <li>الأطفال: <strong>{random.randint(20, 45)}%</strong></li>
        <li>كبار السن: <strong>{random.randint(5, 15)}%</strong></li>
        </ul>
        </div>
        
        <p>{fake_ar.text(max_nb_chars=400)}</p>
        
        <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107;">
        <h3>⚠️ تحذير مهم</h3>
        <p>{fake_ar.text(max_nb_chars=200)}</p>
        </div>
        </article>""",
        
        # Template 3: Witness testimony
        f"""<div style="direction: rtl; line-height: 1.8;">
        <h2 style="text-align: center; color: #8B0000;">شهادة موثقة من {fake_ar.name()}</h2>
        
        <p><strong>العمر:</strong> {random.randint(18, 70)} سنة</p>
        <p><strong>المهنة:</strong> {fake_ar.job()}</p>
        <p><strong>المكان:</strong> {fake_ar.city()}</p>
        
        <h3>🗣️ نص الشهادة:</h3>
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
        <p style="font-style: italic;">"{fake_ar.text(max_nb_chars=500)}"</p>
        </div>
        
        <div style="margin-top: 20px;">
        <h4>📋 تفاصيل إضافية:</h4>
        <ol>
        <li>{fake_ar.sentence(nb_words=random.randint(8, 15))}</li>
        <li>{fake_ar.sentence(nb_words=random.randint(6, 12))}</li>
        <li>{fake_ar.sentence(nb_words=random.randint(7, 14))}</li>
        </ol>
        </div>
        
        <p style="color: #666; font-size: 0.9em;">تم توثيق هذه الشهادة في {fake_ar.date_time_between(start_date='-2y', end_date='now').strftime('%Y/%m/%d')}</p>
        </div>"""
    ]
    
    return random.choice(templates)

def generate_mixed_bulletin_content():
    """Generate mixed Arabic/English bulletin content"""
    # Mix of Arabic and English titles
    if random.choice([True, False]):
        title = fake_en.sentence(nb_words=random.randint(4, 8)).rstrip('.')
        title_ar = fake_ar.sentence(nb_words=random.randint(3, 7)).rstrip('.')
    else:
        title = fake_en.catch_phrase() + " Report"
        title_ar = fake_ar.sentence(nb_words=random.randint(4, 6)).rstrip('.')
    
    # Descriptions primarily in Arabic with some HTML
    if random.choice([True, False, False]):  # 33% chance for HTML
        description = generate_arabic_description_with_html()
    else:
        # Pure Arabic descriptions
        description = fake_ar.text(max_nb_chars=random.randint(500, 1200))
    
    return title, title_ar, description

def create_labels(count=120):
    """Create labels with Arabic titles using Faker"""
    print(f"Creating {count} labels...")
    
    labels = []
    used_titles = set()
    
    # Label categories in Arabic for more realistic generation
    categories = ["انتهاكات", "شهادات", "تقارير", "توثيق", "أدلة", "تحقيقات", "حوادث", "جرائم"]
    
    for i in range(count):
        # Generate Arabic title
        if random.choice([True, False]):
            ar_title = f"{random.choice(categories)} {fake_ar.word()}"
        else:
            ar_title = fake_ar.sentence(nb_words=random.randint(2, 4)).rstrip('.')
        
        # Generate English title
        en_title = fake_en.sentence(nb_words=random.randint(2, 5)).rstrip('.')
        
        if ar_title not in used_titles:
            label = Label(
                title=en_title,
                title_ar=ar_title,
                comments=fake.text(max_nb_chars=200),
                verified=random.choice([True, False]),
                for_bulletin=True,
                for_actor=random.choice([True, False]),
                for_incident=random.choice([True, False]),
                order=random.randint(1, 100)
            )
            labels.append(label)
            used_titles.add(ar_title)
    
    db.session.add_all(labels)
    db.session.commit()
    print(f"Created {len(labels)} labels")
    return labels

def create_sources(count=80):
    """Create sources with Arabic titles using Faker"""
    print(f"Creating {count} sources...")
    
    sources = []
    used_titles = set()
    
    # Source types in Arabic
    source_types = ["منظمة", "مركز", "جمعية", "لجنة", "مؤسسة", "شبكة", "مرصد", "وكالة"]
    activities = ["حقوق الإنسان", "الإغاثة", "التوثيق", "الرصد", "المساعدة", "الحماية", "الإعلام"]
    
    for i in range(count):
        # Generate Arabic source name
        if random.choice([True, False]):
            ar_title = f"{random.choice(source_types)} {fake_ar.city()} لـ{random.choice(activities)}"
        else:
            ar_title = f"{random.choice(activities)} في {fake_ar.city()}"
        
        # Generate English title
        en_title = f"{fake_en.company()} {random.choice(['Foundation', 'Organization', 'Center', 'Network'])}"
        
        if ar_title not in used_titles:
            source = Source(
                title=en_title,
                title_ar=ar_title,
                comments=fake.text(max_nb_chars=300),
                source_type=random.choice(["Primary", "Secondary", "Tertiary"])
            )
            sources.append(source)
            used_titles.add(ar_title)
    
    db.session.add_all(sources)
    db.session.commit()
    print(f"Created {len(sources)} sources")
    return sources

def create_locations(count=150):
    """Create locations with Arabic titles using Faker"""
    print(f"Creating {count} locations...")
    
    location_types = LocationType.query.all()
    admin_levels = LocationAdminLevel.query.all()
    countries = Country.query.all()
    
    locations = []
    used_titles = set()
    
    # Location types in Arabic
    location_prefixes = ["مدينة", "بلدة", "قرية", "حي", "منطقة", "مخيم", "مستشفى", "مدرسة", "مسجد", "كنيسة"]
    
    for i in range(count):
        # Generate Arabic location name
        if random.choice([True, False]):
            ar_title = f"{random.choice(location_prefixes)} {fake_ar.city()}"
        else:
            ar_title = fake_ar.city()
        
        # Generate English title
        en_title = fake_en.city()
        
        if ar_title not in used_titles:
            location = Location(
                title=en_title,
                title_ar=ar_title,
                description=fake.text(max_nb_chars=200),
                location_type=random.choice(location_types) if location_types else None,
                admin_level=random.choice(admin_levels) if admin_levels else None,
                country=random.choice(countries) if countries else None,
                latlng=f"SRID=4326;POINT({fake.longitude()} {fake.latitude()})",
                postal_code=fake.postcode() if random.choice([True, False]) else None
            )
            locations.append(location)
            used_titles.add(ar_title)
    
    db.session.add_all(locations)
    db.session.commit()
    
    # Generate full_location paths for all locations
    print("Generating location full paths...")
    for location in locations:
        location.full_location = location.get_full_string()
        location.id_tree = location.get_id_tree()
    
    db.session.commit()
    print(f"Created {len(locations)} locations with full paths")
    return locations

def create_bulletins(count=500, labels=None, sources=None, locations=None):
    """Create bulletins with mixed Arabic/English content"""
    print(f"Creating {count} bulletins...")
    
    bulletins = []
    user = get_random_user()
    
    for i in range(count):
        title, title_ar, description = generate_mixed_bulletin_content()
        
        bulletin = Bulletin(
            title=title,
            title_ar=title_ar,
            sjac_title=fake_en.sentence(nb_words=random.randint(3, 6)).rstrip('.') if random.choice([True, False]) else None,
            sjac_title_ar=fake_ar.sentence(nb_words=random.randint(3, 6)).rstrip('.') if random.choice([True, False]) else None,
            description=description,
            user=user,
            assigned_to=user if random.choice([True, False]) else None,
            publish_date=fake.date_time_between(start_date='-2y', end_date='now'),
            documentation_date=fake.date_time_between(start_date='-2y', end_date='now'),
            status="Machine Created",
            source_link=fake.url() if random.choice([True, False]) else None,
            comments=fake.text(max_nb_chars=300) if random.choice([True, False]) else None,
            tags=[fake.word() for _ in range(random.randint(0, 5))]
        )
        
        # Add random labels (1-5 labels per bulletin)
        if labels:
            num_labels = random.randint(1, min(5, len(labels)))
            bulletin.labels = random.sample(labels, num_labels)
        
        # Add random sources (1-3 sources per bulletin)
        if sources:
            num_sources = random.randint(1, min(3, len(sources)))
            bulletin.sources = random.sample(sources, num_sources)
        
        # Add random locations (1-3 locations per bulletin)
        if locations:
            num_locations = random.randint(1, min(3, len(locations)))
            bulletin.locations = random.sample(locations, num_locations)
        
        bulletins.append(bulletin)
    
    # Add bulletins in batches to avoid memory issues
    batch_size = 100
    total_added = 0
    
    for i in range(0, len(bulletins), batch_size):
        batch = bulletins[i:i + batch_size]
        try:
            # Clear any pending session state
            db.session.expunge_all()
            db.session.add_all(batch)
            db.session.commit()
            total_added += len(batch)
            print(f"Added batch {i//batch_size + 1}: {len(batch)} bulletins (Total: {total_added})")
        except Exception as e:
            print(f"Error adding batch {i//batch_size + 1}: {e}")
            db.session.rollback()
    
    print(f"Successfully created {total_added} bulletins")
    return bulletins[:total_added]

def create_actors(count=300, locations=None):
    """Create actors with mixed Arabic/English names using Faker"""
    print(f"Creating {count} actors...")
    
    actors = []
    user = get_random_user()
    
    # Actor types
    person_types = ["Victim", "Witness", "Perpetrator", "Survivor", "Activist", "Journalist"]
    entity_types = ["Organization", "Government Agency", "Military Unit", "NGO", "Media Outlet"]
    
    for i in range(count):
        actor_type = random.choice(["Person", "Entity"])
        
        if actor_type == "Person":
            # Generate names in both languages
            name_ar = fake_ar.name()
            name_en = fake_en.name()
            
            actor = Actor(
                name=name_en,
                name_ar=name_ar,
                type=actor_type,
                age=str(random.randint(18, 80)) if random.choice([True, False]) else None,
                sex=random.choice(["Male", "Female"]) if random.choice([True, False]) else None,
                assigned_to=user if random.choice([True, False]) else None
            )
        else:
            # Entity names
            if random.choice([True, False]):
                name_ar = f"منظمة {fake_ar.city()} للحقوق"
                name_en = f"{fake_en.company()} {random.choice(['Foundation', 'Organization'])}"
            else:
                name_ar = f"جمعية {fake_ar.word()} الخيرية"
                name_en = f"{fake_en.city()} {random.choice(['Center', 'Institute', 'Network'])}"
            
            actor = Actor(
                name=name_en,
                name_ar=name_ar,
                type=actor_type,
                assigned_to=user if random.choice([True, False]) else None
            )
        
        # Add random locations
        if locations:
            num_locations = random.randint(1, min(2, len(locations)))
            actor.locations = random.sample(locations, num_locations)
        
        actors.append(actor)
    
    db.session.add_all(actors)
    db.session.commit()
    print(f"Created {len(actors)} actors")
    return actors

def create_incidents(count=250, labels=None, locations=None):
    """Create incidents with mixed Arabic/English content using Faker"""
    print(f"Creating {count} incidents...")
    
    incidents = []
    user = get_random_user()
    
    # Incident types
    incident_types = ["Bombing", "Shooting", "Detention", "Disappearance", "Torture", "Displacement"]
    
    for i in range(count):
        # Generate titles in both languages
        if random.choice([True, False]):
            title = f"{random.choice(incident_types)} in {fake_en.city()}"
            title_ar = f"حادثة {fake_ar.word()} في {fake_ar.city()}"
        else:
            title = fake_en.sentence(nb_words=random.randint(4, 7)).rstrip('.')
            title_ar = fake_ar.sentence(nb_words=random.randint(3, 6)).rstrip('.')
        
        # Arabic-focused descriptions
        description = fake_ar.text(max_nb_chars=random.randint(600, 1000))
        
        incident = Incident(
            title=title,
            title_ar=title_ar,
            description=description,
            assigned_to=user if random.choice([True, False]) else None,
            status="Machine Created",
            comments=fake.text(max_nb_chars=200) if random.choice([True, False]) else None
        )
        
        # Add random labels
        if labels:
            num_labels = random.randint(1, min(4, len(labels)))
            incident.labels = random.sample(labels, num_labels)
        
        # Add random locations
        if locations:
            num_locations = random.randint(1, min(2, len(locations)))
            incident.locations = random.sample(locations, num_locations)
        
        incidents.append(incident)
    
    db.session.add_all(incidents)
    db.session.commit()
    print(f"Created {len(incidents)} incidents")
    return incidents

def create_relationships(bulletins, actors, incidents):
    """Create simple relationships between entities (skip if problematic)"""
    print("Creating relationships...")
    
    user = get_random_user()
    relationships_created = 0
    
    # Only create B2B relationships (most reliable)
    print("Creating Bulletin to Bulletin relationships...")
    try:
        from enferno.admin.models import BtobInfo
        btob_infos = [info.id for info in BtobInfo.query.all()]
        
        for _ in range(min(50, len(bulletins) // 10)):
            bulletin1, bulletin2 = random.sample(bulletins, 2)
            try:
                if not Btob.are_related(bulletin1.id, bulletin2.id):
                    btob = Btob.relate(bulletin1, bulletin2)
                    btob.related_as = [random.choice(btob_infos)] if btob_infos else [1]
                    btob.probability = random.randint(0, 2)
                    btob.comment = fake_ar.text(max_nb_chars=100)
                    btob.user = user
                    db.session.add(btob)
                    relationships_created += 1
            except Exception:
                pass
        
        db.session.commit()
        print(f"Created {relationships_created} bulletin relationships")
    except Exception as e:
        print(f"Skipping relationships due to error: {e}")
        db.session.rollback()

def main(force_clear=False):
    """Main function to populate the database with comprehensive mixed-language data"""
    print("Starting database population with mixed Arabic/English data...")
    
    with create_app_context():
        try:
            # Check if we have users in the system
            user_count = User.query.count()
            if user_count == 0:
                print("Warning: No users found in the database. Some features may not work correctly.")
            
            # Safety check - prevent duplicate data
            existing_bulletins = Bulletin.query.filter(Bulletin.title_ar.isnot(None)).count()
            existing_actors = Actor.query.filter(Actor.name_ar.isnot(None)).count()
            
            if existing_bulletins > 0 or existing_actors > 0:
                print(f"\n⚠️  WARNING: Found existing seed data:")
                print(f"   - {existing_bulletins} bulletins with Arabic titles")
                print(f"   - {existing_actors} actors with Arabic names")
                
                if force_clear:
                    print("Force clear flag enabled - clearing existing data...")
                    clear_data = True
                else:
                    try:
                        response = input("\nDo you want to clear existing data and reseed? (y/N): ").lower()
                        clear_data = response == 'y'
                    except EOFError:
                        print("\nNo interactive input available - skipping without clearing data")
                        return
                
                if clear_data:
                    print("Clearing existing seed data...")
                    from sqlalchemy import text
                    
                    # Clear many-to-many relationships first (only the ones that exist)
                    print("Clearing many-to-many relationships...")
                    try:
                        db.session.execute(text("DELETE FROM bulletin_labels WHERE bulletin_id IN (SELECT id FROM bulletin WHERE title_ar IS NOT NULL)"))
                    except Exception as e:
                        print(f"  bulletin_labels: {e}")
                    try:
                        db.session.execute(text("DELETE FROM bulletin_sources WHERE bulletin_id IN (SELECT id FROM bulletin WHERE title_ar IS NOT NULL)"))
                    except Exception as e:
                        print(f"  bulletin_sources: {e}")
                    try:
                        db.session.execute(text("DELETE FROM bulletin_locations WHERE bulletin_id IN (SELECT id FROM bulletin WHERE title_ar IS NOT NULL)"))
                    except Exception as e:
                        print(f"  bulletin_locations: {e}")
                    try:
                        db.session.execute(text("DELETE FROM incident_locations WHERE incident_id IN (SELECT id FROM incident WHERE title_ar IS NOT NULL)"))
                    except Exception as e:
                        print(f"  incident_locations: {e}")
                    try:
                        db.session.execute(text("DELETE FROM incident_labels WHERE incident_id IN (SELECT id FROM incident WHERE title_ar IS NOT NULL)"))
                    except Exception as e:
                        print(f"  incident_labels: {e}")
                    
                    # Clear relationship entities that reference our seed data
                    print("Clearing relationship entities...")
                    db.session.execute(text("DELETE FROM btob WHERE bulletin_id IN (SELECT id FROM bulletin WHERE title_ar IS NOT NULL) OR related_bulletin_id IN (SELECT id FROM bulletin WHERE title_ar IS NOT NULL)"))
                    db.session.execute(text("DELETE FROM atob WHERE bulletin_id IN (SELECT id FROM bulletin WHERE title_ar IS NOT NULL) OR actor_id IN (SELECT id FROM actor WHERE name_ar IS NOT NULL)"))
                    db.session.execute(text("DELETE FROM itob WHERE bulletin_id IN (SELECT id FROM bulletin WHERE title_ar IS NOT NULL) OR incident_id IN (SELECT id FROM incident WHERE title_ar IS NOT NULL)"))
                    db.session.execute(text("DELETE FROM atoa WHERE actor_id IN (SELECT id FROM actor WHERE name_ar IS NOT NULL) OR related_actor_id IN (SELECT id FROM actor WHERE name_ar IS NOT NULL)"))
                    db.session.execute(text("DELETE FROM itoi WHERE incident_id IN (SELECT id FROM incident WHERE title_ar IS NOT NULL) OR related_incident_id IN (SELECT id FROM incident WHERE title_ar IS NOT NULL)"))
                    
                    # Clear main entities
                    print("Clearing main entities...")
                    Bulletin.query.filter(Bulletin.title_ar.isnot(None)).delete()
                    Actor.query.filter(Actor.name_ar.isnot(None)).delete()
                    Incident.query.filter(Incident.title_ar.isnot(None)).delete()
                    
                    # Clear secondary entities
                    print("Clearing secondary entities...")
                    Label.query.filter(Label.title_ar.isnot(None)).delete()
                    Source.query.filter(Source.title_ar.isnot(None)).delete()
                    Location.query.filter(Location.title_ar.isnot(None)).delete()
                    
                    db.session.commit()
                    print("✅ Existing seed data cleared")
                else:
                    print("❌ Aborted - existing data preserved")
                    return
            
            # Create secondary entities first (minimal)
            print("\n=== Creating Secondary Entities ===")
            labels = create_labels(50)
            sources = create_sources(30) 
            locations = create_locations(80)
            
            # Focus on massive bulletin creation for search testing
            print("\n=== Creating Bulletins (Main Focus) ===")
            bulletins = create_bulletins(5000, labels, sources, locations)
            actors = create_actors(200, locations)
            incidents = create_incidents(150, labels, locations)
            
            # Create relationships
            print("\n=== Creating Relationships ===")
            create_relationships(bulletins, actors, incidents)
            
            print("\n=== Population Complete ===")
            print(f"Successfully created:")
            print(f"  - {len(labels)} Labels (Arabic titles)")
            print(f"  - {len(sources)} Sources (Arabic titles)")
            print(f"  - {len(locations)} Locations (Arabic titles)")
            print(f"  - {len(bulletins)} Bulletins (mixed Arabic/English)")
            print(f"  - {len(actors)} Actors (mixed Arabic/English)")
            print(f"  - {len(incidents)} Incidents (mixed Arabic/English)")
            print(f"  - Various relationships between entities")
            print("\nDatabase populated with comprehensive test data for search optimization!")
            
        except Exception as e:
            print(f"Error during population: {e}")
            db.session.rollback()
            raise
        finally:
            db.session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Seed database with Arabic/English test data')
    parser.add_argument('--force-clear', action='store_true', 
                       help='Automatically clear existing seed data without prompting')
    args = parser.parse_args()
    
    main(force_clear=args.force_clear)