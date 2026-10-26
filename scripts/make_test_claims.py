"""Generate synthetic test claims under data/sample_claims/.

Run from the project root:

    venv/bin/python -m scripts.make_test_claims

Each scenario starts from one fact sheet (BASE) and overrides only the
facts it is testing, so every document in a claim agrees unless the
scenario deliberately introduces a mismatch. Every claim folder gets
the PDFs plus claim.json (the online claim form and the expected
outcome) for tests/run_test_claims.py.
"""

import json
from html import escape
from pathlib import Path

import pymupdf


OUTPUT_DIRECTORY = Path("data/sample_claims")

BANNER = "SYNTHETIC TEST DOCUMENT - FOR CLAIMFILE SOFTWARE TESTING ONLY"

INSURER = "TrustGuard General Insurance Co. Ltd."


BASE = {
    "policy_number": "TEST-POL-0000000000",
    "policy_period": "01/04/2026 (00:00 Hrs) to 31/03/2027 (Midnight)",
    "insured_name": "Test Person",
    "address": "No. 1, Test Street, Chennai, Tamil Nadu - 600001",
    "registration": "TN 01 AA 0000",
    "rc_registration": None,
    "make": "Maruti",
    "model": "Swift",
    "year": "2022",
    "fuel": "Petrol",
    "cc": "1197 cc",
    "idv": "Rs. 4,00,000",
    "compulsory_deductible": "Rs. 1,000 per claim",
    "voluntary_deductible": "NIL",
    "add_ons": [],
    "licence_number": "TEST-TN01-20150000000",
    "licence_issue": "10/01/2015",
    "licence_expiry": "09/01/2035",
    "licence_classes": "LMV (Light Motor Vehicle), MCWG",
    "driver_name": None,
    "accident_date": "10/07/2026",
    "accident_time": "17:30",
    "accident_location": "Anna Salai, Chennai, Tamil Nadu",
    "accident_description": "",
    "cause": "",
    "third_party": False,
    "third_party_details": "No / Nil",
    "fir": "No FIR filed",
    "driver_condition": "Driver alert and cooperative; no intoxication observed.",
    "damage_rows": [],
    "estimate_rows": [],
    "documents": [
        "policy_schedule",
        "vehicle_registration",
        "driving_license",
        "damage_survey_report",
        "repair_estimate",
    ],
}


