import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from chatbot.config import CONFIG
from projectutils.env import setup_project_environment

# Setup project environment
PROJECT_ROOT, _ = setup_project_environment()


def is_numeric(value: Any) -> bool:
    """Check if a value is numeric."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def is_boolean(value: Any) -> bool:
    """Check if a value is boolean."""
    return isinstance(value, bool)


def calculate_numeric_stats(values: list[int | float]) -> dict[str, float]:
    """Calculate statistical measures for numeric values."""
    if not values:
        return {}

    values_array = np.array(values)
    return {
        "min": float(np.min(values_array)),
        "5%": float(np.percentile(values_array, 5)),
        "25%": float(np.percentile(values_array, 25)),
        "50%": float(np.percentile(values_array, 50)),
        "75%": float(np.percentile(values_array, 75)),
        "95%": float(np.percentile(values_array, 95)),
        "max": float(np.max(values_array)),
        "count": len(values),
    }


def calculate_boolean_stats(values: list[bool]) -> dict[str, int]:
    """Calculate counts for boolean values."""
    if not values:
        return {}

    true_count = sum(values)
    false_count = len(values) - true_count
    return {"True": true_count, "False": false_count, "total": len(values)}


def load_peterson_data() -> list[dict[str, Any]]:
    """Load the peterson_data.json file."""
    data_path = PROJECT_ROOT / Path(CONFIG.paths.input_json)

    if not data_path.exists():
        raise FileNotFoundError(f"Peterson data file not found at: {data_path}")

    print(f"Loading data from: {data_path}")
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} universities")
    return data


def analyze_location_section(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze the location_contact section."""
    print("\nAnalyzing LOCATION section...")

    address_keys = Counter()
    contact_keys = Counter()
    address_samples = defaultdict(list)
    contact_samples = defaultdict(list)
    address_numeric_values = defaultdict(list)
    contact_numeric_values = defaultdict(list)
    address_boolean_values = defaultdict(list)
    contact_boolean_values = defaultdict(list)

    for i, university in enumerate(data):
        if i % 200 == 0:
            print(f"  Processed {i}/{len(data)} universities...")

        location = university.get("location_contact", {})

        # Analyze address keys
        address = location.get("address", {})
        for key, value in address.items():
            address_keys[key] += 1
            if value is not None:
                if is_numeric(value):
                    address_numeric_values[key].append(float(value))
                elif is_boolean(value):
                    address_boolean_values[key].append(value)
                else:
                    if len(address_samples[key]) < 3:
                        str_value = str(value)
                        if str_value not in address_samples[key]:
                            address_samples[key].append(str_value)

        # Analyze contact keys
        contact = location.get("contact", {})
        for key, value in contact.items():
            contact_keys[key] += 1
            if value is not None:
                if is_numeric(value):
                    contact_numeric_values[key].append(float(value))
                elif is_boolean(value):
                    contact_boolean_values[key].append(value)
                else:
                    if len(contact_samples[key]) < 3:
                        str_value = str(value)
                        if str_value not in contact_samples[key]:
                            contact_samples[key].append(str_value)

    # Calculate statistics
    address_numeric_stats = {}
    for key, values in address_numeric_values.items():
        address_numeric_stats[key] = calculate_numeric_stats(values)

    contact_numeric_stats = {}
    for key, values in contact_numeric_values.items():
        contact_numeric_stats[key] = calculate_numeric_stats(values)

    address_boolean_stats = {}
    for key, values in address_boolean_values.items():
        address_boolean_stats[key] = calculate_boolean_stats(values)

    contact_boolean_stats = {}
    for key, values in contact_boolean_values.items():
        contact_boolean_stats[key] = calculate_boolean_stats(values)

    return {
        "section_name": "location_contact",
        "total_universities": len(data),
        "address_keys": address_keys,
        "contact_keys": contact_keys,
        "address_samples": dict(address_samples),
        "contact_samples": dict(contact_samples),
        "address_numeric_stats": address_numeric_stats,
        "contact_numeric_stats": contact_numeric_stats,
        "address_boolean_stats": address_boolean_stats,
        "contact_boolean_stats": contact_boolean_stats,
    }


