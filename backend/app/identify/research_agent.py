"""
Identify pillar.

Two jobs, both now grounded in real web research (see web_research.py for
exactly when/how often this runs -- short answer: on-demand, not constant
background scraping):

1. `run_research_cycle(attack_entry)` -- refresh a single existing
   taxonomy entry with real, current search results. Doesn't rewrite the
   curated description; it attaches sources + a timestamp so the person
   (and a judge) can see what's actually backing the pattern, and can
   sanity-check it against real reporting.

2. `synthesize_new_attack_id(cluster_summary, channel)` -- called by the
   closed loop when it's about to name a brand-new pattern. Now runs a
   real web search using the cluster summary as the query BEFORE asking
   Groq to name/describe it, and feeds the actual search snippets into
   the prompt as grounding context. The new entry ships with its sources
   attached, so a newly-discovered pattern is "we found N related
   reports and this is our synthesis," not "the LLM free-associated a
   name."
"""
import uuid

from app.groq_client import groq_client
from app.config import settings
from app.identify.web_research import research_attack_pattern

_SYSTEM = (
    "You are a fraud-intelligence analyst. You turn short incident "
    "descriptions into a single structured taxonomy entry describing an "
    "emerging GenAI-enabled payment fraud pattern. Be specific and concrete. "
    "If real search results are provided, ground your description in them "
    "and prefer their specifics over generic assumptions."
)


def run_research_cycle(attack_entry: dict) -> dict:
    """Refresh one existing taxonomy entry with real search results.
    Returns the updated entry (also mutates research_sources /
    last_researched_at in place for convenience)."""
    query = f"{attack_entry['display_name']} payment fraud India UPI 2026"
    research = research_attack_pattern(query, max_results=5)
    attack_entry["research_sources"] = research["sources"]
    attack_entry["last_researched_at"] = research["researched_at"]
    attack_entry["research_found_live_results"] = research["found_results"]
    return attack_entry


def synthesize_new_attack_id(cluster_summary: str, sample_channel: str) -> dict:
    """
    Called by the Defend feedback loop when a cluster of generalist-only
    catches looks coherent enough to deserve its own specialist.
    """
    # Ground the naming step in a real search first, using the cluster's
    # own summary as the query -- this is the "researched, not guessed"
    # step for brand-new patterns.
    query = cluster_summary.replace("\n", " ").replace("- ", "")[:200]
    research = research_attack_pattern(f"{query} payment fraud", max_results=5)
    sources_block = (
        "\n".join(f"- {s['title']}: {s['snippet'][:200]}" for s in research["sources"])
        if research["sources"]
        else "(no live search results available for this query)"
    )

    prompt = (
        f"Cluster of unclaimed fraud cases (channel: {sample_channel}):\n"
        f"{cluster_summary}\n\n"
        f"Real web search results for related reporting:\n{sources_block}\n\n"
        "Return a JSON object with keys: attack_id (snake_case, short), "
        "display_name, technique, description (1-2 sentences), "
        "social_engineering_pattern, technical_signature (array of 2-4 "
        "short strings)."
    )
    fallback = {
        "attack_id": "emerging_pattern_" + uuid.uuid4().hex[:8],
        "display_name": "Emerging Pattern (auto-detected)",
        "technique": "unclassified_emerging_pattern",
        "description": "Auto-flagged by the generalist detector; pending analyst review. "
                        "(Offline fallback name -- set GROQ_API_KEY for a real LLM-generated "
                        "name/description drawn from the actual cluster summary and search results.)",
        "social_engineering_pattern": "unknown",
        "technical_signature": ["anomalous_pattern"],
    }
    result = groq_client.complete_json(
        prompt, system=_SYSTEM, model=settings.groq_model_smart, offline_fallback=fallback
    )
    result.setdefault("channel", sample_channel)
    result.setdefault("seed_or_discovered", "discovered")
    result.setdefault("specialist_tier", "auto")
    result.setdefault("specialist_module", "auto")
    for k, v in fallback.items():
        result.setdefault(k, v)

    # Attach the research this entry was actually grounded in, so it's
    # visible in the UI and the sources are real, clickable citations.
    result["research_sources"] = research["sources"]
    result["last_researched_at"] = research["researched_at"]
    result["research_found_live_results"] = research["found_results"]
    return result