SCENARIOS = {
    "claim_002_rear_end_third_party": {
        "purpose": (
            "Clean claim with a different car, city and a third party "
            "involved. Should reach human approval."
        ),
        "expected_status": ["human_approval"],
        "policy_number": "TEST-POL-4410556721",
        "insured_name": "Priya Ramesh Sharma",
        "address": "Flat 3B, Lakeview Residency, HSR Layout, Bengaluru - 560102",
        "registration": "KA 01 MK 2231",
        "make": "Hyundai",
        "model": "i20",
        "year": "2023",
        "cc": "1197 cc",
        "idv": "Rs. 6,20,000",
        "add_ons": ["TA01 - Depreciation Reimbursement"],
        "licence_number": "TEST-KA01-20170045678",
        "licence_issue": "22/05/2017",
        "licence_expiry": "21/05/2037",
        "accident_date": "02/08/2026",
        "accident_time": "09:10",
        "accident_location": "Outer Ring Road, Marathahalli, Bengaluru",
        "accident_description": (
            "While stationary at a red traffic signal, my car was hit "
            "from behind by another car."
        ),
        "cause": (
            "Insured vehicle was stationary at a red signal when a "
            "third-party car (KA 03 HJ 9087) failed to brake and struck "
            "the rear of the insured vehicle."
        ),
        "third_party": True,
        "third_party_details": (
            "Yes - third-party vehicle KA 03 HJ 9087; no injuries"
        ),
        "fir": (
            "FIR No. TEST-FIR-118/2026, Marathahalli Traffic Police "
            "Station, dated 02/08/2026"
        ),
        "damage_rows": [
            ("Rear Bumper", "Cracked and pushed in at centre", "Replace"),
            ("Boot Lid (Tailgate)", "Dented, lock misaligned", "Repair"),
            ("Right Tail Lamp", "Lens shattered", "Replace"),
        ],
        "estimate_rows": [
            ("Rear bumper replacement", "Spare Part", "9,400.00"),
            ("Boot lid denting and alignment", "Labour", "6,200.00"),
            ("Right tail lamp assembly", "Spare Part", "5,850.00"),
            ("Painting and refinishing", "Labour & Paint", "7,550.00"),
        ],
    },
    "claim_003_expired_licence": {
        "purpose": (
            "Driving licence expired before the accident. Licence check "
            "is deterministic, so the claim must not be approved."
        ),
        "expected_status": ["complete", "terminated", "needs_internal_review"],
        "expected_review": ["REJECTED", "NEEDS_INVESTIGATION"],
        "policy_number": "TEST-POL-7720193345",
        "insured_name": "Rahul Anand Verma",
        "address": "B-14, Sector 22, Noida, Uttar Pradesh - 201301",
        "registration": "UP 16 CK 4410",
        "make": "Honda",
        "model": "City",
        "year": "2021",
        "cc": "1498 cc",
        "idv": "Rs. 7,10,000",
        "licence_number": "TEST-UP16-20060011223",
        "licence_issue": "11/01/2006",
        "licence_expiry": "10/01/2026",
        "accident_date": "05/07/2026",
        "accident_time": "21:15",
        "accident_location": "Sector 18 Market Road, Noida",
        "accident_description": (
            "Car hit a roadside pole while reversing out of a parking spot."
        ),
        "cause": (
            "While reversing out of a parking space at night, the insured "
            "vehicle struck a metal roadside lamp pole."
        ),
        "damage_rows": [
            ("Rear Bumper", "Cracked on left side", "Replace"),
            ("Left Rear Quarter Panel", "Dented", "Repair"),
        ],
        "estimate_rows": [
            ("Rear bumper replacement", "Spare Part", "8,900.00"),
            ("Quarter panel denting", "Labour", "4,600.00"),
            ("Painting and refinishing", "Labour & Paint", "5,500.00"),
        ],
    },
    "claim_004_outside_policy_period": {
        "purpose": (
            "Accident happened after the policy expired. Policy validity "
            "is deterministic, so the claim must not be approved."
        ),
        "expected_status": ["complete", "terminated", "needs_internal_review"],
        "expected_review": ["REJECTED", "NEEDS_INVESTIGATION"],
        "policy_number": "TEST-POL-3302981176",
        "policy_period": "01/01/2025 (00:00 Hrs) to 31/12/2025 (Midnight)",
        "insured_name": "Ananya Iyer",
        "address": "12, Second Main Road, Adyar, Chennai - 600020",
        "registration": "TN 07 CQ 5512",
        "make": "Tata",
        "model": "Nexon",
        "year": "2022",
        "cc": "1199 cc",
        "idv": "Rs. 7,40,000",
        "licence_number": "TEST-TN07-20180067890",
        "licence_issue": "03/03/2018",
        "licence_expiry": "02/03/2038",
        "accident_date": "20/02/2026",
        "accident_time": "13:40",
        "accident_location": "East Coast Road, Chennai",
        "accident_description": (
            "Car skidded on loose gravel and hit a road divider."
        ),
        "cause": (
            "Vehicle skidded on loose gravel at a bend and its front left "
            "side struck a concrete divider."
        ),
        "damage_rows": [
            ("Front Bumper", "Torn at left corner", "Replace"),
            ("Left Fender", "Crumpled", "Replace"),
            ("Left Fog Lamp", "Broken", "Replace"),
        ],
        "estimate_rows": [
            ("Front bumper replacement", "Spare Part", "11,200.00"),
            ("Left fender replacement", "Spare Part", "7,800.00"),
            ("Fog lamp assembly", "Spare Part", "2,400.00"),
            ("Labour and painting", "Labour & Paint", "9,600.00"),
        ],
    },
    "claim_005_drunk_driving": {
        "purpose": (
            "Survey and FIR record the driver as intoxicated. Tests that "
            "RAG retrieves the General Exceptions intoxication exclusion."
        ),
        "expected_status": ["complete", "terminated"],
        "expected_review": ["REJECTED"],
        "policy_number": "TEST-POL-5581027734",
        "insured_name": "Vikram Singh Rathore",
        "address": "45, Civil Lines, Jaipur, Rajasthan - 302006",
        "registration": "RJ 14 CV 7781",
        "make": "Mahindra",
        "model": "XUV300",
        "year": "2023",
        "cc": "1197 cc",
        "idv": "Rs. 9,10,000",
        "licence_number": "TEST-RJ14-20120033445",
        "licence_issue": "14/06/2012",
        "licence_expiry": "13/06/2032",
        "accident_date": "16/08/2026",
        "accident_time": "23:50",
        "accident_location": "Tonk Road, Jaipur, Rajasthan",
        "accident_description": (
            "Car went off the road and hit a tree late at night."
        ),
        "cause": (
            "Vehicle left the carriageway at speed and struck a roadside "
            "tree. The police breath analyser test recorded a blood "
            "alcohol concentration of 0.11% for the driver, above the "
            "legal limit of 0.03%."
        ),
        "fir": (
            "FIR No. TEST-FIR-342/2026, Tonk Road Police Station, "
            "dated 17/08/2026, registered for drunk driving"
        ),
        "driver_condition": (
            "Driver found under the influence of alcohol at the scene "
            "(breath analyser 0.11% BAC, per FIR)."
        ),
        "damage_rows": [
            ("Front Bumper", "Destroyed", "Replace"),
            ("Bonnet", "Folded and buckled", "Replace"),
            ("Radiator", "Punctured, coolant leak", "Replace"),
            ("Windshield", "Cracked across", "Replace"),
        ],
        "estimate_rows": [
            ("Front bumper replacement", "Spare Part", "14,500.00"),
            ("Bonnet replacement", "Spare Part", "18,200.00"),
            ("Radiator replacement", "Spare Part", "12,800.00"),
            ("Windshield replacement", "Spare Part", "15,600.00"),
            ("Labour and painting", "Labour & Paint", "16,900.00"),
        ],
    },
    "claim_006_registration_mismatch": {
        "purpose": (
            "Registration certificate shows a different number from the "
            "claim form and schedule. Should be flagged, not approved."
        ),
        "expected_status": ["needs_internal_review", "waiting_for_documents"],
        "expected_review": ["NEEDS_INVESTIGATION"],
        "policy_number": "TEST-POL-6603318820",
        "insured_name": "Meera Krishnan Nair",
        "address": "TC 9/1123, Sasthamangalam, Thiruvananthapuram - 695010",
        "registration": "KL 01 BT 6634",
        "rc_registration": "KL 01 BT 6684",
        "make": "Toyota",
        "model": "Glanza",
        "year": "2022",
        "cc": "1197 cc",
        "idv": "Rs. 5,90,000",
        "licence_number": "TEST-KL01-20160077889",
        "licence_issue": "19/09/2016",
        "licence_expiry": "18/09/2036",
        "accident_date": "28/07/2026",
        "accident_time": "11:20",
        "accident_location": "MC Road, Thiruvananthapuram, Kerala",
        "accident_description": (
            "Scraped the left side of the car against a wall while "
            "turning into a narrow lane."
        ),
        "cause": (
            "While turning into a narrow lane, the left side of the "
            "insured vehicle scraped along a compound wall."
        ),
        "damage_rows": [
            ("Left Front Door", "Deep scratches and dent", "Repair"),
            ("Left Rear Door", "Scratches", "Repair"),
            ("Left ORVM", "Housing cracked", "Replace"),
        ],
        "estimate_rows": [
            ("Left doors denting and painting", "Labour & Paint", "12,400.00"),
            ("Left ORVM assembly", "Spare Part", "3,900.00"),
        ],
    },
    "claim_007_missing_survey_report": {
        "purpose": (
            "Damage survey report not uploaded. The claim should wait "
            "for that document before any investigation."
        ),
        "expected_status": ["waiting_for_documents"],
        "expected_pending": ["damage_survey_report"],
        "policy_number": "TEST-POL-8812204459",
        "insured_name": "Arjun Mehta",
        "address": "402, Sunrise Towers, Andheri West, Mumbai - 400053",
        "registration": "MH 02 FG 3390",
        "make": "Kia",
        "model": "Sonet",
        "year": "2024",
        "cc": "998 cc",
        "idv": "Rs. 9,60,000",
        "licence_number": "TEST-MH02-20190012121",
        "licence_issue": "07/07/2019",
        "licence_expiry": "06/07/2039",
        "accident_date": "09/08/2026",
        "accident_time": "19:05",
        "accident_location": "Link Road, Andheri West, Mumbai",
        "accident_description": (
            "A motorcycle brushed against my car door in slow traffic."
        ),
        "cause": "Motorcycle brushed the right side of the vehicle.",
        "damage_rows": [
            ("Right Front Door", "Scratched", "Repair"),
        ],
        "estimate_rows": [
            ("Right door painting", "Labour & Paint", "6,500.00"),
        ],
        "documents": [
            "policy_schedule",
            "vehicle_registration",
            "driving_license",
            "repair_estimate",
        ],
    },
    "claim_008_flood_damage": {
        "purpose": (
            "Non-collision peril (flood). Tests that RAG retrieves the "
            "flood/inundation peril and engine-related exclusions. "
            "Exploratory: any final status is accepted."
        ),
        "expected_status": None,
        "policy_number": "TEST-POL-9905517702",
        "insured_name": "Sanjay Kumar Reddy",
        "address": "8-2-293, Road No. 12, Banjara Hills, Hyderabad - 500034",
        "registration": "TS 09 EZ 1145",
        "make": "Hyundai",
        "model": "Creta",
        "year": "2023",
        "cc": "1497 cc",
        "idv": "Rs. 12,40,000",
        "licence_number": "TEST-TS09-20110054321",
        "licence_issue": "25/11/2011",
        "licence_expiry": "24/11/2031",
        "accident_date": "21/08/2026",
        "accident_time": "06:30",
        "accident_location": "Banjara Hills, Hyderabad, Telangana",
        "accident_description": (
            "Heavy rain flooded the street overnight and my parked car "
            "was submerged up to the dashboard."
        ),
        "cause": (
            "The vehicle was parked on the street when overnight "
            "cloudburst rainfall caused flooding. Water rose to dashboard "
            "level. Vehicle was not started after the flood and was towed "
            "to the workshop."
        ),
        "damage_rows": [
            ("Interior Upholstery and Carpets", "Water-soaked, silt deposits", "Replace"),
            ("Engine Control Unit (ECU)", "Water ingress, not powering on", "Replace"),
            ("Wiring Harness (Floor)", "Corroded connectors", "Repair"),
        ],
        "estimate_rows": [
            ("Interior cleaning and carpet replacement", "Spare Part", "18,500.00"),
            ("ECU replacement", "Spare Part", "42,000.00"),
            ("Wiring harness repair", "Labour", "9,800.00"),
            ("Engine oil and filter flush", "Labour", "4,700.00"),
        ],
    },
}


