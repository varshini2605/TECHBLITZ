import csv
import io
import os
from datetime import datetime
import openpyxl
from werkzeug.utils import secure_filename
from models import db, Registration

# Header synonyms for fuzzy detection
HEADER_MAP = {
    'hall_ticket': [
        'hall ticket', 'hall ticket number', 'hallticket', 'hallticketnumber',
        'ht no', 'ht number', 'htno', 'roll number', 'roll no', 'registration number',
        'reg no', 'hall_ticket_number', 'hall_ticket', 'id', 'student id'
    ],
    'name': [
        'name', 'candidate name', 'student name', 'full name', 'participant name',
        'candidatename', 'studentname', 'fullname'
    ],
    'team_id': [
        'team id', 'teamid', 'team', 'team number', 'team no', 'team_id',
        'group id', 'group', 'team name', 'teamname'
    ],
    'email': [
        'email', 'email address', 'mail', 'e-mail', 'candidate email', 'student email'
    ]
}

def clean_str(val):
    if val is None:
        return ''
    return str(val).strip()

def detect_column_mappings(headers):
    """
    Given a list of header strings from a spreadsheet/CSV,
    match them to standard keys: hall_ticket, name, team_id, email.
    """
    detected = {
        'hall_ticket': None,
        'name': None,
        'team_id': None,
        'email': None
    }
    
    cleaned_headers = [clean_str(h).lower() for h in headers]
    
    for key, synonyms in HEADER_MAP.items():
        for i, header in enumerate(cleaned_headers):
            if header in synonyms:
                detected[key] = i
                break
        # Fallback substring match if exact match not found
        if detected[key] is None:
            for i, header in enumerate(cleaned_headers):
                if any(syn in header for syn in synonyms):
                    detected[key] = i
                    break
                    
    return detected

def parse_file(file_path):
    """
    Parses an Excel (.xlsx) or CSV file and extracts raw rows as lists of strings.
    """
    ext = file_path.rsplit('.', 1)[-1].lower()
    raw_rows = []
    
    if ext == 'csv':
        try:
            with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.reader(f)
                for row in reader:
                    raw_rows.append([clean_str(cell) for cell in row])
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {str(e)}")
            
    elif ext == 'xlsx':
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet = wb.active
            for row in sheet.iter_rows(values_only=True):
                # Filter out completely empty rows
                if any(row):
                    raw_rows.append([clean_str(cell) for cell in row])
        except Exception as e:
            raise ValueError(f"Failed to parse .xlsx file: {str(e)}")
    else:
        raise ValueError("Unsupported registration file. From Google Sheets, use File → Download → Microsoft Excel (.xlsx) or Comma-separated values (.csv), then upload that downloaded file.")
        
    return raw_rows

