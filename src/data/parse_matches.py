from pathlib import Path
from datetime import datetime
import csv
import re


# ============================================================
# Paths (built fo universal use and not only in local directory system)
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "historical-ucl-matches"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "matches.csv"
)


# ============================================================
# Patterns
# ============================================================

SEASON_PATTERN = re.compile(
    r"UEFA Champions League (\d{4}/\d{2})"
)

DATE_PATTERN = re.compile(
    r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
    r"(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"\s+"
    r"(?P<day>\d{1,2})"
    r"(?:\s+(?P<year>\d{4}))?$"
)

STAGE_PATTERN = re.compile(
    r"^▪\s+(.+)"
)

MATCH_PATTERN = re.compile(
    r"""
    ^\s*

    # Optional kickoff time
    (?:(?P<time>\d{1,2}:\d{2})\s+)?

    # Home team
    (?P<home>.+?)
    \s+v\s+

    # Away team
    (?P<away>.+?)
    \s+

    # Final score
    (?P<final_home>\d+)
    -
    (?P<final_away>\d+)

    # Optional penalty shootout:
    # 4-3 pen. 1-0 a.e.t.
    (?:
        \s+pen\.\s+
        (?P<shootout_home>\d+)
        -
        (?P<shootout_away>\d+)
        \s+a\.e\.t\.
    )?

    # Optional extra time
    (?:
        \s+a\.e\.t\.
    )?

    # Optional scores in parentheses
    (?:
        \s+
        \(
        (?P<parentheses>[^)]+)
        \)
    )?

    \s*$
    """,
    re.VERBOSE,
)


# ============================================================
# Helpers
# ============================================================

MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def extract_team_name(team_text):
    """
    Extract the team name without the country code.

    Example:

        Bayern München (GER)

    becomes:

        Bayern München
    """

    match = re.search(
        r"\s*\(([A-Z]{3})\)\s*$",
        team_text
    )

    if match:

        country = match.group(1)

        team = team_text[
            :match.start()
        ].strip()

        return team, country

    return team_text.strip(), None


def parse_parentheses(parentheses):
    """
    Interpret scores contained inside parentheses.

    Normal match:

        2-1 (1-0)

    means:

        final = 2-1
        halftime = 1-0

    Extra-time match:

        4-1 a.e.t. (3-1, 1-0)

    means:

        final-after-ET = 4-1
        score-after-90 = 3-1
        halftime = 1-0
    """

    if not parentheses:
        return {
            "regulation_home_goals": None,
            "regulation_away_goals": None,
            "half_time_home_goals": None,
            "half_time_away_goals": None,
        }

    scores = [
        score.strip()
        for score in parentheses.split(",")
    ]

    parsed_scores = []

    for score in scores:

        match = re.fullmatch(
            r"(\d+)-(\d+)",
            score
        )

        if not match:
            raise ValueError(
                f"Invalid parenthetical score: {score}"
            )

        parsed_scores.append(
            (
                int(match.group(1)),
                int(match.group(2)),
            )
        )

    if len(parsed_scores) == 1:

        return {
            "regulation_home_goals": None,
            "regulation_away_goals": None,
            "half_time_home_goals": (
                parsed_scores[0][0]
            ),
            "half_time_away_goals": (
                parsed_scores[0][1]
            ),
        }

    if len(parsed_scores) == 2:

        return {
            "regulation_home_goals": (
                parsed_scores[0][0]
            ),
            "regulation_away_goals": (
                parsed_scores[0][1]
            ),
            "half_time_home_goals": (
                parsed_scores[1][0]
            ),
            "half_time_away_goals": (
                parsed_scores[1][1]
            ),
        }

    raise ValueError(
        f"Unexpected number of parenthetical scores: "
        f"{parentheses}"
    )