def scenario_facts(overrides: dict) -> dict:
    facts = {**BASE, **overrides}

    facts["driver_name"] = facts["driver_name"] or facts["insured_name"]
    facts["rc_registration"] = (
        facts["rc_registration"] or facts["registration"]
    )

    return facts


def table(rows: list[tuple[str, str]]) -> str:
    cells = "".join(
        f"<tr><td><b>{escape(label)}</b></td><td>{escape(value)}</td></tr>"
        for label, value in rows
    )

    return f"<table>{cells}</table>"


def grid(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    head = "".join(f"<th>{escape(cell)}</th>" for cell in header)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )

    return f"<table><tr>{head}</tr>{body}</table>"


def page_html(title: str, sections: list[tuple[str, str]]) -> str:
    body = "".join(
        f"<h3>{escape(heading)}</h3>{content}"
        for heading, content in sections
    )

    return (
        f"<p><i>{BANNER}</i></p>"
        f"<h2>{escape(title)}</h2>"
        f"{body}"
    )


def write_pdf(path: Path, html: str) -> None:
    css = (
        "* {font-family: sans-serif; font-size: 10pt;}"
        "h2 {font-size: 14pt;} h3 {font-size: 11pt;}"
        "td, th {border: 0.5px solid #999; padding: 3px;}"
        "table {border-collapse: collapse; width: 100%;}"
    )

    story = pymupdf.Story(html=html, user_css=css)
    writer = pymupdf.DocumentWriter(str(path))
    mediabox = pymupdf.paper_rect("a4")
    where = mediabox + (40, 40, -40, -40)

    more = True

    while more:
        device = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(device)
        writer.end_page()

    writer.close()