def preview_import_data(file_path, column_map=None):
    """
    Reads the file, detects columns (or uses column_map), validates records,
    and returns a preview structure for admin review.
    """
    raw_rows = parse_file(file_path)
    if not raw_rows or len(raw_rows) < 2:
        return {
            'success': False,
            'error': 'The uploaded file is empty or does not contain header and data rows.'
        }
        
    headers = raw_rows[0]
    data_rows = raw_rows[1:]
    
    if not column_map:
        detected_map = detect_column_mappings(headers)
    else:
        detected_map = column_map
        
    ht_idx = detected_map.get('hall_ticket')
    name_idx = detected_map.get('name')
    team_idx = detected_map.get('team_id')
    email_idx = detected_map.get('email')
    
    missing_mappings = []
    if ht_idx is None or ht_idx >= len(headers):
        missing_mappings.append('Hall Ticket Number')
    if name_idx is None or name_idx >= len(headers):
        missing_mappings.append('Name')
    if team_idx is None or team_idx >= len(headers):
        missing_mappings.append('Team ID')
        
    if missing_mappings:
        return {
            'success': True,
            'needs_mapping': True,
            'headers': headers,
            'detected_map': detected_map,
            'missing_mappings': missing_mappings,
            'message': f"Please map required columns: {', '.join(missing_mappings)}"
        }
        
    # Validation
    valid_records = []
    invalid_records = []
    seen_in_file_ht = set()
    file_duplicates = []
    
    # Query existing HT numbers in DB
    existing_records = {r.normalized_hall_ticket: r for r in Registration.query.all()}
    db_duplicates = []
    
    for row_idx, row in enumerate(data_rows, start=2):
        if not any(row):
            continue
            
        ht = row[ht_idx] if ht_idx is not None and ht_idx < len(row) else ''
        name = row[name_idx] if name_idx is not None and name_idx < len(row) else ''
        team = row[team_idx] if team_idx is not None and team_idx < len(row) else ''
        email = row[email_idx] if email_idx is not None and email_idx < len(row) else ''
        
        errors = []
        if not ht:
            errors.append('Missing Hall Ticket Number')
        if not name:
            errors.append('Missing Name')
        if not team:
            errors.append('Missing Team ID')
            
        norm_ht = Registration.normalize_string(ht)
        norm_team = Registration.normalize_string(team)
        
        is_file_dup = False
        if norm_ht in seen_in_file_ht:
            errors.append('Duplicate Hall Ticket in file')
            is_file_dup = True
        elif norm_ht:
            seen_in_file_ht.add(norm_ht)
            
        is_db_dup = False
        if norm_ht in existing_records:
            is_db_dup = True
            
        record_info = {
            'row_number': row_idx,
            'hall_ticket_number': ht,
            'name': name,
            'team_id': team,
            'email': email,
            'is_valid': len(errors) == 0,
            'errors': errors,
            'is_file_duplicate': is_file_dup,
            'is_db_duplicate': is_db_dup
        }
        
        if record_info['is_valid']:
            valid_records.append(record_info)
            if is_db_dup:
                db_duplicates.append(record_info)
        else:
            invalid_records.append(record_info)
            
    return {
        'success': True,
        'needs_mapping': False,
        'headers': headers,
        'detected_map': detected_map,
        'total_rows': len(data_rows),
        'valid_count': len(valid_records),
        'invalid_count': len(invalid_records),
        'duplicate_count': len(db_duplicates),
        'valid_records': valid_records[:50],  # Sample for preview
        'all_valid_records': valid_records,
        'invalid_records': invalid_records[:50],
        'db_duplicates': db_duplicates[:50]
    }

def commit_import_data(records, duplicate_mode='skip', source_filename='Uploaded File'):
    """
    Imports validated records transactionally.
    duplicate_mode:
      - 'skip': skip records where hall_ticket already exists in DB
      - 'keep': alias for skip
      - 'update': update existing record's name, team, email, updated_at
    """
    imported_count = 0
    updated_count = 0
    skipped_count = 0
    
    try:
        existing_map = {r.normalized_hall_ticket: r for r in Registration.query.all()}
        
        for rec in records:
            ht = rec['hall_ticket_number'].strip()
            name = rec['name'].strip()
            team = rec['team_id'].strip()
            email = rec.get('email', '').strip() or None
            
            norm_ht = Registration.normalize_string(ht)
            norm_team = Registration.normalize_string(team)
            
            if norm_ht in existing_map:
                if duplicate_mode == 'update':
                    existing = existing_map[norm_ht]
                    existing.name = name
                    existing.team_id = team
                    existing.normalized_team_id = norm_team
                    existing.email = email
                    existing.source_file = source_filename
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                else:  # 'skip' or 'keep'
                    skipped_count += 1
            else:
                new_reg = Registration(
                    hall_ticket_number=ht,
                    normalized_hall_ticket=norm_ht,
                    name=name,
                    team_id=team,
                    normalized_team_id=norm_team,
                    email=email,
                    status='ACTIVE',
                    source_file=source_filename,
                    imported_at=datetime.utcnow()
                )
                db.session.add(new_reg)
                existing_map[norm_ht] = new_reg
                imported_count += 1
                
        db.session.commit()
        return {
            'success': True,
            'imported': imported_count,
            'updated': updated_count,
            'skipped': skipped_count
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'error': f"Database transaction failed: {str(e)}"
        }
