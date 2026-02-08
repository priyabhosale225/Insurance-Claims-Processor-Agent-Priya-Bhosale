"""
Field Validator
Checks for missing mandatory fields and data inconsistencies.
"""
import re
from datetime import datetime


# All mandatory fields that must be present in a valid claim
MANDATORY_FIELDS = {
    "policyInformation": ["policyNumber", "policyholderName", "effectiveDates"],
    "incidentInformation": ["date", "time", "location", "description"],
    "involvedParties": ["claimant", "contactDetails"],
    "assetDetails": ["assetType", "assetId", "estimatedDamage"],
    "otherFields": ["claimType", "initialEstimate"]
}


class FieldValidator:
    """Validates extracted fields for completeness and consistency."""

    def validate(self, extracted_fields: dict) -> tuple:
        """
        Validate extracted fields.
        Returns: (missing_fields: list, inconsistencies: list)
        """
        missing = self._find_missing_fields(extracted_fields)
        inconsistencies = self._find_inconsistencies(extracted_fields)
        return missing, inconsistencies

    def _find_missing_fields(self, fields: dict) -> list:
        """Find all mandatory fields that are missing or empty."""
        missing = []
        for section, required_keys in MANDATORY_FIELDS.items():
            section_data = fields.get(section, {})
            for key in required_keys:
                value = section_data.get(key)
                if value is None or (isinstance(value, str) and value.strip() == ''):
                    missing.append(f"{section}.{key}")
        return missing

    def _find_inconsistencies(self, fields: dict) -> list:
        """Check for logical inconsistencies in the data."""
        issues = []

        # Check if incident date is in the future
        incident_date = fields.get("incidentInformation", {}).get("date")
        if incident_date:
            try:
                for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
                    try:
                        parsed_date = datetime.strptime(incident_date, fmt)
                        if parsed_date > datetime.now():
                            issues.append("Incident date is in the future")
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        # Check if estimated damage is negative or zero
        est_damage = fields.get("assetDetails", {}).get("estimatedDamage")
        if est_damage:
            try:
                damage_val = float(str(est_damage).replace(',', '').replace('₹', '').replace('Rs', '').strip())
                if damage_val < 0:
                    issues.append("Estimated damage amount is negative")
                if damage_val == 0:
                    issues.append("Estimated damage amount is zero")
            except (ValueError, TypeError):
                issues.append("Estimated damage is not a valid number")

        # Check if initial estimate and estimated damage differ significantly
        init_est = fields.get("otherFields", {}).get("initialEstimate")
        if est_damage and init_est:
            try:
                dmg = float(str(est_damage).replace(',', '').replace('₹', '').replace('Rs', '').strip())
                est = float(str(init_est).replace(',', '').replace('₹', '').replace('Rs', '').strip())
                if dmg > 0 and est > 0:
                    diff_ratio = abs(dmg - est) / max(dmg, est)
                    if diff_ratio > 0.5:
                        issues.append(f"Large discrepancy between estimated damage (₹{dmg:,.0f}) and initial estimate (₹{est:,.0f})")
            except (ValueError, TypeError):
                pass

        # Check for valid policy number format (basic check)
        policy_num = fields.get("policyInformation", {}).get("policyNumber")
        if policy_num and len(str(policy_num).strip()) < 3:
            issues.append("Policy number appears too short")

        return issues