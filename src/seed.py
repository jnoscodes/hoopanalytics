"""Build the seed database committed to the repo (data/seed/hoopanalytics_seed.db).

Pre-fetches bio + career stats for every currently active NBA player, so a
fresh cloud deploy starts with useful, reliable data instead of an empty
database that depends on live calls to stats.nba.com -- which blocks
requests from major cloud hosting providers (see PROGRESS.md for the
investigation).

"Active players" (~500+ people currently on an NBA roster) was chosen over
an arbitrary season cutoff: it's a principled, self-updating criterion --
covers who a visitor is actually likely to search for -- rather than an
arbitrary date that would need to be revisited every season anyway.

Run manually, from a network not affected by the cloud-IP blocking (i.e.
not from a blocked cloud host), whenever the seed needs refreshing:

    python -m src.seed
"""

import sqlite3
import sys

from nba_api.stats.static import players

from src.clean import clean_career_stats, clean_player_bio
from src.database import CREATE_CAREER_STATS_TABLE, CREATE_PLAYERS_TABLE, SEED_DB_PATH, insert_career_stats, insert_player_bio
from src.fetch import fetch_player_career_stats, fetch_player_info

# Many player names contain non-ASCII characters (e.g. Jokic -> Jokić).
# A redirected/backgrounded stdout on Windows defaults to cp1252, which
# can't encode them and would crash the print() calls below.
sys.stdout.reconfigure(encoding="utf-8")


def seed_active_players() -> None:
    SEED_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SEED_DB_PATH)
    conn.execute(CREATE_PLAYERS_TABLE)
    conn.execute(CREATE_CAREER_STATS_TABLE)
    conn.commit()

    already_seeded = {
        row[0] for row in conn.execute("SELECT PERSON_ID FROM players").fetchall()
    }

    active = players.get_active_players()
    to_fetch = [p for p in active if p["id"] not in already_seeded]
    print(
        f"{len(active)} active players, {len(already_seeded)} already seeded, "
        f"{len(to_fetch)} left to fetch into {SEED_DB_PATH}..."
    )

    succeeded = 0
    failed = []
    for i, p in enumerate(to_fetch, 1):
        try:
            bio_df = clean_player_bio(fetch_player_info(p["id"]))
            stats_df = clean_career_stats(fetch_player_career_stats(p["id"]))
            insert_player_bio(conn, bio_df)
            insert_career_stats(conn, stats_df)
            succeeded += 1
            print(f"[{i}/{len(to_fetch)}] OK: {p['full_name']}")
        except Exception as exc:
            failed.append(p["full_name"])
            print(f"[{i}/{len(to_fetch)}] FAILED: {p['full_name']} ({exc})")

    conn.close()
    print(f"Done. {succeeded} succeeded, {len(failed)} failed this run.")
    if failed:
        print("Failed players:", failed)


if __name__ == "__main__":
    seed_active_players()
