"""
Generate 5 Sample FNOL (First Notice of Loss) Documents
Format: Based on ACORD Automobile Loss Notice form structure
Currency: ₹ (Indian Rupees / INR)

Run this script to create the sample PDFs:
    python generate_samples.py
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import os


def draw_acord_form(c, data, page_width, page_height):
    """Draw an ACORD-style automobile loss notice form."""

    # Colors
    header_bg = HexColor('#1a237e')
    section_bg = HexColor('#e8eaf6')
    line_color = HexColor('#90a4ae')
    text_color = HexColor('#212121')
    label_color = HexColor('#546e7a')

    margin = 40
    y = page_height - 40
    content_width = page_width - 2 * margin

    # ===== FORM HEADER =====
    c.setFillColor(header_bg)
    c.rect(margin, y - 50, content_width, 50, fill=1, stroke=0)
    c.setFillColor(HexColor('#ffffff'))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin + 12, y - 20, "AUTOMOBILE LOSS NOTICE")
    c.setFont("Helvetica", 9)
    c.drawString(margin + 12, y - 38, "ACORD FORM (First Notice of Loss)")

    # Date on right
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(page_width - margin - 12, y - 20, "DATE (DD/MM/YYYY)")
    c.setFont("Helvetica", 10)
    c.drawRightString(page_width - margin - 12, y - 38, data.get('form_date', ''))

    y -= 60

    def draw_section_header(y_pos, title):
        c.setFillColor(section_bg)
        c.rect(margin, y_pos - 18, content_width, 18, fill=1, stroke=0)
        c.setStrokeColor(line_color)
        c.rect(margin, y_pos - 18, content_width, 18, fill=0, stroke=1)
        c.setFillColor(header_bg)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin + 6, y_pos - 14, title)
        return y_pos - 18

    def draw_field(y_pos, label, value, x_offset=margin + 8, field_width=250):
        c.setFillColor(label_color)
        c.setFont("Helvetica", 7)
        c.drawString(x_offset, y_pos - 10, label)
        c.setFillColor(text_color)
        c.setFont("Helvetica", 9)
        if value:
            c.drawString(x_offset, y_pos - 22, str(value))
        # Underline
        c.setStrokeColor(HexColor('#e0e0e0'))
        c.line(x_offset, y_pos - 25, x_offset + field_width, y_pos - 25)
        return y_pos - 30

    def draw_field_pair(y_pos, label1, val1, label2, val2):
        half = content_width / 2 - 10
        draw_field(y_pos, label1, val1, margin + 8, half - 20)
        draw_field(y_pos, label2, val2, margin + half + 10, half - 20)
        return y_pos - 30

    # ===== AGENCY / POLICY SECTION =====
    y = draw_section_header(y, "AGENCY / POLICY INFORMATION")
    y = draw_field_pair(y, "POLICY NUMBER", data.get('policy_number', ''),
                        "CARRIER", data.get('carrier', 'National Insurance Co. Ltd.'))
    y = draw_field_pair(y, "POLICYHOLDER NAME (First, Middle, Last)", data.get('policyholder_name', ''),
                        "EFFECTIVE DATES", data.get('effective_dates', ''))
    y = draw_field_pair(y, "DATE OF BIRTH", data.get('dob', ''),
                        "CONTACT PHONE", data.get('phone', ''))
    y = draw_field(y, "EMAIL ADDRESS", data.get('email', ''), margin + 8, content_width - 20)

    y -= 8

    # ===== LOSS SECTION =====
    y = draw_section_header(y, "LOSS / INCIDENT INFORMATION")
    y = draw_field_pair(y, "DATE OF LOSS (DD/MM/YYYY)", data.get('loss_date', ''),
                        "TIME OF LOSS", data.get('loss_time', ''))
    y = draw_field(y, "LOCATION OF LOSS", data.get('loss_location', ''), margin + 8, content_width - 20)

    # Description box
    c.setFillColor(label_color)
    c.setFont("Helvetica", 7)
    c.drawString(margin + 8, y - 10, "DESCRIPTION OF ACCIDENT")
    c.setStrokeColor(line_color)
    c.rect(margin + 6, y - 70, content_width - 16, 55, fill=0, stroke=1)
    c.setFillColor(text_color)
    c.setFont("Helvetica", 9)
    desc = data.get('description', '')
    # Word wrap description
    words = desc.split()
    lines = []
    current_line = ''
    for word in words:
        test = current_line + ' ' + word if current_line else word
        if c.stringWidth(test, "Helvetica", 9) < content_width - 36:
            current_line = test
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    text_y = y - 24
    for line in lines[:4]:  # Max 4 lines
        c.drawString(margin + 12, text_y, line)
        text_y -= 13
    y -= 80

    y -= 5

    # ===== INSURED VEHICLE SECTION =====
    y = draw_section_header(y, "INSURED VEHICLE / ASSET DETAILS")
    y = draw_field_pair(y, "ASSET TYPE", data.get('asset_type', ''),
                        "YEAR / MAKE", data.get('vehicle_make', ''))
    y = draw_field_pair(y, "MODEL / BODY TYPE", data.get('vehicle_model', ''),
                        "V.I.N. / ASSET ID", data.get('asset_id', ''))
    y = draw_field_pair(y, "PLATE NUMBER / REGISTRATION", data.get('plate_number', ''),
                        "STATE", data.get('state', ''))
    y = draw_field(y, "DESCRIBE DAMAGE", data.get('damage_description', ''), margin + 8, content_width - 20)

    y -= 5

    # ===== OTHER PARTY SECTION =====
    y = draw_section_header(y, "OTHER VEHICLE / THIRD PARTY")
    y = draw_field_pair(y, "THIRD PARTY NAME", data.get('third_party', ''),
                        "THIRD PARTY VEHICLE", data.get('third_party_vehicle', ''))
    y = draw_field(y, "THIRD PARTY CONTACT / INSURANCE", data.get('third_party_contact', ''), margin + 8, content_width - 20)

    y -= 5

    # ===== INJURED PERSONS =====
    y = draw_section_header(y, "INJURED PERSONS")
    y = draw_field_pair(y, "NAME", data.get('injured_name', ''),
                        "EXTENT OF INJURY", data.get('injury_extent', ''))

    y -= 5

    # ===== ESTIMATE & CLAIM TYPE =====
    y = draw_section_header(y, "ESTIMATE & CLAIM DETAILS")
    y = draw_field_pair(y, "ESTIMATED DAMAGE (INR)", data.get('estimated_damage', ''),
                        "INITIAL ESTIMATE (INR)", data.get('initial_estimate', ''))
    y = draw_field_pair(y, "CLAIM TYPE", data.get('claim_type', ''),
                        "ATTACHMENTS", data.get('attachments', ''))

    y -= 5

    # ===== REPORTED BY =====
    y = draw_section_header(y, "REPORTED BY")
    y = draw_field_pair(y, "REPORTED BY", data.get('reported_by', ''),
                        "DATE REPORTED", data.get('form_date', ''))

    # Footer
    c.setFillColor(label_color)
    c.setFont("Helvetica", 7)
    c.drawString(margin, 30, "ACORD FORM (Sample FNOL)")
    c.drawRightString(page_width - margin, 30, "Page 1 of 1")


# ===== 5 SAMPLE SCENARIOS =====

samples = [
    {
        'filename': 'claim_001_fast_track.pdf',
        'form_date': '03/02/2026',
        'policy_number': 'NIC-MH-2024-08742',
        'carrier': 'National Insurance Co. Ltd.',
        'policyholder_name': 'Rajesh Kumar Sharma',
        'effective_dates': '01/04/2025 to 31/03/2026',
        'dob': '15/08/1985',
        'phone': '+91-9876543210',
        'email': 'rajesh.sharma@email.com',
        'loss_date': '01/02/2026',
        'loss_time': '10:30 AM',
        'loss_location': 'MG Road, Near Forum Mall, Bangalore, Karnataka 560025',
        'description': 'Minor rear-end collision at traffic signal. The insured vehicle was stationary at a red light when another vehicle hit from behind at low speed. Minor dent on rear bumper and cracked tail light. No injuries to any party. Weather was clear and road was dry.',
        'asset_type': 'Motor Vehicle - Private Car',
        'vehicle_make': '2022 Maruti Suzuki',
        'vehicle_model': 'Swift VXi - Hatchback',
        'asset_id': 'MA3EYD81S00T52847',
        'plate_number': 'KA-01-MJ-4521',
        'state': 'Karnataka',
        'damage_description': 'Rear bumper dent, cracked left tail light assembly',
        'third_party': 'Vikram Patel',
        'third_party_vehicle': '2021 Hyundai i20 - KA-03-AB-7823',
        'third_party_contact': '+91-9845012345, ICICI Lombard Policy #IL-2024-55123',
        'injured_name': '',
        'injury_extent': '',
        'estimated_damage': '8,500',
        'initial_estimate': '8,500',
        'claim_type': 'Auto - Property Damage',
        'attachments': 'Photos (3), Police spot report',
        'reported_by': 'Rajesh Kumar Sharma (Self)',
        'claimant': 'Rajesh Kumar Sharma',
        'contact_details': '+91-9876543210, rajesh.sharma@email.com'
    },
    {
        'filename': 'claim_002_manual_review.pdf',
        'form_date': '02/02/2026',
        'policy_number': 'UIIC-DL-2023-33210',
        'carrier': 'United India Insurance',
        'policyholder_name': 'Priya Menon',
        'effective_dates': '',  # MISSING
        'dob': '22/03/1990',
        'phone': '+91-8801234567',
        'email': 'priya.menon@gmail.com',
        'loss_date': '30/01/2026',
        'loss_time': '3:45 PM',
        'loss_location': 'NH-44, near Moinabad toll plaza, Hyderabad, Telangana',
        'description': 'Vehicle skidded on wet road and hit the highway divider. Front portion of the car is significantly damaged. Airbags deployed. Driver had minor bruises but no serious injuries. Towing was required from the accident site.',
        'asset_type': 'Motor Vehicle - Private Car',
        'vehicle_make': '2023 Honda',
        'vehicle_model': 'City ZX CVT - Sedan',
        'asset_id': '',  # MISSING
        'plate_number': 'TS-09-FA-1234',
        'state': 'Telangana',
        'damage_description': 'Front bumper destroyed, hood bent, radiator damaged, both airbags deployed',
        'third_party': 'None - Single vehicle accident',
        'third_party_vehicle': 'N/A',
        'third_party_contact': 'N/A',
        'injured_name': '',
        'injury_extent': '',
        'estimated_damage': '1,85,000',
        'initial_estimate': '',  # MISSING
        'claim_type': 'Auto - Property Damage',
        'attachments': 'Photos (5), FIR copy',
        'reported_by': 'Priya Menon (Self)',
        'claimant': 'Priya Menon',
        'contact_details': '+91-8801234567, priya.menon@gmail.com'
    },
    {
        'filename': 'claim_003_investigation.pdf',
        'form_date': '01/02/2026',
        'policy_number': 'OIC-MH-2024-77654',
        'carrier': 'Oriental Insurance Co.',
        'policyholder_name': 'Suresh Babu Reddy',
        'effective_dates': '15/06/2025 to 14/06/2026',
        'dob': '10/11/1978',
        'phone': '+91-9912345678',
        'email': 'suresh.reddy@yahoo.com',
        'loss_date': '28/01/2026',
        'loss_time': '11:50 PM',
        'loss_location': 'Isolated road near Lonavala, off Mumbai-Pune Expressway, Maharashtra',
        'description': 'Vehicle was found completely burned on an isolated road near Lonavala. The circumstances appear staged and inconsistent with the driver account. The insured claims the car caught fire spontaneously while parked, but the burn pattern suggests fraud. Witness reports are inconsistent with the timeline provided. Investigation is strongly recommended.',
        'asset_type': 'Motor Vehicle - Private Car',
        'vehicle_make': '2024 BMW',
        'vehicle_model': '3 Series 320d - Sedan',
        'asset_id': 'WBA5R1C50KAE12345',
        'plate_number': 'MH-01-CZ-9999',
        'state': 'Maharashtra',
        'damage_description': 'Total loss - vehicle completely gutted by fire',
        'third_party': 'None',
        'third_party_vehicle': 'N/A',
        'third_party_contact': 'N/A',
        'injured_name': '',
        'injury_extent': '',
        'estimated_damage': '42,00,000',
        'initial_estimate': '42,00,000',
        'claim_type': 'Auto - Total Loss / Fire',
        'attachments': 'Fire brigade report, Photos (12), Police FIR',
        'reported_by': 'Suresh Babu Reddy (Self)',
        'claimant': 'Suresh Babu Reddy',
        'contact_details': '+91-9912345678, suresh.reddy@yahoo.com'
    },
    {
        'filename': 'claim_004_specialist_injury.pdf',
        'form_date': '31/01/2026',
        'policy_number': 'NIAC-TN-2025-12890',
        'carrier': 'New India Assurance Co.',
        'policyholder_name': 'Anitha Krishnamurthy',
        'effective_dates': '01/01/2025 to 31/12/2025',
        'dob': '05/05/1982',
        'phone': '+91-9443012345',
        'email': 'anitha.k@outlook.com',
        'loss_date': '29/01/2026',
        'loss_time': '8:15 AM',
        'loss_location': 'Anna Salai, near Saidapet junction, Chennai, Tamil Nadu 600015',
        'description': 'Head-on collision with a truck that jumped the median. The insured driver suffered serious bodily injury including fractured ribs and a dislocated shoulder. The passenger sustained a head injury requiring hospitalization and emergency surgery. Both are currently admitted to Apollo Hospital, Chennai.',
        'asset_type': 'Motor Vehicle - Private Car',
        'vehicle_make': '2021 Toyota',
        'vehicle_model': 'Innova Crysta GX - MPV',
        'asset_id': 'MHFZ29G0SM0012345',
        'plate_number': 'TN-01-BC-5678',
        'state': 'Tamil Nadu',
        'damage_description': 'Complete front-end damage, engine bay crushed, windshield shattered, both front doors jammed',
        'third_party': 'Ramu Transport - Driver: Selvam',
        'third_party_vehicle': '2019 Tata LPT 1613 Truck - TN-22-G-4567',
        'third_party_contact': 'Ramu Transport: +91-4428001234, Bajaj Allianz Policy #BA-COM-2024-99876',
        'injured_name': 'Anitha Krishnamurthy, Deepa Lakshmi (passenger)',
        'injury_extent': 'Fractured ribs, dislocated shoulder (driver). Head injury requiring surgery (passenger). Both hospitalized.',
        'estimated_damage': '3,50,000',
        'initial_estimate': '3,50,000',
        'claim_type': 'Injury - Bodily Injury + Property',
        'attachments': 'Hospital admission records, Photos (8), FIR copy, Ambulance receipt',
        'reported_by': 'Venkat Krishnamurthy (Spouse)',
        'claimant': 'Anitha Krishnamurthy',
        'contact_details': '+91-9443012345, anitha.k@outlook.com'
    },
    {
        'filename': 'claim_005_standard.pdf',
        'form_date': '30/01/2026',
        'policy_number': 'SBI-GI-KA-2024-45678',
        'carrier': 'SBI General Insurance',
        'policyholder_name': 'Mohammed Irfan Sheikh',
        'effective_dates': '01/09/2024 to 31/08/2025',
        'dob': '20/07/1988',
        'phone': '+91-7760012345',
        'email': 'irfan.sheikh@email.com',
        'loss_date': '27/01/2026',
        'loss_time': '6:30 PM',
        'loss_location': 'Outer Ring Road, Marathahalli junction, Bangalore, Karnataka 560037',
        'description': 'Three-vehicle pile-up during evening rush hour traffic. The insured vehicle rear-ended a stopped car which then hit the vehicle in front. Significant damage to front and rear of the insured vehicle. All parties exchanged information. Traffic police filed a report. No injuries reported.',
        'asset_type': 'Motor Vehicle - SUV',
        'vehicle_make': '2023 Mahindra',
        'vehicle_model': 'XUV700 AX7 - SUV',
        'asset_id': 'MAL1C2BL5P1234567',
        'plate_number': 'KA-05-MR-2345',
        'state': 'Karnataka',
        'damage_description': 'Front bumper cracked, grille broken, bonnet dented, rear bumper damaged, boot lid misaligned',
        'third_party': 'Amit Joshi (front vehicle), Kavya Rao (rear vehicle)',
        'third_party_vehicle': 'Hyundai Creta KA-01-NM-8901 (front), Kia Seltos KA-03-HB-5678 (rear)',
        'third_party_contact': 'Amit: +91-9900012345, Kavya: +91-9845098765',
        'injured_name': '',
        'injury_extent': '',
        'estimated_damage': '28,500',
        'initial_estimate': '28,500',
        'claim_type': 'Auto - Property Damage',
        'attachments': 'Photos (10), Traffic police report, Witness statement',
        'reported_by': 'Mohammed Irfan Sheikh (Self)',
        'claimant': 'Mohammed Irfan Sheikh',
        'contact_details': '+91-7760012345, irfan.sheikh@email.com'
    }
]


def main():
    output_dir = os.path.join(os.path.dirname(__file__), 'sample_fnol')
    os.makedirs(output_dir, exist_ok=True)

    for sample in samples:
        filepath = os.path.join(output_dir, sample['filename'])
        width, height = letter
        c = canvas.Canvas(filepath, pagesize=letter)

        draw_acord_form(c, sample, width, height)
        c.save()
        print(f"  Created: {sample['filename']}")

    print(f"\nAll {len(samples)} sample FNOL documents generated in: {output_dir}")
    print("\nScenarios:")
    print("  1. claim_001_fast_track.pdf      -> ₹8,500 damage, all fields present")
    print("  2. claim_002_manual_review.pdf    -> Missing: effectiveDates, assetId, initialEstimate")
    print("  3. claim_003_investigation.pdf    -> Contains: 'staged', 'inconsistent', 'fraud' keywords")
    print("  4. claim_004_specialist_injury.pdf -> Claim type: Injury - Bodily Injury")
    print("  5. claim_005_standard.pdf         -> ₹28,500 damage (above ₹25,000 threshold)")


if __name__ == '__main__':
    main()