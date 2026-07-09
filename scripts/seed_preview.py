"""
Seeds the 3 fictitious preview profiles (CLAUDE_CRM_MODULE.md section 10)
into their own dedicated preview databases. Run once after migrating each
preview DB with 0002_client_raise_schema. Idempotent-ish: truncates each
preview DB's tables first so re-running doesn't duplicate rows.

Usage: python crm/scripts/seed_preview.py
(run with cwd=crm/ and PYTHONPATH set to the crm/ dir so `app.*` resolves)
"""
from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.db.models.client_raise import (
    Campaign, CampaignMetrics, DataRoomAccessLog, DataRoomDocument,
    FundingEvent, FundingSummary, InvestorTarget, Meeting, PipelineRecord,
    RaiseConfig, WeeklyReport,
)

random.seed(42)

FIRST_NAMES = [
    "James", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas",
    "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald",
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
    "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Margaret", "Sandra", "Ashley",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
]
TITLES = [
    "Managing Director", "Principal", "Partner", "Chief Investment Officer",
    "Portfolio Manager", "Director of Investments", "Founder", "Managing Partner",
    "VP Private Wealth", "Family Office Director", "Investment Committee Chair",
]
COMPANY_SUFFIXES = ["Capital", "Partners", "Family Office", "Wealth Management", "Investments", "Holdings", "Group"]
INVESTOR_TYPES = ["family_office", "ria", "hnw", "uhnw", "institutional"]
GEOGRAPHIES = ["Southeast US", "Northeast US", "West Coast", "Midwest", "Texas", "Mid-Atlantic"]


def random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_company() -> str:
    return f"{random.choice(LAST_NAMES)} {random.choice(COMPANY_SUFFIXES)}"


PROFILES = {
    "ias_crm_preview_meridian": {
        "display_name": "Meridian Capital Partners",
        "deal_type": "cre_syndication",
        "asset_class": "value_add_multifamily",
        "geography": "Southeast US",
        "raise_target": 18_000_000,
        "days_active": 34,
        "investor_count": 94,
        "stage_weights": {
            "prospect": 0.30, "qualified": 0.25, "engaged": 0.20,
            "meeting_scheduled": 0.12, "meeting_completed": 0.08, "soft_committed": 0.05,
        },
        "open_rate": 0.38, "reply_rate": 0.14, "meetings": 11,
        "doc_count": 6, "views_this_week": 23,
        "soft_committed": 4_200_000, "hard_committed": 0, "funded": 0,
    },
    "ias_crm_preview_cornerstone": {
        "display_name": "Cornerstone Credit Fund I",
        "deal_type": "private_credit",
        "asset_class": "sme_bridge_lending",
        "geography": "Nationwide",
        "raise_target": 40_000_000,
        "days_active": 52,
        "investor_count": 71,
        "stage_weights": {
            "prospect": 0.20, "qualified": 0.20, "engaged": 0.20,
            "meeting_completed": 0.15, "soft_committed": 0.15, "committed": 0.10,
        },
        "open_rate": 0.42, "reply_rate": 0.18, "meetings": 8,
        "doc_count": 8, "views_this_week": 31,
        "soft_committed": 0, "hard_committed": 12_500_000, "funded": 0,
    },
    "ias_crm_preview_elevation": {
        "display_name": "Elevation Income REIT",
        "deal_type": "real_estate_fund",
        "asset_class": "diversified_income",
        "geography": "Nationwide",
        "raise_target": 75_000_000,
        "days_active": 28,
        "investor_count": 118,
        "stage_weights": {
            "prospect": 0.40, "qualified": 0.30, "engaged": 0.15,
            "meeting_scheduled": 0.08, "meeting_completed": 0.05, "soft_committed": 0.02,
        },
        "open_rate": 0.35, "reply_rate": 0.11, "meetings": 17,
        "doc_count": 5, "views_this_week": 44,
        "soft_committed": 8_800_000, "hard_committed": 0, "funded": 0,
    },
}

DOC_TYPES = ["ppm", "exec_summary", "financial_model", "subscription_agreement", "track_record", "market_analysis", "team_bios", "operating_agreement"]