def policy_schedule(f: dict) -> str:
    add_ons = f["add_ons"] or ["None opted"]

    return page_html(
        f"{INSURER} - Private Car Package Policy Schedule",
        [
            ("1. Policy Summary", table([
                ("Policy Number", f["policy_number"]),
                ("Policy Period", f["policy_period"]),
                ("Policy Status", "ISSUED"),
            ])),
            ("2. Insured Details", table([
                ("Insured Name", f["insured_name"]),
                ("Address", f["address"]),
            ])),
            ("3. Vehicle Schedule", table([
                ("Registration Number", f["registration"]),
                ("Make", f["make"]),
                ("Model", f["model"]),
                ("Year of Manufacture", f["year"]),
                ("Fuel Type", f["fuel"]),
                ("Cubic Capacity", f["cc"]),
                ("Vehicle Class", "Private Car (LMV)"),
                ("Insured Declared Value (IDV)", f["idv"]),
            ])),
            ("4. Deductibles and Limits", table([
                ("Compulsory Deductible (IMT-22)", f["compulsory_deductible"]),
                ("Voluntary Deductible", f["voluntary_deductible"]),
                ("Third Party Property Damage Limit", "Rs. 7,50,000"),
            ])),
            ("5. Add-On Covers Included", table([
                ("Add-on", add_on) for add_on in add_ons
            ])),
        ],
    )