def parse_match_line(line):
    """
    Parse one match line.

    Returns a dictionary or None.
    """

    match = MATCH_PATTERN.match(line)

    if not match:
        return None

    data = match.groupdict()

    home_team, home_country = extract_team_name(
        data["home"]
    )

    away_team, away_country = extract_team_name(
        data["away"]
    )

    final_home = int(
        data["final_home"]
    )

    final_away = int(
        data["final_away"]
    )

    is_penalty = (
        data["shootout_home"] is not None
    )

    is_extra_time = (
        "a.e.t." in line
    )

    parentheses_data = parse_parentheses(
        data["parentheses"]
    )

    # --------------------------------------------------------
    # For normal matches:
    #
    # final score = 90-minute score
    #
    # For extra-time matches:
    #
    # final score = extra-time score
    # regulation score comes from parentheses
    #
    # For penalty matches:
    #
    # final score = shootout score
    # extra-time score = second score
    # --------------------------------------------------------

    if is_penalty:

        shootout_home = int(
            data["shootout_home"]
        )

        shootout_away = int(
            data["shootout_away"]
        )

        final_after_et_home = (
            int(data["shootout_home"])
            if False
            else parentheses_data[
                "regulation_home_goals"
            ]
        )

        final_after_et_away = (
            int(data["shootout_away"])
            if False
            else parentheses_data[
                "regulation_away_goals"
            ]
        )

        # If the parenthetical contains only one score,
        # we cannot distinguish 90-minute and halftime.
        if final_after_et_home is None:

            final_after_et_home = (
                int(data["final_home"])
                * 0
            )

            final_after_et_away = (
                int(data["final_away"])
                * 0
            )

        regulation_home = final_after_et_home
        regulation_away = final_after_et_away

    elif is_extra_time:

        regulation_home = (
            parentheses_data[
                "regulation_home_goals"
            ]
        )

        regulation_away = (
            parentheses_data[
                "regulation_away_goals"
            ]
        )

        shootout_home = None
        shootout_away = None

    else:

        regulation_home = final_home
        regulation_away = final_away

        shootout_home = None
        shootout_away = None

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    if is_penalty:

        shootout_winner = (
            "H"
            if shootout_home > shootout_away
            else "A"
        )

        result_90 = (
            "H"
            if regulation_home > regulation_away
            else "A"
            if regulation_home < regulation_away
            else "D"
        )

        result_final = shootout_winner

    else:

        shootout_winner = None

        result_90 = (
            "H"
            if regulation_home > regulation_away
            else "A"
            if regulation_home < regulation_away
            else "D"
        )

        result_final = (
            "H"
            if final_home > final_away
            else "A"
            if final_home < final_away
            else "D"
        )

    return {
        "time": data["time"],
        "home_team": home_team,
        "home_country": home_country,
        "away_team": away_team,
        "away_country": away_country,

        "home_goals": final_home,
        "away_goals": final_away,

        "regulation_home_goals": regulation_home,
        "regulation_away_goals": regulation_away,

        "half_time_home_goals": (
            parentheses_data[
                "half_time_home_goals"
            ]
        ),

        "half_time_away_goals": (
            parentheses_data[
                "half_time_away_goals"
            ]
        ),

        "shootout_home_goals": shootout_home,
        "shootout_away_goals": shootout_away,

        "extra_time": is_extra_time,
        "penalty_shootout": is_penalty,

        "result_90": result_90,
        "result_final": result_final,
        "shootout_winner": shootout_winner,

        "raw_match": line.strip(),
    }


# ============================================================
# Date handling
# ============================================================

def parse_date(
    date_text,
    season_start_year,
    previous_date
):
    """
    Convert source dates into ISO dates.

    The source only gives the year for the first
    date of a season. Subsequent dates omit it.

    We infer the year from the previous date.
    """

    match = DATE_PATTERN.match(
        date_text
    )

    if not match:
        raise ValueError(
            f"Invalid date: {date_text}"
        )

    month = MONTHS[
        match.group("month")
    ]

    day = int(
        match.group("day")
    )

    explicit_year = match.group(
        "year"
    )

    if explicit_year:

        year = int(explicit_year)

    elif previous_date:

        year = previous_date.year

        # Season crossed into the next calendar year.
        if month < previous_date.month:
            year += 1

    else:

        year = season_start_year

    return datetime(
        year,
        month,
        day
    ).date()


# ============================================================
# Stage parsing
# ============================================================

def parse_stage(stage_text):
    """
    Convert source stage heading into:

        stage
        round

    Examples:

        Group A
        -> Group / Group A

        Group, Matchday 1
        -> Group / Matchday 1

        League, Matchday 3
        -> League / Matchday 3

        Finals, Quarterfinals
        -> Finals / Quarterfinals
    """

    if "," in stage_text:

        stage, round_name = (
            part.strip()
            for part in stage_text.split(
                ",",
                1
            )
        )

        return stage, round_name

    # Old format:
    # Group A
    if stage_text.startswith(
        "Group "
    ) or stage_text.startswith(
        "Gruppe "
    ):

        return (
            "Group",
            stage_text
        )

    return (
        stage_text,
        stage_text
    )


# ============================================================
# Parse one file
# ============================================================