def weighted_stage(weights: dict[str, float]) -> str:
    stages, probs = zip(*weights.items())
    return random.choices(stages, weights=probs, k=1)[0]


async def seed_profile(db_url: str, profile: dict) -> None:
    engine = create_async_engine(db_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        # Wipe existing seed data so re-runs don't duplicate.
        for table in [
            "funding_events", "funding_summary", "data_room_access_log", "data_room_documents",
            "meetings", "campaign_metrics", "campaigns", "pipeline_records", "investor_targets",
            "weekly_reports", "raise_config",
        ]:
            await session.execute(text(f"TRUNCATE {table} CASCADE"))
        await session.commit()

        now = datetime.now(timezone.utc)
        launch_date = date.today() - timedelta(days=profile["days_active"])

        # raise_config
        session.add(RaiseConfig(
            id=uuid.uuid4(),
            raise_name=profile["display_name"],
            deal_type=profile["deal_type"],
            asset_class=profile["asset_class"],
            geography=profile["geography"],
            raise_target=profile["raise_target"],
            minimum_investment=250_000,
            structure="506c",
            launch_date=launch_date,
            target_close_date=launch_date + timedelta(days=180),
            status="active",
        ))

        # investor_targets + pipeline_records
        target_ids = []
        for _ in range(profile["investor_count"]):
            tid = uuid.uuid4()
            target_ids.append(tid)
            session.add(InvestorTarget(
                id=tid,
                full_name=random_name(),
                email=f"investor{tid.hex[:8]}@example.test",
                title=random.choice(TITLES),
                company=random_company(),
                investor_type=random.choice(INVESTOR_TYPES),
                geography=random.choice(GEOGRAPHIES),
                fit_score=random.randint(55, 98),
                status="active",
                added_by="rep@capitalcontext.com",
            ))
            session.add(PipelineRecord(
                id=uuid.uuid4(),
                investor_target_id=tid,
                stage=weighted_stage(profile["stage_weights"]),
                stage_entered_at=now - timedelta(days=random.randint(0, profile["days_active"])),
                days_in_stage=random.randint(1, 21),
            ))

        # campaign + weekly campaign_metrics converging to stated rates
        campaign_id = uuid.uuid4()
        session.add(Campaign(
            id=campaign_id,
            campaign_name=f"{profile['display_name']} — Investor Outreach",
            channel="combined",
            status="active",
            start_date=launch_date,
            target_count=profile["investor_count"],
        ))
        weeks = max(1, profile["days_active"] // 7)
        per_week_sent = profile["investor_count"] // weeks or profile["investor_count"]
        for w in range(weeks):
            sent = per_week_sent
            opened = round(sent * profile["open_rate"])
            replied = round(sent * profile["reply_rate"])
            session.add(CampaignMetrics(
                id=uuid.uuid4(),
                campaign_id=campaign_id,
                metric_date=launch_date + timedelta(weeks=w + 1),
                sent_count=sent,
                delivered_count=round(sent * 0.97),
                open_count=opened,
                click_count=round(opened * 0.3),
                reply_count=replied,
                bounce_count=round(sent * 0.02),
                unsubscribe_count=random.randint(0, 2),
                open_rate=profile["open_rate"] * 100,
                reply_rate=profile["reply_rate"] * 100,
            ))

        # meetings
        for _ in range(profile["meetings"]):
            session.add(Meeting(
                id=uuid.uuid4(),
                investor_target_id=random.choice(target_ids),
                meeting_type=random.choice(["intro_call", "deep_dive", "follow_up"]),
                scheduled_at=now - timedelta(days=random.randint(0, profile["days_active"])),
                duration_minutes=random.choice([30, 45, 60]),
                status="completed",
                outcome=random.choice(["positive", "neutral", "follow_up_required"]),
                logged_by="rep@capitalcontext.com",
            ))

        # data room documents + access log
        doc_ids = []
        for i in range(profile["doc_count"]):
            did = uuid.uuid4()
            doc_ids.append(did)
            session.add(DataRoomDocument(
                id=did,
                document_name=f"{profile['display_name']} — {DOC_TYPES[i % len(DOC_TYPES)].replace('_', ' ').title()}",
                document_type=DOC_TYPES[i % len(DOC_TYPES)],
                file_path=f"/data-room/{profile['deal_type']}/{DOC_TYPES[i % len(DOC_TYPES)]}.pdf",
                file_size_bytes=random.randint(200_000, 5_000_000),
                access_level=random.choice(["qualified", "committed", "public"]),
                uploaded_by="rep@capitalcontext.com",
            ))
        for _ in range(profile["views_this_week"]):
            session.add(DataRoomAccessLog(
                id=uuid.uuid4(),
                document_id=random.choice(doc_ids),
                investor_target_id=random.choice(target_ids),
                accessed_by="investor",
                accessed_at=now - timedelta(hours=random.randint(0, 24 * 7)),
                access_duration_seconds=random.randint(30, 600),
            ))

        # funding summary + a few underlying events
        percent_raised = round(
            (profile["soft_committed"] + profile["hard_committed"] + profile["funded"])
            / profile["raise_target"] * 100, 1,
        )
        session.add(FundingSummary(
            id=uuid.uuid4(),
            raise_target=profile["raise_target"],
            soft_committed=profile["soft_committed"],
            hard_committed=profile["hard_committed"],
            funded=profile["funded"],
            investor_count_soft=max(1, profile["soft_committed"] // 500_000) if profile["soft_committed"] else 0,
            investor_count_funded=0,
            percent_raised=percent_raised,
        ))
        remaining = profile["soft_committed"] or profile["hard_committed"]
        event_type = "soft_commit" if profile["soft_committed"] else "hard_commit"
        n_events = max(1, remaining // 500_000) if remaining else 0
        for _ in range(min(n_events, 12)):
            session.add(FundingEvent(
                id=uuid.uuid4(),
                investor_target_id=random.choice(target_ids),
                event_type=event_type,
                amount=random.choice([250_000, 500_000, 750_000, 1_000_000]),
                event_date=date.today() - timedelta(days=random.randint(0, profile["days_active"])),
                logged_by="rep@capitalcontext.com",
            ))

        # weekly report — hand-authored prose, published (business rule 3)
        session.add(WeeklyReport(
            id=uuid.uuid4(),
            report_week_ending=date.today(),
            generated_by="system",
            pipeline_summary={"total_investors": profile["investor_count"], "by_stage": profile["stage_weights"]},
            campaign_summary={"open_rate": profile["open_rate"], "reply_rate": profile["reply_rate"]},
            meeting_summary={"meetings_scheduled": profile["meetings"]},
            funding_summary={"percent_raised": percent_raised},
            key_activities=(
                f"Continued outreach to {profile['investor_count']} qualified {profile['geography']} investors. "
                f"{profile['meetings']} meetings held to date, with strong engagement on the data room "
                f"({profile['views_this_week']} document views this week)."
            ),
            next_week_priorities=(
                "Advance engaged investors toward scheduled meetings; follow up with soft-committed "
                "investors on subscription documentation timelines."
            ),
            rep_commentary=(
                f"{profile['display_name']}'s raise is tracking well at {percent_raised}% of target "
                f"{profile['days_active']} days in. Campaign performance ({round(profile['open_rate']*100)}% open, "
                f"{round(profile['reply_rate']*100)}% reply) is ahead of program benchmarks."
            ),
            status="published",
            published_at=now,
        ))

        await session.commit()

    await engine.dispose()

    # Report counts for the terminal sanity check the plan calls for.
    engine2 = create_async_engine(db_url, echo=False)
    Session2 = async_sessionmaker(engine2, expire_on_commit=False)
    async with Session2() as session:
        for table in ["investor_targets", "pipeline_records", "campaign_metrics", "meetings",
                      "data_room_documents", "data_room_access_log", "funding_events"]:
            count = (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()
            print(f"    {table}: {count}")
    await engine2.dispose()


async def main() -> None:
    for db_name, url in settings.preview_db_urls.items():
        profile = PROFILES[db_name]
        print(f"Seeding {db_name} ({profile['display_name']})...")
        await seed_profile(url, profile)


if __name__ == "__main__":
    asyncio.run(main())