def vehicle_registration(f: dict) -> str:
    return page_html(
        "Vehicle Registration Record",
        [
            ("1. Registration and Ownership", table([
                ("Registration Number", f["rc_registration"]),
                ("Registered Owner", f["insured_name"]),
                ("Owner Address", f["address"]),
                ("Registration Status", "ACTIVE / VALID"),
            ])),
            ("2. Vehicle Specifications", table([
                ("Make", f["make"]),
                ("Model", f["model"]),
                ("Vehicle Type", "Private Car"),
                ("Fuel Type", f["fuel"]),
                ("Manufacturing Year", f["year"]),
            ])),
        ],
    )


def driving_license(f: dict) -> str:
    return page_html(
        "Driver Licence Record",
        [
            ("1. Licence Holder", table([
                ("Licence Number", f["licence_number"]),
                ("Full Name", f["driver_name"]),
                ("Address", f["address"]),
                ("Original Issue Date", f["licence_issue"]),
                ("Current Expiry Date", f["licence_expiry"]),
            ])),
            ("2. Authorized Vehicle Classes", table([
                ("Classes", f["licence_classes"]),
            ])),
        ],
    )


def damage_survey_report(f: dict) -> str:
    return page_html(
        "Motor Damage Survey Report",
        [
            ("1. Policy and Claim Identification", table([
                ("Insurer", INSURER),
                ("Policy Number", f["policy_number"]),
                ("Insured Name", f["insured_name"]),
                ("Policy Period", f["policy_period"]),
                ("Insured Declared Value", f["idv"]),
            ])),
            ("2. Vehicle Particulars", table([
                ("Registration Number", f["registration"]),
                ("Make and Model", f"{f['make']} {f['model']}"),
                ("Year of Manufacture", f["year"]),
            ])),
            ("3. Driver at Time of Accident", table([
                ("Driver Name", f["driver_name"]),
                ("Driving Licence No.", f["licence_number"]),
                ("Licence Expiry Date", f["licence_expiry"]),
                ("Driver Condition", f["driver_condition"]),
            ])),
            ("4. Incident Circumstances", table([
                (
                    "Accident Date and Time",
                    f"{f['accident_date']} at {f['accident_time']} Hrs",
                ),
                ("Accident Location", f["accident_location"]),
                ("Cause of Accident", f["cause"]),
                ("Third Party Injury / Damage", f["third_party_details"]),
                ("Police Report / FIR", f["fir"]),
            ])),
            ("5. Inspection Findings", grid(
                ("Component", "Observed Damage", "Recommended Action"),
                f["damage_rows"],
            )),
        ],
    )


