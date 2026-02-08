"""
LLM-based Field Extraction using OpenAI GPT-4o-mini.
Falls back to regex-based extraction if OpenAI API key is not configured.
Regex patterns are tuned for ACORD Automobile Loss Notice form format.
"""
import os
import re
import json


def get_empty_fields():
    """Default empty structure for extracted fields."""
    return {
        "policyInformation": {
            "policyNumber": None,
            "policyholderName": None,
            "effectiveDates": None
        },
        "incidentInformation": {
            "date": None,
            "time": None,
            "location": None,
            "description": None
        },
        "involvedParties": {
            "claimant": None,
            "thirdParties": None,
            "contactDetails": None
        },
        "assetDetails": {
            "assetType": None,
            "assetId": None,
            "estimatedDamage": None
        },
        "otherFields": {
            "claimType": None,
            "attachments": None,
            "initialEstimate": None
        }
    }


class LLMProcessor:
    """Extracts structured fields from raw text using OpenAI or regex fallback."""

    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY', '')

    def extract_fields(self, raw_text: str) -> dict:
        """Main extraction method. Uses OpenAI if available, else regex."""
        if self.api_key:
            try:
                return self._extract_with_openai(raw_text)
            except Exception as e:
                print(f"OpenAI extraction failed: {e}, falling back to regex")
                return self._extract_with_regex(raw_text)
        else:
            print("No OpenAI API key found. Using regex-based extraction.")
            return self._extract_with_regex(raw_text)

    def _extract_with_openai(self, raw_text: str) -> dict:
        """Extract fields using OpenAI GPT-4o-mini."""
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)

        system_prompt = """You are an expert insurance claims data extractor. 
Given raw text from an FNOL (First Notice of Loss) document, extract the following fields into a JSON structure.
If a field is not found or not mentioned, set its value to null.
For monetary values, extract just the number (no currency symbols). All amounts are in Indian Rupees (INR).

Return ONLY valid JSON in this exact structure:
{
    "policyInformation": {
        "policyNumber": "string or null",
        "policyholderName": "string or null",
        "effectiveDates": "string or null"
    },
    "incidentInformation": {
        "date": "string or null",
        "time": "string or null",
        "location": "string or null",
        "description": "string or null"
    },
    "involvedParties": {
        "claimant": "string or null",
        "thirdParties": "string or null",
        "contactDetails": "string or null"
    },
    "assetDetails": {
        "assetType": "string or null",
        "assetId": "string or null",
        "estimatedDamage": "string or null"
    },
    "otherFields": {
        "claimType": "string or null",
        "attachments": "string or null",
        "initialEstimate": "string or null"
    }
}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract fields from this FNOL document:\n\n{raw_text[:4000]}"}
            ],
            temperature=0.1,
            max_tokens=1500
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)

        parsed = json.loads(result_text)
        base = get_empty_fields()
        for section in base:
            if section in parsed:
                for field in base[section]:
                    if field in parsed[section]:
                        base[section][field] = parsed[section][field]
        return base

    def _extract_with_regex(self, raw_text: str) -> dict:
        """
        Fallback: Extract fields using regex pattern matching.
        Patterns are tuned for ACORD-style form layout where:
        - Labels appear on one line
        - Values appear on the next line
        - Two fields often share the same label/value pair of lines
        """
        fields = get_empty_fields()
        text = raw_text

        # =============================================
        # POLICY INFORMATION
        # =============================================

        # Policy Number: "POLICY NUMBER CARRIER\nVALUE ..."
        m = re.search(r'POLICY\s*NUMBER.*?\n([A-Z0-9][A-Z0-9\-\/]+)', text, re.IGNORECASE)
        if m:
            fields["policyInformation"]["policyNumber"] = m.group(1).strip()
        else:
            m = re.search(r'Policy\s*(?:Number|No\.?|#)[:\s]*([A-Z0-9\-\/]+)', text, re.IGNORECASE)
            if m:
                fields["policyInformation"]["policyNumber"] = m.group(1).strip()

        # Policyholder Name + Effective Dates
        # Format: "POLICYHOLDER NAME... EFFECTIVE DATES\nRajesh Kumar Sharma 01/04/2025 to 31/03/2026"
        m = re.search(r'POLICYHOLDER\s*NAME.*?\n(.+)', text, re.IGNORECASE)
        if m:
            line = m.group(1).strip()
            date_match = re.search(r'(\d{2}/\d{2}/\d{4}\s*to\s*\d{2}/\d{2}/\d{4})', line)
            if date_match:
                name = line[:date_match.start()].strip()
                fields["policyInformation"]["effectiveDates"] = date_match.group(1).strip()
            else:
                name = line.strip()
            if name and len(name) > 2:
                fields["policyInformation"]["policyholderName"] = name
        else:
            # Fallback patterns
            for pat in [r'(?:Policyholder|Insured)\s*(?:Name)?[:\s]+([A-Za-z][\w\s\.]+?)(?:\n|$)',
                        r'Name\s*of\s*Insured[:\s]+([A-Za-z][\w\s\.]+?)(?:\n|$)']:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    fields["policyInformation"]["policyholderName"] = m.group(1).strip()
                    break

        # Effective Dates fallback
        if not fields["policyInformation"]["effectiveDates"]:
            m = re.search(r'(\d{2}/\d{2}/\d{4}\s*to\s*\d{2}/\d{2}/\d{4})', text)
            if m:
                fields["policyInformation"]["effectiveDates"] = m.group(1).strip()

        # =============================================
        # INCIDENT INFORMATION
        # =============================================

        # Date and Time of Loss
        # Format: "DATE OF LOSS (DD/MM/YYYY) TIME OF LOSS\n01/02/2026 10:30 AM"
        m = re.search(r'DATE\s*OF\s*LOSS.*?\n(\d{2}/\d{2}/\d{4})\s+([\d:]+\s*[AP]M)', text, re.IGNORECASE)
        if m:
            fields["incidentInformation"]["date"] = m.group(1).strip()
            fields["incidentInformation"]["time"] = m.group(2).strip()
        else:
            # Try separate patterns
            m = re.search(r'DATE\s*OF\s*LOSS.*?\n(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
            if m:
                fields["incidentInformation"]["date"] = m.group(1).strip()
            else:
                m = re.search(r'(?:Date\s*of\s*(?:Loss|Incident))[:\s]*([\d/\-]+)', text, re.IGNORECASE)
                if m:
                    fields["incidentInformation"]["date"] = m.group(1).strip()

            m = re.search(r'([\d]{1,2}:[\d]{2}\s*[AP]M)', text, re.IGNORECASE)
            if m and not fields["incidentInformation"]["time"]:
                fields["incidentInformation"]["time"] = m.group(1).strip()

        # Location
        m = re.search(r'LOCATION\s*OF\s*LOSS\n(.+)', text, re.IGNORECASE)
        if m:
            fields["incidentInformation"]["location"] = m.group(1).strip()
        else:
            m = re.search(r'Location[:\s]+(.+?)(?:\n|$)', text, re.IGNORECASE)
            if m:
                fields["incidentInformation"]["location"] = m.group(1).strip()

        # Description
        m = re.search(r'DESCRIPTION\s*OF\s*ACCIDENT\n([\s\S]+?)(?=\nINSURED\s+VEHICLE|\nASSET|\n[A-Z]{4,}\s+VEHICLE)', text, re.IGNORECASE)
        if m:
            desc = ' '.join(m.group(1).strip().split())
            fields["incidentInformation"]["description"] = desc
        else:
            m = re.search(r'Description[:\s]+(.+?)(?:\n[A-Z]|\Z)', text, re.IGNORECASE | re.DOTALL)
            if m:
                fields["incidentInformation"]["description"] = ' '.join(m.group(1).strip().split())

        # =============================================
        # INVOLVED PARTIES
        # =============================================

        # Claimant = reported by or policyholder
        m = re.search(r'REPORTED\s*BY\s+DATE\s*REPORTED\n(.+)', text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            # Remove date part and "(Self)"
            name = re.sub(r'\d{2}/\d{2}/\d{4}', '', name).strip()
            name = re.sub(r'\(.*?\)', '', name).strip()
            if name and len(name) > 2:
                fields["involvedParties"]["claimant"] = name
        if not fields["involvedParties"]["claimant"]:
            fields["involvedParties"]["claimant"] = fields["policyInformation"]["policyholderName"]

        # Third Parties
        m = re.search(r'THIRD\s*PARTY\s*NAME.*?\n(.+)', text, re.IGNORECASE)
        if m:
            line = m.group(1).strip()
            if line.lower() not in ['none', 'n/a', 'na', '', 'none - single vehicle accident']:
                fields["involvedParties"]["thirdParties"] = line
            elif 'none' in line.lower() or 'n/a' in line.lower():
                fields["involvedParties"]["thirdParties"] = line  # Still store it

        # Contact Details
        contacts = []
        m = re.search(r'CONTACT\s*PHONE\n(.+)', text, re.IGNORECASE)
        if m:
            contacts.append(m.group(1).strip())
        m = re.search(r'EMAIL\s*ADDRESS\n([\w.\-]+@[\w.\-]+\.\w+)', text, re.IGNORECASE)
        if m:
            contacts.append(m.group(1).strip())
        if not contacts:
            phones = re.findall(r'(\+91[\-\s]?\d[\d\-\s]{8,})', text)
            if phones:
                contacts.append(phones[0].strip())
            emails = re.findall(r'([\w.\-]+@[\w.\-]+\.\w+)', text)
            if emails:
                contacts.append(emails[0])
        if contacts:
            fields["involvedParties"]["contactDetails"] = ", ".join(contacts)

        # =============================================
        # ASSET DETAILS
        # =============================================

        # Asset Type
        m = re.search(r'ASSET\s*TYPE.*?\n(.+)', text, re.IGNORECASE)
        if m:
            line = m.group(1).strip()
            parts = re.split(r'\s{2,}', line)
            if parts:
                fields["assetDetails"]["assetType"] = parts[0].strip()

        # Asset ID / VIN
        m = re.search(r'(?:V\.?I\.?N\.?\s*/?\s*ASSET\s*ID|ASSET\s*ID).*?\n(.+)', text, re.IGNORECASE)
        if m:
            line = m.group(1).strip()
            vin = re.search(r'([A-Z0-9]{10,})', line)
            if vin:
                fields["assetDetails"]["assetId"] = vin.group(1).strip()
        if not fields["assetDetails"]["assetId"]:
            # Try finding VIN pattern in MODEL line
            m = re.search(r'MODEL.*?\n.*?([A-Z0-9]{10,})', text, re.IGNORECASE)
            if m:
                fields["assetDetails"]["assetId"] = m.group(1).strip()

        # Estimated Damage + Initial Estimate
        # Format: "ESTIMATED DAMAGE (INR) INITIAL ESTIMATE (INR)\n8,500 8,500"
        m = re.search(r'ESTIMATED\s*DAMAGE\s*\(INR\).*?\n([\d,]+)(?:\s+([\d,]+))?', text, re.IGNORECASE)
        if m:
            fields["assetDetails"]["estimatedDamage"] = m.group(1).strip().replace(',', '')
            if m.group(2):
                fields["otherFields"]["initialEstimate"] = m.group(2).strip().replace(',', '')
        else:
            m = re.search(r'(?:Estimated\s*Damage|Damage\s*Amount)[:\s]*(?:₹|Rs\.?|INR)?\s*([\d,]+)', text, re.IGNORECASE)
            if m:
                fields["assetDetails"]["estimatedDamage"] = m.group(1).strip().replace(',', '')

        # =============================================
        # OTHER FIELDS
        # =============================================

        # Claim Type + Attachments
        # Format: "CLAIM TYPE ATTACHMENTS\nAuto - Property Damage Photos (3), Police spot report"
        m = re.search(r'CLAIM\s*TYPE\s+ATTACHMENTS\n(.+)', text, re.IGNORECASE)
        if m:
            line = m.group(1).strip()
            # Try splitting on well-known attachment patterns
            attach_match = re.search(r'((?:Photos?|Documents?|FIR|Report|Receipt|Hospital|Records?)[\s\S]*)', line, re.IGNORECASE)
            if attach_match:
                ct = line[:attach_match.start()].strip().rstrip('-').strip()
                att = attach_match.group(1).strip()
                if ct:
                    fields["otherFields"]["claimType"] = ct
                if att:
                    fields["otherFields"]["attachments"] = att
            else:
                # Try splitting by multiple spaces
                parts = re.split(r'\s{2,}', line)
                if parts:
                    fields["otherFields"]["claimType"] = parts[0].strip()
                if len(parts) > 1:
                    fields["otherFields"]["attachments"] = parts[1].strip()
        else:
            m = re.search(r'CLAIM\s*TYPE.*?\n(.+)', text, re.IGNORECASE)
            if m:
                fields["otherFields"]["claimType"] = m.group(1).strip()
            m = re.search(r'ATTACHMENTS.*?\n(.+)', text, re.IGNORECASE)
            if m:
                fields["otherFields"]["attachments"] = m.group(1).strip()

        # Initial Estimate fallback
        if not fields["otherFields"]["initialEstimate"]:
            m = re.search(r'INITIAL\s*ESTIMATE.*?\n.*?([\d,]+)', text, re.IGNORECASE)
            if m:
                fields["otherFields"]["initialEstimate"] = m.group(1).strip().replace(',', '')
            elif fields["assetDetails"]["estimatedDamage"]:
                # If we have estimated damage but no initial estimate, don't assume
                pass

        return fields