def parse_file(file_path):

    with file_path.open(
        "r",
        encoding="utf-8"
    ) as file:

        lines = [
            line.rstrip()
            for line in file
        ]

    # --------------------------------------------------------
    # Season
    # --------------------------------------------------------

    season = None

    for line in lines:

        match = SEASON_PATTERN.search(
            line
        )

        if match:

            season = match.group(1)
            break

    if season is None:

        raise ValueError(
            f"Could not find season in "
            f"{file_path.name}"
        )

    season_start_year = int(
        season[:4]
    )

    # --------------------------------------------------------
    # State
    # --------------------------------------------------------

    current_stage = None
    current_round = None

    current_date = None

    matches = []

    warnings = []

    # --------------------------------------------------------
    # Process lines
    # --------------------------------------------------------

    for line_number, line in enumerate(
        lines,
        start=1
    ):

        stripped = line.strip()

        if not stripped:
            continue

        # ----------------------------------------------------
        # Stage
        # ----------------------------------------------------

        stage_match = STAGE_PATTERN.match(
            stripped
        )

        if stage_match:

            stage_text = (
                stage_match.group(1).strip()
            )

            (
                current_stage,
                current_round,
            ) = parse_stage(
                stage_text
            )

            continue

        # ----------------------------------------------------
        # Date
        # ----------------------------------------------------

        if DATE_PATTERN.match(
            stripped
        ):

            current_date = parse_date(
                stripped,
                season_start_year,
                current_date
            )

            continue

        # ----------------------------------------------------
        # Match
        # ----------------------------------------------------

        if " v " in stripped:

            parsed = parse_match_line(
                stripped
            )

            if parsed is None:

                warnings.append(
                    {
                        "line": line_number,
                        "content": stripped,
                    }
                )

                continue

            parsed.update(
                {
                    "season": season,
                    "date": current_date,
                    "stage": current_stage,
                    "round": current_round,
                    "source_file": file_path.name,
                    "source_line": line_number,
                }
            )

            matches.append(
                parsed
            )

    return matches, warnings


# ============================================================
# Match IDs
# ============================================================

def add_match_ids(matches):

    counters = {}

    for match in matches:

        season_start = match[
            "season"
        ][:4]

        counters.setdefault(
            season_start,
            0
        )

        counters[season_start] += 1

        match["match_id"] = (
            f"UCL_{season_start}_"
            f"{counters[season_start]:04d}"
        )

    return matches


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 70)
    print("UCL MATCH DATA EXTRACTION")
    print("=" * 70)

    files = sorted(
        RAW_DIR.glob("*.txt")
    )

    if not files:

        print(
            "\nERROR: No raw files found."
        )

        return

    all_matches = []

    total_warnings = 0

    # --------------------------------------------------------
    # Parse files
    # --------------------------------------------------------

    for file_path in files:

        print(
            f"\nProcessing: "
            f"{file_path.name}"
        )

        matches, warnings = parse_file(
            file_path
        )

        print(
            f"  Matches extracted: "
            f"{len(matches)}"
        )

        if warnings:

            print(
                f"  Warnings: "
                f"{len(warnings)}"
            )

            for warning in warnings[:5]:

                print(
                    f"    Line "
                    f"{warning['line']}: "
                    f"{warning['content']}"
                )

        else:

            print(
                "  Warnings: 0"
            )

        total_warnings += len(
            warnings
        )

        all_matches.extend(
            matches
        )

    # --------------------------------------------------------
    # Add IDs
    # --------------------------------------------------------

    all_matches = add_match_ids(
        all_matches
    )

    # --------------------------------------------------------
    # Output directory
    # --------------------------------------------------------

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # CSV columns
    # --------------------------------------------------------

    fieldnames = [
        "match_id",

        "season",
        "date",
        "time",

        "stage",
        "round",

        "home_team",
        "home_country",

        "away_team",
        "away_country",

        "home_goals",
        "away_goals",

        "regulation_home_goals",
        "regulation_away_goals",

        "half_time_home_goals",
        "half_time_away_goals",

        "shootout_home_goals",
        "shootout_away_goals",

        "extra_time",
        "penalty_shootout",

        "result_90",
        "result_final",
        "shootout_winner",

        "raw_match",

        "source_file",
        "source_line",
    ]

    # --------------------------------------------------------
    # Write CSV
    # --------------------------------------------------------

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            all_matches
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "EXTRACTION COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        f"Files processed:    {len(files)}"
    )

    print(
        f"Total matches:      {len(all_matches)}"
    )

    print(
        f"Parser warnings:    {total_warnings}"
    )

    print(
        f"Output:             {OUTPUT_FILE}"
    )

    extra_time = sum(
        match["extra_time"]
        for match in all_matches
    )

    penalties = sum(
        match["penalty_shootout"]
        for match in all_matches
    )

    print(
        f"\nExtra-time matches: "
        f"{extra_time}"
    )

    print(
        f"Penalty shootouts:  "
        f"{penalties}"
    )

    print(
        "\nDone."
    )


if __name__ == "__main__":
    main()