def repair_estimate(f: dict) -> str:
    total = sum(
        float(amount.replace(",", ""))
        for _, _, amount in f["estimate_rows"]
    )

    return page_html(
        "Motor Vehicle Repair Estimate",
        [
            ("Estimate Details", table([
                ("Customer Name", f["insured_name"]),
                ("Vehicle Registration", f["registration"]),
                ("Vehicle Make/Model", f"{f['make']} {f['model']}"),
                ("Accident Date", f["accident_date"]),
                ("Policy Number", f["policy_number"]),
            ])),
            ("Repair Items", grid(
                ("Description", "Category", "Amount (Rs.)"),
                f["estimate_rows"],
            )),
            ("Total", table([
                ("TOTAL ESTIMATED REPAIR COST", f"Rs. {total:,.2f}"),
            ])),
        ],
    )


RENDERERS = {
    "policy_schedule": policy_schedule,
    "vehicle_registration": vehicle_registration,
    "driving_license": driving_license,
    "damage_survey_report": damage_survey_report,
    "repair_estimate": repair_estimate,
}


def claim_form(f: dict) -> dict:
    total = sum(
        float(amount.replace(",", ""))
        for _, _, amount in f["estimate_rows"]
    )

    return {
        "policy_number": f["policy_number"],
        "insured_name": f["insured_name"],
        "vehicle_registration_number": f["registration"],
        "vehicle_make": f["make"],
        "vehicle_model": f["model"],
        "accident_date": f["accident_date"],
        "accident_time": f["accident_time"],
        "accident_location": f["accident_location"],
        "accident_description": f["accident_description"],
        "driver_name": f["driver_name"],
        "driver_license_number": f["licence_number"],
        "damage_description": ", ".join(
            component for component, _, _ in f["damage_rows"]
        ) + " damaged.",
        "third_party_involved": f["third_party"],
        "additional_information": {
            "estimated_repair_cost": f"{total:.0f}",
        },
    }


def build_claim(name: str, overrides: dict) -> None:
    facts = scenario_facts(overrides)
    directory = OUTPUT_DIRECTORY / name
    directory.mkdir(parents=True, exist_ok=True)

    for document_type in facts["documents"]:
        write_pdf(
            directory / f"{document_type}.pdf",
            RENDERERS[document_type](facts),
        )

    (directory / "claim.json").write_text(
        json.dumps(
            {
                "purpose": facts["purpose"],
                "expected_status": facts["expected_status"],
                "expected_review": facts.get("expected_review"),
                "expected_pending": facts.get("expected_pending"),
                "documents": facts["documents"],
                "claim_form": claim_form(facts),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"{name}: {len(facts['documents'])} documents")


if __name__ == "__main__":
    for scenario_name, scenario in SCENARIOS.items():
        build_claim(scenario_name, scenario)
