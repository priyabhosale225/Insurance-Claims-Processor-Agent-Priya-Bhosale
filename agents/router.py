"""
Claim Router
Routes claims to appropriate workflow based on extraction and validation results.

Priority Order (highest to lowest):
1. Investigation Flag   → Fraud keywords detected in description
2. Specialist Queue     → Claim type is injury-related
3. Manual Review        → Any mandatory field is missing
4. Fast-track           → Damage < ₹25,000 and all fields present
5. Standard Processing  → Default route for everything else
"""

FAST_TRACK_THRESHOLD = 25000  # ₹25,000

FRAUD_KEYWORDS = ["fraud", "fraudulent", "inconsistent", "staged", "suspicious", "fake", "fabricated"]

INJURY_KEYWORDS = ["injury", "bodily injury", "personal injury", "medical", "hospitalization",
                    "hospital", "death", "fatality", "wounded"]


class ClaimRouter:
    """Routes insurance claims to the appropriate processing workflow."""

    def route(self, extracted_fields: dict, missing_fields: list) -> tuple:
        """
        Determine the routing for a claim.
        Returns: (route_name: str, reasoning: str)
        """
        reasons = []

        # --- PRIORITY 1: Investigation Flag ---
        description = (extracted_fields.get("incidentInformation", {}).get("description") or "").lower()
        fraud_found = [kw for kw in FRAUD_KEYWORDS if kw in description]
        if fraud_found:
            reasons.append(f"Description contains fraud-related keywords: {', '.join(fraud_found)}")
            return "Investigation Flag", ". ".join(reasons)

        # --- PRIORITY 2: Specialist Queue ---
        claim_type = (extracted_fields.get("otherFields", {}).get("claimType") or "").lower()
        desc_lower = description.lower()

        injury_in_type = any(kw in claim_type for kw in INJURY_KEYWORDS)
        injury_in_desc = any(kw in desc_lower for kw in INJURY_KEYWORDS)

        if injury_in_type or injury_in_desc:
            where = "claim type" if injury_in_type else "description"
            reasons.append(f"Injury-related claim detected in {where}")
            return "Specialist Queue", ". ".join(reasons)

        # --- PRIORITY 3: Manual Review ---
        if missing_fields:
            field_names = [f.split('.')[-1] for f in missing_fields]
            reasons.append(f"Missing mandatory fields: {', '.join(field_names)} ({len(missing_fields)} field(s))")
            return "Manual Review", ". ".join(reasons)

        # --- PRIORITY 4: Fast-track ---
        est_damage = extracted_fields.get("assetDetails", {}).get("estimatedDamage")
        if est_damage:
            try:
                damage_val = float(str(est_damage).replace(',', '').replace('₹', '').replace('Rs', '').strip())
                if damage_val < FAST_TRACK_THRESHOLD:
                    reasons.append(f"Estimated damage ₹{damage_val:,.0f} is below fast-track threshold of ₹{FAST_TRACK_THRESHOLD:,}")
                    reasons.append("All mandatory fields are present")
                    return "Fast-track", ". ".join(reasons)
                else:
                    reasons.append(f"Estimated damage ₹{damage_val:,.0f} exceeds fast-track threshold of ₹{FAST_TRACK_THRESHOLD:,}")
                    reasons.append("All mandatory fields are present. Routed to standard processing")
                    return "Standard Processing", ". ".join(reasons)
            except (ValueError, TypeError):
                reasons.append("Could not parse estimated damage amount. Routing to standard processing")
                return "Standard Processing", ". ".join(reasons)

        # --- PRIORITY 5: Standard Processing (default) ---
        reasons.append("All mandatory fields present. No special conditions detected")
        return "Standard Processing", ". ".join(reasons)