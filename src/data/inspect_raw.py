from pathlib import Path
import re


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "historical-ucl-matches"


# ============================================================
# Patterns
# ============================================================

SEASON_PATTERN = re.compile(
    r"UEFA Champions League (\d{4}/\d{2})"
)

TEAMS_PATTERN = re.compile(
    r"# Teams\s+(\d+)"
)

MATCHES_PATTERN = re.compile(
    r"# Matches\s+(\d+)"
)

STAGES_PATTERN = re.compile(
    r"# Stages\s+(.+)"
)

STAGE_PATTERN = re.compile(
    r"^▪\s+(.+)"
)

DATE_PATTERN = re.compile(
    r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"\s+\d{1,2}"
)

MATCH_LIKE_PATTERN = re.compile(
    r"\bv\b.*\d+-\d+"
)


# ============================================================
# File inspection
# ============================================================

def inspect_file(file_path):
    """
    Inspect one raw UCL file and return structural information.
    """

    with file_path.open(
        "r",
        encoding="utf-8"
    ) as file:
        lines = file.readlines()

    text = "".join(lines)

    # --------------------------------------------------------
    # Header information
    # --------------------------------------------------------

    season_match = SEASON_PATTERN.search(text)
    teams_match = TEAMS_PATTERN.search(text)
    matches_match = MATCHES_PATTERN.search(text)
    stages_match = STAGES_PATTERN.search(text)

    season = (
        season_match.group(1)
        if season_match
        else None
    )

    teams = (
        int(teams_match.group(1))
        if teams_match
        else None
    )

    declared_matches = (
        int(matches_match.group(1))
        if matches_match
        else None
    )

    stages_summary = (
        stages_match.group(1)
        if stages_match
        else None
    )

    # --------------------------------------------------------
    # Stage headings
    # --------------------------------------------------------

    stages = []

    for line in lines:

        match = STAGE_PATTERN.match(
            line.strip()
        )

        if match:
            stages.append(
                match.group(1).strip()
            )

    # --------------------------------------------------------
    # Match-like lines
    # --------------------------------------------------------

    match_like_lines = []

    for line_number, line in enumerate(
        lines,
        start=1
    ):

        stripped = line.strip()

        if MATCH_LIKE_PATTERN.search(stripped):
            match_like_lines.append(
                (line_number, stripped)
            )

    # --------------------------------------------------------
    # Date lines
    # --------------------------------------------------------

    date_lines = [
        line.strip()
        for line in lines
        if DATE_PATTERN.match(line.strip())
    ]

    # --------------------------------------------------------
    # Special results
    # --------------------------------------------------------

    extra_time_lines = [
        (i, line.strip())
        for i, line in enumerate(lines, start=1)
        if "a.e.t." in line
    ]

    penalty_lines = [
        (i, line.strip())
        for i, line in enumerate(lines, start=1)
        if "pen." in line
    ]

    return {
        "filename": file_path.name,
        "line_count": len(lines),
        "season": season,
        "teams": teams,
        "declared_matches": declared_matches,
        "stages_summary": stages_summary,
        "stages": stages,
        "match_like_count": len(match_like_lines),
        "date_count": len(date_lines),
        "extra_time_count": len(extra_time_lines),
        "penalty_count": len(penalty_lines),
        "match_like_lines": match_like_lines,
    }


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 70)
    print("UCL RAW DATA INSPECTION")
    print("=" * 70)

    print(f"\nRaw data directory:")
    print(RAW_DIR)

    files = sorted(
        RAW_DIR.glob("*.txt")
    )

    print(
        f"\nFiles discovered: {len(files)}"
    )

    if not files:
        print("\nERROR: No .txt files found.")
        return

    total_declared = 0
    total_detected = 0
    total_extra_time = 0
    total_penalties = 0

    print()

    for file_path in files:

        info = inspect_file(file_path)

        total_declared += (
            info["declared_matches"] or 0
        )

        total_detected += (
            info["match_like_count"]
        )

        total_extra_time += (
            info["extra_time_count"]
        )

        total_penalties += (
            info["penalty_count"]
        )

        print("-" * 70)
        print(info["filename"])
        print("-" * 70)

        print(
            f"Season:             {info['season']}"
        )

        print(
            f"Teams:              {info['teams']}"
        )

        print(
            f"Declared matches:   {info['declared_matches']}"
        )

        print(
            f"Match-like lines:   {info['match_like_count']}"
        )

        print(
            f"Date lines:         {info['date_count']}"
        )

        print(
            f"Extra-time results: {info['extra_time_count']}"
        )

        print(
            f"Penalty results:    {info['penalty_count']}"
        )

        if info["stages_summary"]:
            print(
                f"Stages:             {info['stages_summary']}"
            )

        # ----------------------------------------------------
        # Check declared vs detected
        # ----------------------------------------------------

        if (
            info["declared_matches"]
            != info["match_like_count"]
        ):

            print(
                "\nWARNING:"
            )

            print(
                "  Declared match count does not "
                "match detected match-like lines."
            )

        else:

            print(
                "\nMatch count check:  OK"
            )

    # ========================================================
    # Overall summary
    # ========================================================

    print("\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)

    print(
        f"Files:               {len(files)}"
    )

    print(
        f"Declared matches:    {total_declared}"
    )

    print(
        f"Detected matches:    {total_detected}"
    )

    print(
        f"Extra-time matches:  {total_extra_time}"
    )

    print(
        f"Penalty shootouts:   {total_penalties}"
    )

    if total_declared == total_detected:
        print(
            "\nOverall match count:  OK"
        )
    else:
        print(
            "\nOverall match count:  WARNING"
        )


if __name__ == "__main__":
    main()