def analyze_admissions_section(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze the admissions section."""
    print("\nAnalyzing ADMISSIONS section...")

    all_keys = Counter()
    samples = defaultdict(list)
    numeric_values = defaultdict(list)
    boolean_values = defaultdict(list)

    # Separate collections for test scores
    sat_reading_scores = defaultdict(list)
    sat_math_scores = defaultdict(list)
    act_composite_scores = defaultdict(list)
    sat_total_scores = defaultdict(list)
    universities_with_test_scores = set()

    def analyze_nested(obj, prefix=""):
        """Recursively analyze nested structure."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key
                all_keys[full_key] += 1

                if not isinstance(value, dict | list) and value is not None:
                    if is_boolean(value):
                        boolean_values[full_key].append(value)
                    elif is_numeric(value):
                        numeric_values[full_key].append(float(value))
                    else:
                        if len(samples[full_key]) < 3:
                            str_value = str(value)
                            if str_value not in samples[full_key]:
                                samples[full_key].append(str_value)
                elif isinstance(value, dict):
                    analyze_nested(value, full_key)
                elif isinstance(value, list) and value:
                    if isinstance(value[0], dict):
                        analyze_nested(value[0], f"{full_key}[0]")
                    else:
                        # List of simple values
                        if is_boolean(value[0]):
                            boolean_values[full_key].append(value[0])
                        elif is_numeric(value[0]):
                            numeric_values[full_key].append(float(value[0]))
                        else:
                            if len(samples[full_key]) < 3:
                                str_value = str(value[0])
                                if str_value not in samples[full_key]:
                                    samples[full_key].append(str_value)

    for i, university in enumerate(data):
        if i % 200 == 0:
            print(f"  Processed {i}/{len(data)} universities...")

        admissions = university.get("admissions", {})
        if admissions:
            analyze_nested(admissions)

            # Special handling for test scores
            test_scores = admissions.get("test_scores_accepted", [])
            if test_scores:
                universities_with_test_scores.add(i)

                # Track individual test scores
                sat_reading_data = None
                sat_math_data = None

                for test_score in test_scores:
                    if isinstance(test_score, dict):
                        test_name = test_score.get("test", "")
                        avg_score = test_score.get("avg_score")
                        percentile_25 = test_score.get("percentile_25")
                        percentile_75 = test_score.get("percentile_75")

                        if (
                            "SAT Critical Reading" in test_name
                            or "SAT Verbal" in test_name
                        ):
                            if avg_score is not None and is_numeric(avg_score):
                                sat_reading_scores["avg_score"].append(float(avg_score))
                                sat_reading_data = float(avg_score)
                            if percentile_25 is not None and is_numeric(percentile_25):
                                sat_reading_scores["percentile_25"].append(
                                    float(percentile_25)
                                )
                            if percentile_75 is not None and is_numeric(percentile_75):
                                sat_reading_scores["percentile_75"].append(
                                    float(percentile_75)
                                )

                        elif "SAT Math" in test_name:
                            if avg_score is not None and is_numeric(avg_score):
                                sat_math_scores["avg_score"].append(float(avg_score))
                                sat_math_data = float(avg_score)
                            if percentile_25 is not None and is_numeric(percentile_25):
                                sat_math_scores["percentile_25"].append(
                                    float(percentile_25)
                                )
                            if percentile_75 is not None and is_numeric(percentile_75):
                                sat_math_scores["percentile_75"].append(
                                    float(percentile_75)
                                )

                        elif "ACT Composite" in test_name:
                            if avg_score is not None and is_numeric(avg_score):
                                act_composite_scores["avg_score"].append(
                                    float(avg_score)
                                )
                            if percentile_25 is not None and is_numeric(percentile_25):
                                act_composite_scores["percentile_25"].append(
                                    float(percentile_25)
                                )
                            if percentile_75 is not None and is_numeric(percentile_75):
                                act_composite_scores["percentile_75"].append(
                                    float(percentile_75)
                                )

                # Calculate SAT total if both reading and math data are available
                if sat_reading_data is not None and sat_math_data is not None:
                    sat_total = sat_reading_data + sat_math_data
                    sat_total_scores["total_avg"].append(sat_total)

    # Calculate statistics for test scores
    sat_reading_stats = {}
    for key, values in sat_reading_scores.items():
        if values:
            sat_reading_stats[f"sat_reading_{key}"] = calculate_numeric_stats(values)

    sat_math_stats = {}
    for key, values in sat_math_scores.items():
        if values:
            sat_math_stats[f"sat_math_{key}"] = calculate_numeric_stats(values)

    act_composite_stats = {}
    for key, values in act_composite_scores.items():
        if values:
            act_composite_stats[f"act_composite_{key}"] = calculate_numeric_stats(
                values
            )

    sat_total_stats = {}
    for key, values in sat_total_scores.items():
        if values:
            sat_total_stats[f"sat_{key}"] = calculate_numeric_stats(values)

    # Calculate statistics for other fields
    numeric_stats = {}
    for key, values in numeric_values.items():
        numeric_stats[key] = calculate_numeric_stats(values)

    boolean_stats = {}
    for key, values in boolean_values.items():
        boolean_stats[key] = calculate_boolean_stats(values)

    return {
        "section_name": "admissions",
        "total_universities": len(data),
        "all_keys": all_keys,
        "samples": dict(samples),
        "numeric_stats": numeric_stats,
        "boolean_stats": boolean_stats,
        "sat_reading_stats": sat_reading_stats,
        "sat_math_stats": sat_math_stats,
        "act_composite_stats": act_composite_stats,
        "sat_total_stats": sat_total_stats,
        "universities_with_test_scores": len(universities_with_test_scores),
    }


def analyze_tuition_section(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze the tuition_and_fees section."""
    print("\nAnalyzing TUITION_AND_FEES section...")

    all_keys = Counter()
    samples = defaultdict(list)
    tuition_categories = Counter()
    fee_categories = Counter()
    tuition_numeric_values = defaultdict(list)
    fee_numeric_values = defaultdict(list)
    numeric_values = defaultdict(list)
    boolean_values = defaultdict(list)

    for i, university in enumerate(data):
        if i % 200 == 0:
            print(f"  Processed {i}/{len(data)} universities...")

        tuition_fees = university.get("tuition_and_fees", {})

        # Track top-level keys
        for key in tuition_fees.keys():
            all_keys[key] += 1

        # Analyze tuition categories
        for tuition_info in tuition_fees.get("tuition", []):
            category = tuition_info.get("category")
            if category:
                tuition_categories[category] += 1
                amount = tuition_info.get("amount")
                if amount is not None:
                    if is_numeric(amount):
                        tuition_numeric_values[f"tuition.{category}"].append(
                            float(amount)
                        )
                    else:
                        if len(samples[f"tuition.{category}"]) < 3:
                            str_amount = str(amount)
                            if str_amount not in samples[f"tuition.{category}"]:
                                samples[f"tuition.{category}"].append(str_amount)

        # Analyze fee categories
        for fee_info in tuition_fees.get("fees", []):
            category = fee_info.get("category")
            if category:
                fee_categories[category] += 1
                amount = fee_info.get("amount")
                if amount is not None:
                    if is_numeric(amount):
                        fee_numeric_values[f"fees.{category}"].append(float(amount))
                    else:
                        if len(samples[f"fees.{category}"]) < 3:
                            str_amount = str(amount)
                            if str_amount not in samples[f"fees.{category}"]:
                                samples[f"fees.{category}"].append(str_amount)

        # Other payment considerations
        other = tuition_fees.get("other_payment_considerations")
        if other is not None:
            all_keys["other_payment_considerations"] += 1
            if is_numeric(other):
                numeric_values["other_payment_considerations"].append(float(other))
            elif is_boolean(other):
                boolean_values["other_payment_considerations"].append(other)
            else:
                if len(samples["other_payment_considerations"]) < 3:
                    str_other = str(other)
                    if str_other not in samples["other_payment_considerations"]:
                        samples["other_payment_considerations"].append(str_other)

    # Calculate statistics
    tuition_numeric_stats = {}
    for key, values in tuition_numeric_values.items():
        tuition_numeric_stats[key] = calculate_numeric_stats(values)

    fee_numeric_stats = {}
    for key, values in fee_numeric_values.items():
        fee_numeric_stats[key] = calculate_numeric_stats(values)

    numeric_stats = {}
    for key, values in numeric_values.items():
        numeric_stats[key] = calculate_numeric_stats(values)

    boolean_stats = {}
    for key, values in boolean_values.items():
        boolean_stats[key] = calculate_boolean_stats(values)

    return {
        "section_name": "tuition_and_fees",
        "total_universities": len(data),
        "all_keys": all_keys,
        "tuition_categories": tuition_categories,
        "fee_categories": fee_categories,
        "samples": dict(samples),
        "tuition_numeric_stats": tuition_numeric_stats,
        "fee_numeric_stats": fee_numeric_stats,
        "numeric_stats": numeric_stats,
        "boolean_stats": boolean_stats,
    }


def analyze_campus_life_section(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze the campus_life section."""
    print("\nAnalyzing CAMPUS_LIFE section...")

    all_keys = Counter()
    samples = defaultdict(list)
    numeric_values = defaultdict(list)
    boolean_values = defaultdict(list)

    def analyze_nested(obj, prefix=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key
                all_keys[full_key] += 1

                if not isinstance(value, dict | list) and value is not None:
                    if is_boolean(value):
                        boolean_values[full_key].append(value)
                    elif is_numeric(value):
                        numeric_values[full_key].append(float(value))
                    else:
                        if len(samples[full_key]) < 3:
                            str_value = str(value)
                            if str_value not in samples[full_key]:
                                samples[full_key].append(str_value)
                elif isinstance(value, dict):
                    analyze_nested(value, full_key)
                elif isinstance(value, list) and value:
                    if isinstance(value[0], dict):
                        analyze_nested(value[0], f"{full_key}[0]")
                    else:
                        if len(samples[full_key]) < 3:
                            str_value = str(value[:3])  # First few items
                            if str_value not in samples[full_key]:
                                samples[full_key].append(str_value)

    for i, university in enumerate(data):
        if i % 200 == 0:
            print(f"  Processed {i}/{len(data)} universities...")

        campus_life = university.get("campus_life", {})
        if campus_life:
            analyze_nested(campus_life)

    # Calculate statistics
    numeric_stats = {}
    for key, values in numeric_values.items():
        numeric_stats[key] = calculate_numeric_stats(values)

    boolean_stats = {}
    for key, values in boolean_values.items():
        boolean_stats[key] = calculate_boolean_stats(values)

    return {
        "section_name": "campus_life",
        "total_universities": len(data),
        "all_keys": all_keys,
        "samples": dict(samples),
        "numeric_stats": numeric_stats,
        "boolean_stats": boolean_stats,
    }


def analyze_faculty_section(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze the faculty section."""
    print("\nAnalyzing FACULTY section...")

    all_keys = Counter()
    samples = defaultdict(list)
    numeric_values = defaultdict(list)
    boolean_values = defaultdict(list)

    def analyze_nested(obj, prefix=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key
                all_keys[full_key] += 1

                if not isinstance(value, dict | list) and value is not None:
                    if is_boolean(value):
                        boolean_values[full_key].append(value)
                    elif is_numeric(value):
                        numeric_values[full_key].append(float(value))
                    else:
                        if len(samples[full_key]) < 3:
                            str_value = str(value)
                            if str_value not in samples[full_key]:
                                samples[full_key].append(str_value)
                elif isinstance(value, dict):
                    analyze_nested(value, full_key)

    for i, university in enumerate(data):
        if i % 200 == 0:
            print(f"  Processed {i}/{len(data)} universities...")

        faculty = university.get("faculty", {})
        if faculty:
            analyze_nested(faculty)

    # Calculate statistics
    numeric_stats = {}
    for key, values in numeric_values.items():
        numeric_stats[key] = calculate_numeric_stats(values)

    boolean_stats = {}
    for key, values in boolean_values.items():
        boolean_stats[key] = calculate_boolean_stats(values)

    return {
        "section_name": "faculty",
        "total_universities": len(data),
        "all_keys": all_keys,
        "samples": dict(samples),
        "numeric_stats": numeric_stats,
        "boolean_stats": boolean_stats,
    }


def print_location_report(analysis: dict[str, Any]) -> None:
    """Print detailed location analysis report."""
    total = analysis["total_universities"]

    print("\n" + "=" * 70)
    print("LOCATION SECTION DETAILED REPORT")
    print("=" * 70)

    print("\nThis section analyzes university location and contact information.")
    print("Coverage percentages show how many universities have data for each field.")
    print(
        "Numeric stats show distribution percentiles (5% means 5% of values are below this)."
    )
    print("Boolean stats show counts of True/False values.")

    print(f"\nADDRESS KEYS ({len(analysis['address_keys'])} unique keys):")
    print("-" * 50)
    for key, count in analysis["address_keys"].most_common():
        percentage = (count / total) * 100
        print(f"  • {key:<15} {count:>4}/{total} ({percentage:>5.1f}%)")

        # Print numeric statistics if available
        if key in analysis["address_numeric_stats"]:
            stats = analysis["address_numeric_stats"][key]
            print(
                f"    Numeric stats: min={stats['min']:.2f}, 5%={stats['5%']:.2f}, 25%={stats['25%']:.2f}, 50%={stats['50%']:.2f}, 75%={stats['75%']:.2f}, 95%={stats['95%']:.2f}, max={stats['max']:.2f}"
            )

        # Print boolean statistics if available
        elif key in analysis["address_boolean_stats"]:
            stats = analysis["address_boolean_stats"][key]
            print(f"    Boolean stats: True={stats['True']}, False={stats['False']}")

        # Print text samples if available
        elif key in analysis["address_samples"]:
            samples = analysis["address_samples"][key][:3]
            print(f"    Examples: {', '.join(samples)}")

    print(f"\nCONTACT KEYS ({len(analysis['contact_keys'])} unique keys):")
    print("-" * 50)
    for key, count in analysis["contact_keys"].most_common():
        percentage = (count / total) * 100
        print(f"  • {key:<15} {count:>4}/{total} ({percentage:>5.1f}%)")

        # Print numeric statistics if available
        if key in analysis["contact_numeric_stats"]:
            stats = analysis["contact_numeric_stats"][key]
            print(
                f"    Numeric stats: min={stats['min']:.2f}, 5%={stats['5%']:.2f}, 25%={stats['25%']:.2f}, 50%={stats['50%']:.2f}, 75%={stats['75%']:.2f}, 95%={stats['95%']:.2f}, max={stats['max']:.2f}"
            )

        # Print boolean statistics if available
        elif key in analysis["contact_boolean_stats"]:
            stats = analysis["contact_boolean_stats"][key]
            print(f"    Boolean stats: True={stats['True']}, False={stats['False']}")

        # Print text samples if available
        elif key in analysis["contact_samples"]:
            samples = analysis["contact_samples"][key][:3]
            print(f"    Examples: {', '.join(samples)}")


def print_section_report(analysis: dict[str, Any]) -> None:
    """Print detailed section analysis report."""
    total = analysis["total_universities"]
    section_name = analysis["section_name"].upper().replace("_", " ")

    print("\n" + "=" * 70)
    print(f"{section_name} SECTION DETAILED REPORT")
    print("=" * 70)

    # Add section-specific explanations
    if analysis["section_name"] == "admissions":
        print(
            "\nThis section analyzes university admissions requirements and policies."
        )
        print(
            "Coverage shows how many universities provide each type of admissions data."
        )
        print("Examples show typical values found in the dataset.")
    elif analysis["section_name"] == "tuition_and_fees":
        print("\nThis section analyzes university costs including tuition and fees.")
        print(
            "Categories show different types of tuition (in-state, out-of-state, etc.)."
        )
        print("Numeric stats for tuition/fees are in dollars ($).")
    elif analysis["section_name"] == "campus_life":
        print("\nThis section analyzes campus life features and student services.")
        print("Coverage shows availability of different campus life aspects.")
    elif analysis["section_name"] == "faculty":
        print("\nThis section analyzes faculty information and academic staff data.")
        print("Numeric stats may include faculty counts, ratios, or percentages.")
    elif analysis["section_name"] == "financial_aid":
        print("\nThis section analyzes financial aid programs and assistance options.")
        print("Coverage shows availability of different financial aid information.")

    print("Coverage percentages show how many universities have data for each field.")
    print(
        "Numeric stats show distribution percentiles (min, 5%, 25%, 50%, 75%, 95%, max)."
    )
    print("Boolean stats show counts of True/False values.")

    # Special handling for admissions section test scores
    if (
        analysis["section_name"] == "admissions"
        and "universities_with_test_scores" in analysis
    ):
        test_score_count = analysis["universities_with_test_scores"]
        print(
            f"\nTEST SCORE ANALYSIS ({test_score_count}/{total} universities with test scores):"
        )
        print("-" * 60)

        # SAT Reading Statistics
        if analysis.get("sat_reading_stats"):
            print("\nSAT CRITICAL READING SCORES:")
            for stat_name, stats in analysis["sat_reading_stats"].items():
                readable_name = (
                    stat_name.replace("sat_reading_", "").replace("_", " ").title()
                )
                print(f"  • {readable_name:<20} {stats['count']:>4} universities")
                print(
                    f"    Range: {stats['min']:.0f} - {stats['max']:.0f}, Median: {stats['50%']:.0f}"
                )
                print(
                    f"    Percentiles: 25%={stats['25%']:.0f}, 75%={stats['75%']:.0f}, 95%={stats['95%']:.0f}"
                )

        # SAT Math Statistics
        if analysis.get("sat_math_stats"):
            print("\nSAT MATH SCORES:")
            for stat_name, stats in analysis["sat_math_stats"].items():
                readable_name = (
                    stat_name.replace("sat_math_", "").replace("_", " ").title()
                )
                print(f"  • {readable_name:<20} {stats['count']:>4} universities")
                print(
                    f"    Range: {stats['min']:.0f} - {stats['max']:.0f}, Median: {stats['50%']:.0f}"
                )
                print(
                    f"    Percentiles: 25%={stats['25%']:.0f}, 75%={stats['75%']:.0f}, 95%={stats['95%']:.0f}"
                )

        # SAT Total Statistics
        if analysis.get("sat_total_stats"):
            print("\nSAT TOTAL SCORES (Reading + Math):")
            for stat_name, stats in analysis["sat_total_stats"].items():
                readable_name = stat_name.replace("sat_", "").replace("_", " ").title()
                print(f"  • {readable_name:<20} {stats['count']:>4} universities")
                print(
                    f"    Range: {stats['min']:.0f} - {stats['max']:.0f}, Median: {stats['50%']:.0f}"
                )
                print(
                    f"    Percentiles: 25%={stats['25%']:.0f}, 75%={stats['75%']:.0f}, 95%={stats['95%']:.0f}"
                )

        # ACT Composite Statistics
        if analysis.get("act_composite_stats"):
            print("\nACT COMPOSITE SCORES:")
            for stat_name, stats in analysis["act_composite_stats"].items():
                readable_name = (
                    stat_name.replace("act_composite_", "").replace("_", " ").title()
                )
                print(f"  • {readable_name:<20} {stats['count']:>4} universities")
                print(
                    f"    Range: {stats['min']:.0f} - {stats['max']:.0f}, Median: {stats['50%']:.0f}"
                )
                print(
                    f"    Percentiles: 25%={stats['25%']:.0f}, 75%={stats['75%']:.0f}, 95%={stats['95%']:.0f}"
                )

    if "tuition_categories" in analysis:
        # Special handling for tuition section
        print("\nTUITION CATEGORIES:")
        print("-" * 40)
        for category, count in analysis["tuition_categories"].most_common():
            percentage = (count / total) * 100
            print(f"  • {category:<20} {count:>4}/{total} ({percentage:>5.1f}%)")

            # Print numeric statistics if available
            if (
                "tuition_numeric_stats" in analysis
                and f"tuition.{category}" in analysis["tuition_numeric_stats"]
            ):
                stats = analysis["tuition_numeric_stats"][f"tuition.{category}"]
                print(
                    f"    Numeric stats: min=${stats['min']:.0f}, 5%=${stats['5%']:.0f}, 25%=${stats['25%']:.0f}, 50%=${stats['50%']:.0f}, 75%=${stats['75%']:.0f}, 95%=${stats['95%']:.0f}, max=${stats['max']:.0f}"
                )

            # Print text samples if available
            elif f"tuition.{category}" in analysis["samples"]:
                samples = analysis["samples"][f"tuition.{category}"][:3]
                print(f"    Examples: {', '.join(samples)}")

        print("\nFEE CATEGORIES:")
        print("-" * 40)
        for category, count in analysis["fee_categories"].most_common():
            percentage = (count / total) * 100
            print(f"  • {category:<20} {count:>4}/{total} ({percentage:>5.1f}%)")

            # Print numeric statistics if available
            if (
                "fee_numeric_stats" in analysis
                and f"fees.{category}" in analysis["fee_numeric_stats"]
            ):
                stats = analysis["fee_numeric_stats"][f"fees.{category}"]
                print(
                    f"    Numeric stats: min=${stats['min']:.0f}, 5%=${stats['5%']:.0f}, 25%=${stats['25%']:.0f}, 50%=${stats['50%']:.0f}, 75%=${stats['75%']:.0f}, 95%=${stats['95%']:.0f}, max=${stats['max']:.0f}"
                )

            # Print text samples if available
            elif f"fees.{category}" in analysis["samples"]:
                samples = analysis["samples"][f"fees.{category}"][:3]
                print(f"    Examples: {', '.join(samples)}")

    print(f"\nALL KEYS IN {section_name}:")
    print("-" * 50)
    for key, count in analysis["all_keys"].most_common():
        percentage = (count / total) * 100
        print(f"  • {key:<30} {count:>4}/{total} ({percentage:>5.1f}%)")

        # Print numeric statistics if available
        if "numeric_stats" in analysis and key in analysis["numeric_stats"]:
            stats = analysis["numeric_stats"][key]
            print(
                f"    Numeric stats: min={stats['min']:.2f}, 5%={stats['5%']:.2f}, 25%={stats['25%']:.2f}, 50%={stats['50%']:.2f}, 75%={stats['75%']:.2f}, 95%={stats['95%']:.2f}, max={stats['max']:.2f}"
            )

        # Print boolean statistics if available
        elif "boolean_stats" in analysis and key in analysis["boolean_stats"]:
            stats = analysis["boolean_stats"][key]
            print(f"    Boolean stats: True={stats['True']}, False={stats['False']}")

        # Print text samples if available
        elif key in analysis["samples"]:
            samples = analysis["samples"][key][:3]
            print(f"    Examples: {', '.join(samples)}")


def analyze_financial_aid_section(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze the financial_aid section."""
    print("\nAnalyzing FINANCIAL_AID section...")

    all_keys = Counter()
    samples = defaultdict(list)
    numeric_values = defaultdict(list)
    boolean_values = defaultdict(list)

    def analyze_nested(obj, prefix=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key
                all_keys[full_key] += 1

                if not isinstance(value, dict | list) and value is not None:
                    if is_boolean(value):
                        boolean_values[full_key].append(value)
                    elif is_numeric(value):
                        numeric_values[full_key].append(float(value))
                    else:
                        if len(samples[full_key]) < 3:
                            str_value = str(value)
                            if str_value not in samples[full_key]:
                                samples[full_key].append(str_value)
                elif isinstance(value, dict):
                    analyze_nested(value, full_key)

    for i, university in enumerate(data):
        if i % 200 == 0:
            print(f"  Processed {i}/{len(data)} universities...")

        financial_aid = university.get("financial_aid", {})
        if financial_aid:
            analyze_nested(financial_aid)

    # Calculate statistics
    numeric_stats = {}
    for key, values in numeric_values.items():
        numeric_stats[key] = calculate_numeric_stats(values)

    boolean_stats = {}
    for key, values in boolean_values.items():
        boolean_stats[key] = calculate_boolean_stats(values)

    return {
        "section_name": "financial_aid",
        "total_universities": len(data),
        "all_keys": all_keys,
        "samples": dict(samples),
        "numeric_stats": numeric_stats,
        "boolean_stats": boolean_stats,
    }


def analyze_athletics_section(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze the athletics section."""
    print("\nAnalyzing ATHLETICS section...")

    all_keys = Counter()
    samples = defaultdict(list)
    mens_sports_count = Counter()
    womens_sports_count = Counter()
    numeric_values = defaultdict(list)
    boolean_values = defaultdict(list)

    # Track universities that have each attribute (not individual sport records)
    universities_with_key = defaultdict(set)

    for i, university in enumerate(data):
        if i % 200 == 0:
            print(f"  Processed {i}/{len(data)} universities...")

        athletics = university.get("athletics", {})

        # Count top-level keys
        for key in athletics.keys():
            universities_with_key[key].add(i)

        # Analyze men's sports
        mens_sports = athletics.get("Men's Sports", [])
        if mens_sports:
            universities_with_key["Men's Sports"].add(i)

            # Track if this university has any men's sports with these attributes
            has_mens_intramural = False
            has_mens_intercollegiate = False
            has_mens_scholarship = False

            for sport_info in mens_sports:
                if isinstance(sport_info, dict):
                    sport_name = sport_info.get("sport")
                    if sport_name:
                        mens_sports_count[sport_name] += 1
                        if len(samples["Men's Sports.sports"]) < 10:
                            if sport_name not in samples["Men's Sports.sports"]:
                                samples["Men's Sports.sports"].append(sport_name)

                    # Check sport attributes for this university
                    if sport_info.get("intramural") is not None:
                        has_mens_intramural = True
                        intramural_val = sport_info["intramural"]
                        if is_boolean(intramural_val):
                            boolean_values["Men's Sports.intramural"].append(
                                intramural_val
                            )
                        elif is_numeric(intramural_val):
                            numeric_values["Men's Sports.intramural"].append(
                                float(intramural_val)
                            )
                        else:
                            if len(samples["Men's Sports.intramural"]) < 3:
                                str_value = str(intramural_val)
                                if str_value not in samples["Men's Sports.intramural"]:
                                    samples["Men's Sports.intramural"].append(str_value)

                    if sport_info.get("intercollegiate") is not None:
                        has_mens_intercollegiate = True
                        intercollegiate_val = sport_info["intercollegiate"]
                        if is_boolean(intercollegiate_val):
                            boolean_values["Men's Sports.intercollegiate"].append(
                                intercollegiate_val
                            )
                        elif is_numeric(intercollegiate_val):
                            numeric_values["Men's Sports.intercollegiate"].append(
                                float(intercollegiate_val)
                            )
                        else:
                            if len(samples["Men's Sports.intercollegiate"]) < 3:
                                str_value = str(intercollegiate_val)
                                if (
                                    str_value
                                    not in samples["Men's Sports.intercollegiate"]
                                ):
                                    samples["Men's Sports.intercollegiate"].append(
                                        str_value
                                    )

                    if sport_info.get("scholarship") is not None:
                        has_mens_scholarship = True
                        scholarship_val = sport_info["scholarship"]
                        if is_boolean(scholarship_val):
                            boolean_values["Men's Sports.scholarship"].append(
                                scholarship_val
                            )
                        elif is_numeric(scholarship_val):
                            numeric_values["Men's Sports.scholarship"].append(
                                float(scholarship_val)
                            )
                        else:
                            if len(samples["Men's Sports.scholarship"]) < 3:
                                str_value = str(scholarship_val)
                                if str_value not in samples["Men's Sports.scholarship"]:
                                    samples["Men's Sports.scholarship"].append(
                                        str_value
                                    )

            # Count university once for each attribute it has
            if has_mens_intramural:
                universities_with_key["Men's Sports.intramural"].add(i)
            if has_mens_intercollegiate:
                universities_with_key["Men's Sports.intercollegiate"].add(i)
            if has_mens_scholarship:
                universities_with_key["Men's Sports.scholarship"].add(i)

        # Analyze women's sports
        womens_sports = athletics.get("Women's Sports", [])
        if womens_sports:
            universities_with_key["Women's Sports"].add(i)

            # Track if this university has any women's sports with these attributes
            has_womens_intramural = False
            has_womens_intercollegiate = False
            has_womens_scholarship = False

            for sport_info in womens_sports:
                if isinstance(sport_info, dict):
                    sport_name = sport_info.get("sport")
                    if sport_name:
                        womens_sports_count[sport_name] += 1
                        if len(samples["Women's Sports.sports"]) < 10:
                            if sport_name not in samples["Women's Sports.sports"]:
                                samples["Women's Sports.sports"].append(sport_name)

                    # Check sport attributes for this university
                    if sport_info.get("intramural") is not None:
                        has_womens_intramural = True
                        intramural_val = sport_info["intramural"]
                        if is_boolean(intramural_val):
                            boolean_values["Women's Sports.intramural"].append(
                                intramural_val
                            )
                        elif is_numeric(intramural_val):
                            numeric_values["Women's Sports.intramural"].append(
                                float(intramural_val)
                            )
                        else:
                            if len(samples["Women's Sports.intramural"]) < 3:
                                str_value = str(intramural_val)
                                if (
                                    str_value
                                    not in samples["Women's Sports.intramural"]
                                ):
                                    samples["Women's Sports.intramural"].append(
                                        str_value
                                    )

                    if sport_info.get("intercollegiate") is not None:
                        has_womens_intercollegiate = True
                        intercollegiate_val = sport_info["intercollegiate"]
                        if is_boolean(intercollegiate_val):
                            boolean_values["Women's Sports.intercollegiate"].append(
                                intercollegiate_val
                            )
                        elif is_numeric(intercollegiate_val):
                            numeric_values["Women's Sports.intercollegiate"].append(
                                float(intercollegiate_val)
                            )
                        else:
                            if len(samples["Women's Sports.intercollegiate"]) < 3:
                                str_value = str(intercollegiate_val)
                                if (
                                    str_value
                                    not in samples["Women's Sports.intercollegiate"]
                                ):
                                    samples["Women's Sports.intercollegiate"].append(
                                        str_value
                                    )

                    if sport_info.get("scholarship") is not None:
                        has_womens_scholarship = True
                        scholarship_val = sport_info["scholarship"]
                        if is_boolean(scholarship_val):
                            boolean_values["Women's Sports.scholarship"].append(
                                scholarship_val
                            )
                        elif is_numeric(scholarship_val):
                            numeric_values["Women's Sports.scholarship"].append(
                                float(scholarship_val)
                            )
                        else:
                            if len(samples["Women's Sports.scholarship"]) < 3:
                                str_value = str(scholarship_val)
                                if (
                                    str_value
                                    not in samples["Women's Sports.scholarship"]
                                ):
                                    samples["Women's Sports.scholarship"].append(
                                        str_value
                                    )

            # Count university once for each attribute it has
            if has_womens_intramural:
                universities_with_key["Women's Sports.intramural"].add(i)
            if has_womens_intercollegiate:
                universities_with_key["Women's Sports.intercollegiate"].add(i)
            if has_womens_scholarship:
                universities_with_key["Women's Sports.scholarship"].add(i)

    # Convert sets to counts
    for key, university_set in universities_with_key.items():
        all_keys[key] = len(university_set)

    # Calculate statistics
    numeric_stats = {}
    for key, values in numeric_values.items():
        numeric_stats[key] = calculate_numeric_stats(values)

    boolean_stats = {}
    for key, values in boolean_values.items():
        boolean_stats[key] = calculate_boolean_stats(values)

    return {
        "section_name": "athletics",
        "total_universities": len(data),
        "all_keys": all_keys,
        "samples": dict(samples),
        "mens_sports_count": mens_sports_count,
        "womens_sports_count": womens_sports_count,
        "numeric_stats": numeric_stats,
        "boolean_stats": boolean_stats,
    }


def print_athletics_report(analysis: dict[str, Any]) -> None:
    """Print detailed athletics analysis report."""
    total = analysis["total_universities"]

    print("\n" + "=" * 70)
    print("ATHLETICS SECTION DETAILED REPORT")
    print("=" * 70)

    print("\nThis section analyzes university athletics programs and sports offerings.")
    print("Sports counts show how many universities offer each specific sport.")
    print("Coverage percentages show availability of different athletics data.")
    print(
        "Boolean stats for sports attributes show True/False counts for features like:"
    )
    print("  - Intramural: casual/recreational sports within the university")
    print("  - Intercollegiate: competitive sports between universities")
    print("  - Scholarship: whether athletic scholarships are available")

    print("\nTOP 20 MEN'S SPORTS:")
    print("-" * 50)
    for sport, count in analysis["mens_sports_count"].most_common(20):
        percentage = (count / total) * 100
        print(f"  • {sport:<30} {count:>4}/{total} ({percentage:>5.1f}%)")

    print("\nTOP 20 WOMEN'S SPORTS:")
    print("-" * 50)
    for sport, count in analysis["womens_sports_count"].most_common(20):
        percentage = (count / total) * 100
        print(f"  • {sport:<30} {count:>4}/{total} ({percentage:>5.1f}%)")

    print("\nALL KEYS IN ATHLETICS:")
    print("-" * 50)
    for key, count in analysis["all_keys"].most_common():
        percentage = (count / total) * 100
        print(f"  • {key:<30} {count:>4}/{total} ({percentage:>5.1f}%)")

        # Print numeric statistics if available
        if key in analysis["numeric_stats"]:
            stats = analysis["numeric_stats"][key]
            print(
                f"    Numeric stats: min={stats['min']:.2f}, 5%={stats['5%']:.2f}, 25%={stats['25%']:.2f}, 50%={stats['50%']:.2f}, 75%={stats['75%']:.2f}, 95%={stats['95%']:.2f}, max={stats['max']:.2f}"
            )

        # Print boolean statistics if available
        elif key in analysis["boolean_stats"]:
            stats = analysis["boolean_stats"][key]
            print(f"    Boolean stats: True={stats['True']}, False={stats['False']}")

        # Print text samples if available
        elif key in analysis["samples"]:
            samples = analysis["samples"][key][:5]
            print(f"    Examples: {', '.join(samples)}")


def main():
    """Main function to run comprehensive analysis."""
    print("PETERSON DATA JSON STRUCTURE ANALYZER")
    print("=" * 70)

    try:
        # Load data
        data = load_peterson_data()

        # Analyze each section
        location_analysis = analyze_location_section(data)
        admissions_analysis = analyze_admissions_section(data)
        tuition_analysis = analyze_tuition_section(data)
        campus_life_analysis = analyze_campus_life_section(data)
        faculty_analysis = analyze_faculty_section(data)
        financial_aid_analysis = analyze_financial_aid_section(data)
        athletics_analysis = analyze_athletics_section(data)

        # Print reports to console
        print_location_report(location_analysis)
        print_section_report(admissions_analysis)
        print_section_report(tuition_analysis)
        print_section_report(campus_life_analysis)
        print_section_report(faculty_analysis)
        print_section_report(financial_aid_analysis)
        print_athletics_report(athletics_analysis)

        print("\n" + "=" * 70)
        print("COMPREHENSIVE ANALYSIS COMPLETE!")
        print("=" * 70)
        print("Total sections analyzed: 7")
        print(f"Total universities: {len(data)}")

    except Exception as e:
        print(f"Error during analysis: {e}")
        raise


if __name__ == "__main__":
    main()
